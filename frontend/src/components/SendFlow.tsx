import { useEffect, useState } from "react";
import { api, type SearchResult, type SendExecuteResponse } from "../lib/api";

// ── Platform definitions ──────────────────────────────────────────
const PLATFORMS = [
  {
    id: "email",
    label: "Email",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
        <polyline points="22,6 12,13 2,6"/>
      </svg>
    ),
  },
  {
    id: "twitter",
    label: "X (Twitter)",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.744l7.73-8.835L1.254 2.25H8.08l4.253 5.622 5.911-5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
      </svg>
    ),
  },
  {
    id: "discord",
    label: "Discord",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
        <path d="M20.317 4.492c-1.53-.69-3.17-1.2-4.885-1.49a.075.075 0 0 0-.079.036c-.21.369-.444.85-.608 1.23a18.566 18.566 0 0 0-5.487 0 12.36 12.36 0 0 0-.617-1.23A.077.077 0 0 0 8.562 3c-1.714.29-3.354.8-4.885 1.491a.07.07 0 0 0-.032.027C.533 9.093-.32 13.555.099 17.961a.08.08 0 0 0 .031.055 20.03 20.03 0 0 0 5.993 2.98.078.078 0 0 0 .084-.026c.462-.62.874-1.275 1.226-1.963.021-.04.001-.088-.041-.104a13.201 13.201 0 0 1-1.872-.878.075.075 0 0 1-.008-.125c.126-.093.252-.19.372-.287a.075.075 0 0 1 .078-.01c3.927 1.764 8.18 1.764 12.061 0a.075.075 0 0 1 .079.009c.12.098.245.195.372.288a.075.075 0 0 1-.006.125c-.598.344-1.22.635-1.873.877a.075.075 0 0 0-.041.105c.36.687.772 1.341 1.225 1.962a.077.077 0 0 0 .084.028 19.963 19.963 0 0 0 6.002-2.981.076.076 0 0 0 .032-.054c.5-5.094-.838-9.52-3.549-13.442a.06.06 0 0 0-.031-.028zM8.02 15.278c-1.182 0-2.157-1.069-2.157-2.38 0-1.312.956-2.38 2.157-2.38 1.21 0 2.176 1.077 2.157 2.38 0 1.312-.956 2.38-2.157 2.38zm7.975 0c-1.183 0-2.157-1.069-2.157-2.38 0-1.312.955-2.38 2.157-2.38 1.21 0 2.176 1.077 2.157 2.38 0 1.312-.946 2.38-2.157 2.38z"/>
      </svg>
    ),
  },
  {
    id: "telegram",
    label: "Telegram",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
        <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
      </svg>
    ),
  },
  {
    id: "facebook",
    label: "Facebook",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
      </svg>
    ),
  },
  {
    id: "twitch",
    label: "Twitch",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
        <path d="M11.571 4.714h1.715v5.143H11.57zm4.715 0H18v5.143h-1.714zM6 0L1.714 4.286v15.428h5.143V24l4.286-4.286h3.428L22.286 12V0zm14.571 11.143l-3.428 3.428h-3.429l-3 3v-3H6.857V1.714h13.714z"/>
      </svg>
    ),
  },
] as const;

type PlatformId = typeof PLATFORMS[number]["id"];

// ── Icons ─────────────────────────────────────────────────────────
const CheckIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

export function SendFlow() {
  const [step,     setStep]     = useState<1 | 2 | 3>(1);
  const [platform, setPlatform] = useState<PlatformId>("email");
  const [query,    setQuery]    = useState("");
  const [results,  setResults]  = useState<SearchResult[]>([]);
  const [handle,   setHandle]   = useState("");
  const [amount,   setAmount]   = useState("");
  const [fee,      setFee]      = useState<number | null>(null);
  const [receiverGets, setReceiverGets] = useState<number | null>(null);
  const [quoteError,   setQuoteError]   = useState<string | null>(null);
  const [pin,      setPin]      = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [result,   setResult]   = useState<SendExecuteResponse | null>(null);

  // Handle search typeahead
  useEffect(() => {
    if (!query.trim()) { setResults([]); return; }
    const id = setTimeout(() => {
      api.searchHandles(platform, query).then(setResults).catch(() => setResults([]));
    }, 300);
    return () => clearTimeout(id);
  }, [platform, query]);

  // Quote debounce
  useEffect(() => {
    if (!handle || !amount) { setReceiverGets(null); setFee(null); return; }
    const parsed = Number(amount);
    if (!Number.isFinite(parsed) || parsed <= 0) return;
    const id = setTimeout(() => {
      api.sendQuote(platform, handle, parsed)
        .then((q) => { setReceiverGets(q.receiver_gets); setFee(q.fee); setQuoteError(null); })
        .catch((e) => { setReceiverGets(null); setFee(null); setQuoteError(e instanceof Error ? e.message : "Quote failed"); });
    }, 400);
    return () => clearTimeout(id);
  }, [platform, handle, amount]);

  async function submit() {
    setSubmitError(null);
    setSubmitting(true);
    try {
      const res = await api.sendExecute(platform, handle, Number(amount), pin);
      setResult(res);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Send failed");
    } finally {
      setSubmitting(false);
    }
  }

  function reset() {
    setStep(1); setPlatform("email"); setQuery(""); setHandle(""); setAmount("");
    setFee(null); setReceiverGets(null); setQuoteError(null);
    setPin(""); setResult(null); setSubmitError(null);
  }

  if (result) {
    const claimLink = result.claim_token
      ? `${window.location.origin}/?claim_token=${result.claim_token}`
      : null;
    return (
      <div>
        <div className="page-header">
          <div className="page-title">Send</div>
        </div>
        <div className="flow-container">
          <div className="card send-success">
            <div className="send-success-icon"><CheckIcon /></div>
            <h2 style={{ fontSize: "20px", fontWeight: 700, color: "var(--text)", marginBottom: "8px" }}>Payment Sent</h2>
            <p className="text-sm" style={{ color: "var(--text-2)", marginBottom: "20px" }}>
              Status: <strong style={{ color: "var(--green)" }}>{result.status}</strong>
              {" · "}Recipient gets: <strong>{result.receiver_gets} USDC</strong>
            </p>
            {claimLink && (
              <div className="claim-box">
                <div>Recipient hasn't bound this handle yet — share the claim link:</div>
                <code>{claimLink}</code>
              </div>
            )}
            {result.tx_ref && (
              <p className="text-xs text-mono" style={{ color: "var(--text-3)", marginTop: "12px" }}>
                Tx: {result.tx_ref}
              </p>
            )}
            <button type="button" className="btn btn-primary" style={{ marginTop: "24px" }} onClick={reset}>
              Send Another
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Send</div>
          <div className="page-subtitle">Pay to any social handle</div>
        </div>
      </div>

      <div className="flow-container">
        {/* Step indicator */}
        <div className="step-indicator" style={{ marginBottom: "28px" }}>
          {[1, 2, 3].map((s) => (
            <>
              <div
                key={`dot-${s}`}
                className={`step-dot${step === s ? " active" : step > s ? " done" : ""}`}
              >
                {step > s ? <CheckIcon /> : s}
              </div>
              {s < 3 && (
                <div key={`line-${s}`} className={`step-line${step > s ? " done" : ""}`} />
              )}
            </>
          ))}
        </div>

        <div className="card">
          {/* ── Step 1: Platform + Handle ── */}
          {step === 1 && (
            <div>
              <div className="card-title">Choose Platform</div>
              <div className="platform-grid">
                {PLATFORMS.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className={`platform-btn${platform === p.id ? " selected" : ""}`}
                    onClick={() => { setPlatform(p.id); setHandle(""); setQuery(""); setResults([]); }}
                  >
                    <div className="platform-icon">{p.icon}</div>
                    {p.label}
                  </button>
                ))}
              </div>

              <div className="card-title" style={{ marginTop: "8px" }}>Recipient Handle</div>
              <div className="field" style={{ marginBottom: "0" }}>
                <input
                  type="text"
                  placeholder={platform === "email" ? "recipient@example.com" : `@${platform}_handle`}
                  value={query}
                  onChange={(e) => { setQuery(e.target.value); setHandle(e.target.value); if (!e.target.value) setResults([]); }}
                  autoComplete="off"
                />
                {results.length > 0 && (
                  <div className="suggestions" style={{ marginTop: "4px" }}>
                    {results.map((r) => (
                      <button
                        key={r.sui_address}
                        type="button"
                        className="suggestion-item"
                        onClick={() => { setHandle(r.handle); setQuery(r.handle); setResults([]); }}
                      >
                        <span style={{ fontFamily: "var(--mono)", fontSize: "13px" }}>{r.handle}</span>
                        <span className="text-xs text-muted" style={{ marginLeft: "auto" }}>
                          {r.sui_address.slice(0, 8)}…
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <button
                type="button"
                className="btn btn-primary btn-block"
                style={{ marginTop: "20px" }}
                disabled={!handle.trim()}
                onClick={() => setStep(2)}
              >
                Continue
              </button>
            </div>
          )}

          {/* ── Step 2: Amount + Quote ── */}
          {step === 2 && (
            <div>
              <div className="card-title">Payment Details</div>
              <div className="field">
                <label className="field-label">Sending to</label>
                <div style={{ fontSize: "14px", color: "var(--text)", fontFamily: "var(--mono)", padding: "10px 0" }}>
                  {platform}:{handle}
                </div>
              </div>
              <div className="field">
                <label className="field-label">Amount (USDC)</label>
                <input
                  type="number"
                  placeholder="0.00"
                  min="0.15"
                  step="0.01"
                  value={amount}
                  onChange={(e) => { setAmount(e.target.value); setReceiverGets(null); setFee(null); setQuoteError(null); }}
                  style={{ fontSize: "18px", fontWeight: 600 }}
                />
              </div>

              {quoteError && <div className="error-msg">{quoteError}</div>}

              {receiverGets !== null && (
                <div className="quote-box">
                  Platform fee: <strong>${fee?.toFixed(2)}</strong>
                  {" · "}Recipient receives: <strong>{receiverGets.toFixed(2)} USDC</strong>
                </div>
              )}

              <div style={{ display: "flex", gap: "10px", marginTop: "20px" }}>
                <button type="button" className="btn btn-ghost" style={{ flex: 1 }} onClick={() => setStep(1)}>
                  Back
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                  disabled={!amount || Number(amount) <= 0}
                  onClick={() => setStep(3)}
                >
                  Continue
                </button>
              </div>
            </div>
          )}

          {/* ── Step 3: PIN Confirm ── */}
          {step === 3 && (
            <div>
              <div className="card-title">Confirm with PIN</div>

              <div style={{ background: "var(--surface-2)", borderRadius: "var(--radius-sm)", padding: "14px", marginBottom: "20px", fontSize: "13px", color: "var(--text-2)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                  <span>To</span>
                  <span style={{ fontFamily: "var(--mono)", color: "var(--text)" }}>{platform}:{handle}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                  <span>Amount</span>
                  <span style={{ color: "var(--text)", fontWeight: 600 }}>{amount} USDC</span>
                </div>
                {receiverGets !== null && (
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>Recipient gets</span>
                    <span style={{ color: "var(--green)", fontWeight: 600 }}>{receiverGets.toFixed(2)} USDC</span>
                  </div>
                )}
              </div>

              <div className="field">
                <label className="field-label">Transaction PIN</label>
                <input
                  type="password"
                  inputMode="numeric"
                  placeholder="Enter your PIN"
                  value={pin}
                  onChange={(e) => setPin(e.target.value)}
                  autoComplete="current-password"
                />
              </div>

              {submitError && <div className="error-msg">{submitError}</div>}

              <div style={{ display: "flex", gap: "10px", marginTop: "8px" }}>
                <button type="button" className="btn btn-ghost" style={{ flex: 1 }} onClick={() => setStep(2)}>
                  Back
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                  disabled={!pin || submitting}
                  onClick={submit}
                >
                  {submitting ? <span className="spinner" /> : "Send Payment"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
