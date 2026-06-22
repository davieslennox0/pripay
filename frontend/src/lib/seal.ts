import { SealClient } from "@mysten/seal";
import { getJsonRpcFullnodeUrl, SuiJsonRpcClient } from "@mysten/sui/jsonRpc";
import { fromBase64, normalizeSuiObjectId, toBase64 } from "@mysten/sui/utils";

const SUI_NETWORK = (import.meta.env.VITE_SUI_NETWORK as string) ?? "testnet";

/** Placeholder until move-contracts/umbra is actually deployed (Sui CLI
 * install was deferred to another server) — mirrors Move.toml's own
 * `umbra = "0x0"` placeholder.
 *
 * Confirmed by testing against this codebase: SealClient.encrypt() itself
 * calls suiClient.core.getObject({ objectId: packageId }) and requires
 * version === "1" — i.e. it needs the *real*, first-published package to
 * exist on-chain. This isn't just a decrypt-time requirement (decrypt
 * additionally needs seal_approve_send deployed and dry-run-able, which is
 * the actual access-control check) — encrypt() is blocked too. So nothing
 * in this file is callable yet; it's wired and ready for the moment
 * move-contracts/umbra is published to testnet at v1.
 */
export const UMBRA_PACKAGE_ID_PLACEHOLDER = normalizeSuiObjectId("0x0");

// Mysten Labs' own open testnet key servers — see
// github.com/MystenLabs/seal/blob/main/docs/content/Pricing.mdx
const TESTNET_KEY_SERVERS = [
  { objectId: "0x73d05d62c18d9374e3ea529e8e0ed6161da1a141a94d3f76ae3fe4e99356db75", weight: 1 },
  { objectId: "0xf5d14a81a982144ae441cd7d64b09027f116a468bd36e7eca494f750591623c8", weight: 1 },
];

const suiClient = new SuiJsonRpcClient({
  url: getJsonRpcFullnodeUrl(SUI_NETWORK as "testnet"),
  network: SUI_NETWORK as "testnet",
});

const sealClient = new SealClient({
  suiClient,
  serverConfigs: TESTNET_KEY_SERVERS,
  verifyKeyServers: false,
});

function addressToHex(address: string): string {
  return address.replace(/^0x/, "").padStart(64, "0");
}

export interface EncryptedPayload {
  ciphertext: string;
  backupKey: string;
}

/** Encrypts a send's plaintext fields (amount, memo) so that, once
 * seal_policy_send is deployed, only the sender or receiver address baked
 * into `id` can ever request a decryption key for it (brief §5). */
export async function encryptSendPayload(
  senderAddress: string,
  receiverAddress: string,
  payload: Record<string, unknown>,
): Promise<EncryptedPayload> {
  const id = addressToHex(senderAddress) + addressToHex(receiverAddress);
  const data = new TextEncoder().encode(JSON.stringify(payload));

  const { encryptedObject, key } = await sealClient.encrypt({
    threshold: 2,
    packageId: UMBRA_PACKAGE_ID_PLACEHOLDER,
    id,
    data,
  });

  return { ciphertext: toBase64(encryptedObject), backupKey: toBase64(key) };
}

/** Parses the encrypted object's structure (version, packageId, id,
 * threshold, which key servers it's split across) without decrypting it —
 * proves the ciphertext round-trips through Seal's real BCS format.
 *
 * Full plaintext recovery needs sealClient.decrypt(), which requires a
 * SessionKey (signed by the user's wallet) and txBytes calling
 * seal_approve_send — both of which need seal_policy_send actually
 * deployed on-chain. There's no shortcut around that dry-run; it's the
 * whole point of the access policy. Deferred to whenever the Move package
 * is deployed (Sui CLI install was deferred to another server).
 */
export async function parseEncryptedObject(encrypted: EncryptedPayload) {
  const { EncryptedObject } = await import("@mysten/seal");
  return EncryptedObject.parse(fromBase64(encrypted.ciphertext));
}
