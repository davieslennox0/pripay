const BACKEND_URL = import.meta.env.VITE_BACKEND_URL as string;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request to ${path} failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export interface GoogleVerifyResponse {
  google_sub: string;
  salt: string;
}

export interface SessionResponse {
  sui_address: string;
}

export interface MeResponse {
  google_sub: string;
  sui_address: string;
}

export interface PinStatusResponse {
  is_set: boolean;
}

export interface SearchResult {
  platform: string;
  handle: string;
  sui_address: string;
}

export interface SendQuoteResponse {
  is_bound: boolean;
  fee: number;
  receiver_gets: number;
}

export interface SendExecuteResponse {
  status: string;
  receiver_gets: number;
  claim_token: string | null;
  tx_ref: string | null;
  // Enclave that settled the send + its attestation digest (brief §4/§5).
  tee_provider: string | null;
  tee_attestation: string | null;
}

export const api = {
  verifyGoogleToken: (idToken: string) =>
    request<GoogleVerifyResponse>("/auth/google/verify", {
      method: "POST",
      body: JSON.stringify({ id_token: idToken }),
    }),

  createSession: (googleSub: string, suiAddress: string) =>
    request<SessionResponse>("/auth/session", {
      method: "POST",
      body: JSON.stringify({ google_sub: googleSub, sui_address: suiAddress }),
    }),

  me: () => request<MeResponse>("/auth/me"),

  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),

  pinStatus: () => request<PinStatusResponse>("/pin/status"),

  setPin: (pin: string) => request<{ ok: boolean }>("/pin/set", { method: "POST", body: JSON.stringify({ pin }) }),

  searchHandles: (platform: string, query: string) =>
    request<SearchResult[]>(`/handles/search?${new URLSearchParams({ platform, query })}`),

  sendQuote: (platform: string, handle: string, amount: number) =>
    request<SendQuoteResponse>("/send/quote", {
      method: "POST",
      body: JSON.stringify({ platform, handle, amount }),
    }),

  sendExecute: (platform: string, handle: string, amount: number, pin: string) =>
    request<SendExecuteResponse>("/send/execute", {
      method: "POST",
      body: JSON.stringify({ platform, handle, amount, pin }),
    }),

  claimSend: (claimToken: string) =>
    request<{ ok: boolean; amount: number }>("/send/claim", {
      method: "POST",
      body: JSON.stringify({ claim_token: claimToken }),
    }),
};
