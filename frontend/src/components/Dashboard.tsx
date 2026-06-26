import { useEffect, useRef, useState } from "react";
import { useSignPersonalMessage } from "@mysten/dapp-kit";
import {
  Chart,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
} from "chart.js";
import { Line } from "react-chartjs-2";
import {
  api,
  type BalanceOut,
  type BoundHandleOut,
  type HistoryDecrypted,
  type HistoryItem,
  type PersonalVolume,
  type PlatformVolume,
} from "../lib/api";
import { signNonce } from "../lib/wallet";

Chart.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip);

const PIN_RESET_KEY = "zenpay.pendingPinReset";

// ── Icons ─────────────────────────────────────────────────────────
const ArrowUp   = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>;
const ArrowDown = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>;
const RefreshIcon=()=> <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>;
const LockIcon  = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>;

// ── Helpers ────────────────────────────────────────────────────────
function fmtUsd(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
}

function symbolAbbr(coinType: string, symbol: string | null) {
  if (symbol) return symbol.slice(0, 6);
  return coinType.split("::").pop()?.slice(0, 6) ?? "?";
}

function txIcon(kind: string, direction: string | null) {
  if (kind === "send") {
    if (direction === "out") return { cls: "tx-icon-send",    el: <ArrowUp /> };
    return { cls: "tx-icon-receive", el: <ArrowDown /> };
  }
  if (kind === "receive") return { cls: "tx-icon-receive", el: <ArrowDown /> };
  if (kind === "swap")    return { cls: "tx-icon-swap",    el: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg> };
  return { cls: "tx-icon-default", el: null };
}

function statusCls(s: string) {
  if (s === "settled") return "tx-status-settled";
  if (s === "pending") return "tx-status-pending";
  if (s === "escrow")  return "tx-status-escrow";
  return "tx-status-failed";
}

// ── Portfolio activity chart ──────────────────────────────────────
function ActivityChart({ items }: { items: HistoryItem[] }) {
  const isDark = document.documentElement.dataset.theme !== "light";
  const accent  = isDark ? "#8B5CF6" : "#6366F1";
  const gridCol = isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)";
  const textCol = isDark ? "#64748B" : "#94A3B8";

  const months: Record<string, number> = {};
  const now = new Date();
  for (let i = 5; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const key = d.toLocaleString("en-US", { month: "short" });
    months[key] = 0;
  }
  for (const item of items) {
    const d = new Date(item.created_at);
    const key = d.toLocaleString("en-US", { month: "short" });
    if (key in months) months[key]++;
  }

  const labels = Object.keys(months);
  const data   = Object.values(months);

  return (
    <Line
      data={{
        labels,
        datasets: [{
          data,
          borderColor: accent,
          backgroundColor: `${accent}22`,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: accent,
          pointRadius: 4,
          pointHoverRadius: 6,
          borderWidth: 2,
        }],
      }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ${ctx.parsed.y} transaction${ctx.parsed.y !== 1 ? "s" : ""}`,
            },
          },
        },
        scales: {
          x: {
            grid: { color: gridCol },
            ticks: { color: textCol, font: { family: "'Inter', sans-serif", size: 11 } },
          },
          y: {
            beginAtZero: true,
            grid: { color: gridCol },
            ticks: { color: textCol, font: { family: "'Inter', sans-serif", size: 11 }, stepSize: 1 },
          },
        },
      }}
    />
  );
}

// ── Dashboard ─────────────────────────────────────────────────────
export function Dashboard() {
  const [balances,  setBalances]  = useState<BalanceOut[] | null>(null);
  const [history,   setHistory]   = useState<HistoryItem[] | null>(null);
  const [volume,    setVolume]    = useState<PersonalVolume | null>(null);
  const [platform,  setPlatform]  = useState<PlatformVolume | null>(null);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState<string | null>(null);
  const [decrypted, setDecrypted] = useState<Record<number, HistoryDecrypted>>({});

  function load() {
    setLoading(true);
    setError(null);
    Promise.all([
      api.getBalances().catch(() => [] as BalanceOut[]),
      api.getHistory().catch(() => [] as HistoryItem[]),
      api.getVolume().catch(() => null),
      api.getPlatformVolume().catch(() => null),
    ]).then(([b, h, v, p]) => {
      setBalances(b);
      setHistory(h);
      setVolume(v);
      setPlatform(p);
    }).catch((e) => setError(e instanceof Error ? e.message : "Failed to load")).finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function decrypt(recordId: number) {
    try {
      const payload = await api.decryptHistoryItem(recordId);
      setDecrypted((prev) => ({ ...prev, [recordId]: payload }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Decryption failed");
    }
  }

  const totalUsd = balances?.reduce((s, b) => s + (b.value_usd ?? 0), 0) ?? 0;
  const knownBalances = balances?.filter((b) => b.symbol !== null) ?? [];

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
        <div className="spinner" style={{ width: "32px", height: "32px" }} />
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Dashboard</div>
          <div className="page-subtitle">Your ZenPay overview</div>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={load} style={{ gap: "6px" }}>
          <RefreshIcon />Refresh
        </button>
      </div>

      {error && <div className="error-msg mb-16">{error}</div>}

      {/* Stats row */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Portfolio Value</div>
          <div className="stat-value">{fmtUsd(totalUsd)}</div>
          <div className="stat-sub">{knownBalances.length} token{knownBalances.length !== 1 ? "s" : ""}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Sent</div>
          <div className="stat-value">{volume ? fmtUsd(volume.total_sent) : "—"}</div>
          <div className="stat-sub">{volume ? `${volume.swap_count} swap${volume.swap_count !== 1 ? "s" : ""}` : ""}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Received</div>
          <div className="stat-value">{volume ? fmtUsd(volume.total_received) : "—"}</div>
          <div className="stat-sub">{platform ? `${platform.send_count} platform tx` : ""}</div>
        </div>
      </div>

      <div className="grid-2 mb-24">
        {/* Balances */}
        <div className="card">
          <div className="card-title">Balances</div>
          {knownBalances.length === 0 ? (
            <div className="empty-state">No tokens found</div>
          ) : (
            <div className="token-list">
              {knownBalances.map((b) => (
                <div className="token-row" key={b.coin_type}>
                  <div className="token-icon">{symbolAbbr(b.coin_type, b.symbol)}</div>
                  <div className="token-info">
                    <div className="token-symbol">{b.symbol ?? symbolAbbr(b.coin_type, null)}</div>
                    <div className="token-amount">{b.amount?.toFixed(4) ?? b.balance}</div>
                  </div>
                  <div>
                    <div className="token-value">{b.value_usd !== null ? fmtUsd(b.value_usd) : "—"}</div>
                    {b.price_usd !== null && (
                      <div className="token-price">{fmtUsd(b.price_usd)}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Activity chart */}
        <div className="card">
          <div className="card-title">Transaction Activity</div>
          {history !== null && history.length > 0 ? (
            <div style={{ height: "180px", position: "relative" }}>
              <ActivityChart items={history} />
            </div>
          ) : (
            <div className="empty-state">No activity yet</div>
          )}
        </div>
      </div>

      {/* History */}
      <div className="card">
        <div className="card-title">Transaction History</div>
        {history === null || history.length === 0 ? (
          <div className="empty-state">No transactions yet</div>
        ) : (
          <div className="tx-list">
            {history.map((item) => {
              const { cls, el } = txIcon(item.kind, item.direction);
              const d = decrypted[item.record_id];
              return (
                <div className="tx-row" key={`${item.kind}-${item.record_id}`}>
                  <div className={`tx-icon ${cls}`}>{el}</div>
                  <div className="tx-info">
                    <div className="tx-title">
                      {item.kind.charAt(0).toUpperCase() + item.kind.slice(1)}
                      {item.direction ? ` · ${item.direction}` : ""}
                      {item.counterparty ? ` — ${item.counterparty}` : ""}
                    </div>
                    <div className="tx-date">{new Date(item.created_at).toLocaleString()}</div>
                    {d && (
                      <div className="tx-decrypted">
                        {d.amount} {d.token}{d.memo ? ` · "${d.memo}"` : ""}
                      </div>
                    )}
                  </div>
                  <div className="tx-meta">
                    <div className={`tx-status ${statusCls(item.status)}`}>{item.status}</div>
                    {item.can_decrypt && !d && (
                      <button
                        type="button"
                        className="tx-decrypt-btn"
                        onClick={() => decrypt(item.record_id)}
                      >
                        <LockIcon /> Decrypt
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Handles & Security */}
      <div className="grid-2 mt-16" style={{ marginTop: "16px" }}>
        <BoundHandles />
        <SecuritySection />
      </div>
    </div>
  );
}

// ── Bound Handles ─────────────────────────────────────────────────
function BoundHandles() {
  const [handles, setHandles] = useState<BoundHandleOut[] | null>(null);
  const [email, setEmail] = useState("");
  const [bindStarted, setBindStarted] = useState(false);
  const [unbindPin, setUnbindPin] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    api.listHandles().then(setHandles).catch(() => setHandles([]));
  }
  useEffect(refresh, []);

  async function startBind() {
    setError(null);
    try {
      await api.startEmailBind(email);
      setBindStarted(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start binding");
    }
  }

  async function unbind(platform: string, handle: string) {
    setError(null);
    try {
      await api.unbindHandle(platform, handle, unbindPin[`${platform}:${handle}`] ?? "");
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to unbind");
    }
  }

  return (
    <div className="card">
      <div className="card-title">Bound Handles</div>
      {error && <div className="error-msg mb-8">{error}</div>}

      {handles !== null && handles.length === 0 && (
        <div className="empty-state" style={{ padding: "16px 0" }}>No handles bound yet</div>
      )}

      {handles !== null && handles.map((h) => (
        <div className="handle-row" key={`${h.platform}:${h.handle}`}>
          <span className="handle-badge">{h.platform}</span>
          <span className="handle-name">{h.handle}</span>
          <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
            <input
              type="password"
              inputMode="numeric"
              placeholder="PIN"
              style={{ width: "70px", padding: "5px 8px", fontSize: "13px" }}
              value={unbindPin[`${h.platform}:${h.handle}`] ?? ""}
              onChange={(e) => setUnbindPin((p) => ({ ...p, [`${h.platform}:${h.handle}`]: e.target.value }))}
            />
            <button
              type="button"
              className="btn btn-danger btn-sm"
              onClick={() => unbind(h.platform, h.handle)}
            >
              Unbind
            </button>
          </div>
        </div>
      ))}

      <div className="divider" />

      {bindStarted ? (
        <div className="info-msg">Check your email for a verification link.</div>
      ) : (
        <div style={{ display: "flex", gap: "8px" }}>
          <input
            type="email"
            placeholder="Bind an email address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={!email}
            onClick={startBind}
            style={{ flexShrink: 0 }}
          >
            Bind
          </button>
        </div>
      )}
    </div>
  );
}

// ── Security ──────────────────────────────────────────────────────
function SecuritySection() {
  const [pending, setPending] = useState<{ resetToken: string; availableAt: string } | null>(() => {
    const raw = localStorage.getItem(PIN_RESET_KEY);
    return raw ? JSON.parse(raw) : null;
  });
  const [newPin, setNewPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const { mutateAsync: signPersonalMessage } = useSignPersonalMessage();
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!pending) return;
    timerRef.current = setInterval(() => setNow(Date.now()), 1000);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [pending]);

  function save(v: typeof pending) {
    setPending(v);
    if (v) localStorage.setItem(PIN_RESET_KEY, JSON.stringify(v));
    else localStorage.removeItem(PIN_RESET_KEY);
  }

  async function startReset() {
    setError(null);
    try {
      const { nonce, signature } = await signNonce(signPersonalMessage);
      const { reset_token, available_at } = await api.requestPinReset(nonce, signature);
      save({ resetToken: reset_token, availableAt: available_at });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to request PIN reset");
    }
  }

  async function confirmReset() {
    if (!pending) return;
    setError(null);
    try {
      await api.confirmPinReset(pending.resetToken, newPin);
      setDone(true);
      save(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to reset PIN");
    }
  }

  const remaining = pending ? Math.max(0, new Date(pending.availableAt).getTime() - now) : 0;

  return (
    <div className="card">
      <div className="card-title">Security</div>
      {error && <div className="error-msg mb-8">{error}</div>}

      {done && <div className="success-msg">PIN has been reset.</div>}

      {!pending && !done && (
        <div>
          <p className="text-sm" style={{ color: "var(--text-2)", marginBottom: "16px" }}>
            Reset your transaction PIN with a fresh wallet signature.
          </p>
          <button type="button" className="btn btn-ghost btn-sm" onClick={startReset}>
            Reset PIN
          </button>
        </div>
      )}

      {pending && remaining > 0 && (
        <div className="info-msg">
          Reset requested — available in {Math.ceil(remaining / 1000)}s
        </div>
      )}

      {pending && remaining <= 0 && (
        <div style={{ display: "flex", gap: "8px" }}>
          <input
            type="password"
            inputMode="numeric"
            placeholder="New 4–6 digit PIN"
            value={newPin}
            onChange={(e) => setNewPin(e.target.value)}
          />
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={newPin.length < 4}
            onClick={confirmReset}
            style={{ flexShrink: 0 }}
          >
            Confirm
          </button>
        </div>
      )}
    </div>
  );
}
