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

// ── Auth ─────────────────────────────────────────────────────────
export interface NonceResponse    { nonce: string; }
export interface SessionResponse  { sui_address: string; }
export interface MeResponse       { sui_address: string; }
export interface PinStatusResponse { is_set: boolean; }

// ── Handles ──────────────────────────────────────────────────────
export interface SearchResult {
  platform: string;
  handle: string;
  sui_address: string;
}

export interface BoundHandleOut {
  platform: string;
  handle: string;
  verified_at: string;
}

// ── Send ─────────────────────────────────────────────────────────
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
  tee_provider: string | null;
  tee_attestation: string | null;
  record_hash: string | null;
}

// ── Dashboard ────────────────────────────────────────────────────
export interface BalanceOut {
  coin_type: string;
  symbol: string | null;
  balance: string;
  decimals: number | null;
  amount: number | null;
  price_usd: number | null;
  value_usd: number | null;
}

export interface HistoryItem {
  kind: string;
  direction: string | null;
  record_id: number;
  counterparty: string | null;
  status: string;
  created_at: string;
  can_decrypt: boolean;
}

export interface HistoryDecrypted {
  amount: number;
  token: string;
  memo: string | null;
}

export interface PersonalVolume {
  total_sent: number;
  total_received: number;
  swap_count: number;
}

export interface PlatformVolume {
  total_volume: number;
  total_fees: number;
  send_count: number;
}

// ── Swap ─────────────────────────────────────────────────────────
export interface SwapQuoteResponse {
  quote_id: number;
  amount_in: string;
  amount_out: string;
  spot_price: number;
  net_trade_fee_percentage: number;
}

export interface SwapExecuteResponse {
  status: string;
  tx_ref: string | null;
  tee_provider: string | null;
  tee_attestation: string | null;
}

// ── Receive ──────────────────────────────────────────────────────
export interface ReceiveQuoteResponse {
  record_id: number;
  tool: string;
  to_amount: string;
  to_amount_min: string;
  estimated_duration_seconds: number;
  transaction_request: Record<string, unknown> | null;
}

export interface ReceiveStatusResponse {
  status: string;
  sub_status: string | null;
  sub_status_message: string | null;
  receiving_tx_hash: string | null;
}

// ── API client ───────────────────────────────────────────────────
export const api = {
  // Auth
  requestNonce: () => request<NonceResponse>("/auth/nonce", { method: "POST" }),
  createSession: (suiAddress: string, nonce: string, signature: string) =>
    request<SessionResponse>("/auth/session", {
      method: "POST",
      body: JSON.stringify({ sui_address: suiAddress, nonce, signature }),
    }),
  me:     () => request<MeResponse>("/auth/me"),
  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),

  // PIN
  pinStatus:  () => request<PinStatusResponse>("/pin/status"),
  setPin: (pin: string) =>
    request<{ ok: boolean }>("/pin/set", { method: "POST", body: JSON.stringify({ pin }) }),
  requestPinReset: (nonce: string, signature: string) =>
    request<{ reset_token: string; available_at: string }>("/pin/reset/request", {
      method: "POST",
      body: JSON.stringify({ nonce, signature }),
    }),
  confirmPinReset: (resetToken: string, newPin: string) =>
    request<{ ok: boolean }>("/pin/reset/confirm", {
      method: "POST",
      body: JSON.stringify({ reset_token: resetToken, new_pin: newPin }),
    }),

  // Handles
  searchHandles: (platform: string, query: string) =>
    request<SearchResult[]>(`/handles/search?${new URLSearchParams({ platform, query })}`),
  listHandles: () => request<BoundHandleOut[]>("/handles/mine"),
  startEmailBind: (email: string) =>
    request<{ ok: boolean }>("/handles/email/start", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  confirmEmailBind: (token: string) =>
    request<BoundHandleOut>("/handles/email/confirm", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  unbindHandle: (platform: string, handle: string, pin: string) =>
    request<{ ok: boolean }>("/handles/unbind", {
      method: "POST",
      body: JSON.stringify({ platform, handle, pin }),
    }),

  // Send
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

  // Dashboard
  getBalances:       () => request<BalanceOut[]>("/dashboard/balances"),
  getHistory:        () => request<HistoryItem[]>("/dashboard/history"),
  decryptHistoryItem: (recordId: number) =>
    request<HistoryDecrypted>(`/dashboard/history/${recordId}/decrypt`),
  getVolume:         () => request<PersonalVolume>("/dashboard/volume"),
  getPlatformVolume: () => request<PlatformVolume>("/dashboard/volume/platform"),

  // Swap (Aftermath Finance — Sui-native)
  swapQuote: (coinInType: string, coinOutType: string, amountIn: string) =>
    request<SwapQuoteResponse>("/swap/quote", {
      method: "POST",
      body: JSON.stringify({ coin_in_type: coinInType, coin_out_type: coinOutType, amount_in: amountIn }),
    }),
  swapExecute: (quoteId: number, pin: string, slippage?: number) =>
    request<SwapExecuteResponse>("/swap/execute", {
      method: "POST",
      body: JSON.stringify({ quote_id: quoteId, pin, ...(slippage !== undefined && { slippage }) }),
    }),

  // Receive (LI.FI cross-chain)
  receiveQuote: (fromChain: string, fromToken: string, fromAmount: string, fromAddress: string) =>
    request<ReceiveQuoteResponse>("/receive/quote", {
      method: "POST",
      body: JSON.stringify({ from_chain: fromChain, from_token: fromToken, from_amount: fromAmount, from_address: fromAddress }),
    }),
  receiveStatus: (recordId: number) =>
    request<ReceiveStatusResponse>(`/receive/status/${recordId}`),
};
