import type { SuiSignPersonalMessageOutput } from "@mysten/wallet-standard";
import { api } from "./api";

/** Must match `SIGNIN_MESSAGE_TEMPLATE` in backend/app/auth/service.py
 * exactly — the backend re-derives this from the nonce alone rather than
 * trusting client-supplied message text, so any drift here just fails
 * verification rather than being a security issue, but keep them in sync. */
function signInMessage(nonce: string): Uint8Array {
  return new TextEncoder().encode(`Sign in to Umbra\n\nNonce: ${nonce}`);
}

type SignPersonalMessage = (input: {
  message: Uint8Array;
}) => Promise<SuiSignPersonalMessageOutput>;

/** Requests a fresh nonce and asks the connected wallet to sign it —
 * the shared first half of both establishing a session (App.tsx) and
 * re-authenticating for a PIN reset (Dashboard.tsx). */
export async function signNonce(
  signPersonalMessage: SignPersonalMessage,
): Promise<{ nonce: string; signature: string }> {
  const { nonce } = await api.requestNonce();
  const { signature } = await signPersonalMessage({ message: signInMessage(nonce) });
  return { nonce, signature };
}

/** Full sign-in: proves wallet control of `address` and establishes the
 * Umbra session cookie. */
export async function establishSession(
  address: string,
  signPersonalMessage: SignPersonalMessage,
): Promise<string> {
  const { nonce, signature } = await signNonce(signPersonalMessage);
  const { sui_address } = await api.createSession(address, nonce, signature);
  return sui_address;
}
