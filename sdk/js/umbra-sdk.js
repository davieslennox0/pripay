/**
 * Minimal JS SDK for the Umbra AI agent API (brief §9).
 *
 *   import { UmbraClient } from "./umbra-sdk.js";
 *   const client = new UmbraClient({ apiKey: "...", baseUrl: "https://api.umbra.example" });
 *   const result = await client.send({ handle: "bob@x.com", platform: "email", amount: 5 });
 *
 * Zero dependencies — uses the global `fetch` available in Node 18+ and
 * browsers, so it drops into any agent runtime without a package install.
 */

export class UmbraApiError extends Error {
  constructor(status, detail) {
    super(`Umbra API error ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

export class UmbraClient {
  constructor({ apiKey, baseUrl = "https://api.umbra.example" }) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  /** Sends `amount` of `token` to `handle` on `platform` (brief §9:
   * umbra.send(handle, platform, amount, token)). Throws UmbraApiError on a
   * 4xx/5xx — e.g. over the key's per-tx or daily cap, or a revoked key. */
  async send({ handle, platform, amount, token = "USDC" }) {
    return this._post("/agent/send", { platform, handle, amount, token });
  }

  async _post(path, body) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify(body),
    });
    const json = await res.json().catch(() => ({}));
    if (!res.ok) throw new UmbraApiError(res.status, json.detail ?? res.statusText);
    return json;
  }
}
