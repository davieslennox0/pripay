import { isValidPersonalMessageSignature } from "@mysten/sui/verify";
import { SuiJsonRpcClient } from "@mysten/sui/jsonRpc";

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return Buffer.concat(chunks).toString("utf8");
}

async function main() {
  const { message_b64, signature, address, rpc_url } = JSON.parse(await readStdin());
  const client = new SuiJsonRpcClient({ url: rpc_url });
  const message = Buffer.from(message_b64, "base64");

  // isValidPersonalMessageSignature only documents returning `false` for a
  // well-formed-but-wrong signature; a structurally malformed one (e.g. the
  // wrong byte length) throws instead. Both are attacker-controlled input,
  // not an environmental failure, so both map to {valid:false} here — only
  // errors *before* this call (bad JSON, unreachable rpc_url) should bubble
  // up to the process-exit-1 path below.
  let valid;
  try {
    valid = await isValidPersonalMessageSignature(message, signature, { client, address });
  } catch {
    valid = false;
  }
  process.stdout.write(JSON.stringify({ valid }));
}

main().catch((err) => {
  process.stderr.write(String(err?.stack ?? err));
  process.exit(1);
});
