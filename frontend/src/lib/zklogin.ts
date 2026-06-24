import { Ed25519Keypair } from "@mysten/sui/keypairs/ed25519";
import { getJsonRpcFullnodeUrl, SuiJsonRpcClient } from "@mysten/sui/jsonRpc";
import { decodeJwt, generateNonce, generateRandomness, jwtToAddress } from "@mysten/sui/zklogin";
import { api } from "./api";

// PIN reset (brief §6) needs a *fresh* Google ID token, not the zkLogin
// address derivation this module otherwise exists for — generateNonce still
// needs a keypair + maxEpoch to produce a valid nonce shape, but the
// resulting token is only ever used for /pin/reset/request, never to derive
// or rebind a Sui address.
const PIN_RESET_PENDING_KEY = "umbra.pinResetPending";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string;
const SUI_NETWORK = (import.meta.env.VITE_SUI_NETWORK as string) ?? "testnet";

// Buffer so the ephemeral keypair stays valid for a couple of epochs past
// when the user starts the login flow.
const MAX_EPOCH_BUFFER = 2;

const STORAGE_KEYS = {
  ephemeralSecretKey: "umbra.ephemeralSecretKey",
  maxEpoch: "umbra.maxEpoch",
  randomness: "umbra.randomness",
} as const;

const suiClient = new SuiJsonRpcClient({
  url: getJsonRpcFullnodeUrl(SUI_NETWORK as "testnet"),
  network: SUI_NETWORK as "testnet",
});

/** Step 1: generate the ephemeral keypair + nonce, then redirect to Google.
 *
 * The ephemeral keypair, randomness, and maxEpoch are needed again later to
 * request the ZK proof at send-time (brief §12 step 6) — they're stashed in
 * sessionStorage now so they survive the redirect to Google and back.
 */
export async function beginGoogleLogin(): Promise<void> {
  const { epoch } = await suiClient.getLatestSuiSystemState();
  const maxEpoch = Number(epoch) + MAX_EPOCH_BUFFER;

  const ephemeralKeypair = new Ed25519Keypair();
  const randomness = generateRandomness();
  const nonce = generateNonce(ephemeralKeypair.getPublicKey(), maxEpoch, randomness);

  sessionStorage.setItem(STORAGE_KEYS.ephemeralSecretKey, ephemeralKeypair.getSecretKey());
  sessionStorage.setItem(STORAGE_KEYS.maxEpoch, String(maxEpoch));
  sessionStorage.setItem(STORAGE_KEYS.randomness, randomness);

  const params = new URLSearchParams({
    client_id: GOOGLE_CLIENT_ID,
    redirect_uri: window.location.origin + "/",
    response_type: "id_token",
    scope: "openid",
    nonce,
  });
  window.location.assign(`https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`);
}

/** Step 2: called on redirect back from Google. Extracts the ID token from
 * the URL fragment, verifies it server-side, derives the zkLogin Sui
 * address, and establishes the Umbra session. Returns null if there's no
 * pending login to complete — including when the redirect is actually for
 * a PIN-reset re-auth (same `#id_token=...` shape), which leaves the hash
 * untouched for completePinResetReauth to consume instead. */
export async function completeGoogleLogin(): Promise<string | null> {
  if (sessionStorage.getItem(PIN_RESET_PENDING_KEY) === "1") return null;

  const hashParams = new URLSearchParams(window.location.hash.slice(1));
  const idToken = hashParams.get("id_token");
  if (!idToken) return null;

  window.history.replaceState(null, "", window.location.pathname);

  if (!sessionStorage.getItem(STORAGE_KEYS.ephemeralSecretKey)) {
    throw new Error("No pending login found for this session (ephemeral key missing)");
  }

  decodeJwt(idToken); // throws if malformed before we round-trip to the backend
  const { google_sub, salt } = await api.verifyGoogleToken(idToken);
  const suiAddress = jwtToAddress(idToken, salt, false);
  await api.createSession(google_sub, suiAddress);
  return suiAddress;
}

/** Starts a fresh Google re-auth round-trip for a PIN reset (brief §6: "only
 * resettable via zkLogin re-auth + cooldown period") — separate from
 * beginGoogleLogin since it must NOT touch the ephemeral-keypair storage a
 * real login is mid-flight on, and must redirect back to a state that
 * resumes the reset instead of re-deriving a session. */
export function beginPinResetReauth(): void {
  sessionStorage.setItem(PIN_RESET_PENDING_KEY, "1");
  const params = new URLSearchParams({
    client_id: GOOGLE_CLIENT_ID,
    redirect_uri: window.location.origin + "/",
    response_type: "id_token",
    scope: "openid",
    nonce: generateRandomness(),
  });
  window.location.assign(`https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`);
}

/** Step 2 of the PIN-reset re-auth: called on redirect back from Google.
 * Returns the reset token + when its cooldown clears, or null if there's no
 * pending reset re-auth to complete. */
export async function completePinResetReauth(): Promise<{
  resetToken: string;
  availableAt: string;
} | null> {
  if (sessionStorage.getItem(PIN_RESET_PENDING_KEY) !== "1") return null;

  const hashParams = new URLSearchParams(window.location.hash.slice(1));
  const idToken = hashParams.get("id_token");
  window.history.replaceState(null, "", window.location.pathname);
  sessionStorage.removeItem(PIN_RESET_PENDING_KEY);
  if (!idToken) return null;

  const { reset_token, available_at } = await api.requestPinReset(idToken);
  return { resetToken: reset_token, availableAt: available_at };
}
