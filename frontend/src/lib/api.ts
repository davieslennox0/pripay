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
};
