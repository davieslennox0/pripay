import { useState } from "react";
import { api, type SwapExecuteResponse, type SwapQuoteResponse } from "../lib/api";

const SUI_COIN = "0x2::sui::SUI";
const ZUSDC_COIN = import.meta.env.VITE_ZUSDC_COIN_TYPE as string | undefined
  ?? "0x228245f74e01948d43ef584c0e94e160874e7936434e2e390eec7228db2b61ba::zusdc::ZUSDC";

const KNOWN_COINS: { type: string; symbol: string; decimals: number }[] = [
  { type: SUI_COIN,   symbol: "SUI",   decimals: 9 },
  { type: ZUSDC_COIN, symbol: "zUSDC", decimals: 6 },
];

function coinLabel(t: string) {
  const k = KNOWN_COINS.find((c) => c.type === t);
  return k ? k.symbol : t.split("::").pop() ?? t.slice(0, 10);
}

function toBaseUnits(amount: string, coinType: string): string {
  const n = parseFloat(amount);
  if (!Number.isFinite(n) || n <= 0) return "0";
  const dec = KNOWN_COINS.find((c) => c.type === coinType)?.decimals ?? 9;
  return Math.round(n * 10 ** dec).toString();
}

function fromBaseUnits(raw: string, coinType: string): string {
  const dec = KNOWN_COINS.find((c) => c.type === coinType)?.decimals ?? 9;
  const n = Number(raw) / 10 ** dec;
  return n.toFixed(dec > 6 ? 6 : dec);
}

// ── Swap arrow ────────────────────────────────────────────────────
const SwapArrowIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19"/>
    <polyline points="19 12 12 19 5 12"/>
  </svg>
);

const CheckIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

export function Swap() {
  const [coinIn,   setCoinIn]   = useState(SUI_COIN);
  const [coinOut,  setCoinOut]  = useState(ZUSDC_COIN);
  const [amountIn, setAmountIn] = useState("");
  const [customIn, setCustomIn] = useState(false);
  const [customOut,setCustomOut]= useState(false);

  const [quote,    setQuote]    = useState<SwapQuoteResponse | null>(null);
  const [quoting,  setQuoting]  = useState(false);
  const [quoteErr, setQuoteErr] = useState<string | null>(null);

  const [pin,      setPin]      = useState("");
  const [result,   setResult]   = useState<SwapExecuteResponse | null>(null);
  const [executing,setExecuting]= useState(false);
  const [execErr,  setExecErr]  = useState<string | null>(null);

  async function getQuote() {
    if (!amountIn || !coinIn || !coinOut) return;
    setQuoting(true);
    setQuoteErr(null);
    setQuote(null);
    try {
      const baseUnits = toBaseUnits(amountIn, coinIn);
      const q = await api.swapQuote(coinIn, coinOut, baseUnits);
      setQuote(q);
    } catch (e) {
      setQuoteErr(e instanceof Error ? e.message : "Failed to get quote");
    } finally {
      setQuoting(false);
    }
  }

  async function execute() {
    if (!quote) return;
    setExecuting(true);
    setExecErr(null);
    try {
      const res = await api.swapExecute(quote.quote_id, pin);
      setResult(res);
    } catch (e) {
      setExecErr(e instanceof Error ? e.message : "Swap failed");
    } finally {
      setExecuting(false);
    }
  }

  function flip() {
    const tmp = coinIn;
    setCoinIn(coinOut);
    setCoinOut(tmp);
    setQuote(null);
    setAmountIn("");
  }

  if (result) {
    return (
      <div>
        <div className="page-header"><div className="page-title">Swap</div></div>
        <div className="flow-container">
          <div className="card" style={{ textAlign: "center", padding: "40px 24px" }}>
            <div className="send-success-icon" style={{ margin: "0 auto 16px" }}><CheckIcon /></div>
            <h2 style={{ fontSize: "20px", fontWeight: 700, color: "var(--text)", marginBottom: "8px" }}>Swap Submitted</h2>
            <p className="text-sm" style={{ color: "var(--text-2)", marginBottom: "4px" }}>
              Status: <strong style={{ color: "var(--green)" }}>{result.status}</strong>
            </p>
            {result.tx_ref && (
              <p className="text-xs text-mono" style={{ color: "var(--text-3)", marginTop: "8px" }}>
                Tx: {result.tx_ref}
              </p>
            )}
            <button
              type="button"
              className="btn btn-primary"
              style={{ marginTop: "24px" }}
              onClick={() => { setResult(null); setQuote(null); setPin(""); setAmountIn(""); }}
            >
              New Swap
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
          <div className="page-title">Swap</div>
          <div className="page-subtitle">Swap Sui tokens via Aftermath Finance</div>
        </div>
      </div>

      <div className="flow-container">
        <div className="card">
          {/* From */}
          <div className="coin-input-group">
            <label>You Pay</label>
            <div style={{ marginBottom: "10px" }}>
              {customIn ? (
                <input
                  className="coin-type-input"
                  style={{ width: "100%", background: "transparent", border: "none", outline: "none", padding: 0 }}
                  placeholder="Coin type (e.g. 0x2::sui::SUI)"
                  value={coinIn}
                  onChange={(e) => { setCoinIn(e.target.value); setQuote(null); }}
                  onBlur={() => { if (!coinIn) setCustomIn(false); }}
                />
              ) : (
                <div style={{ display: "flex", gap: "8px" }}>
                  {KNOWN_COINS.map((c) => (
                    <button
                      key={c.type}
                      type="button"
                      className={`chain-btn${coinIn === c.type ? " active" : ""}`}
                      onClick={() => { setCoinIn(c.type); setQuote(null); }}
                    >
                      {c.symbol}
                    </button>
                  ))}
                  <button type="button" className="chain-btn" onClick={() => setCustomIn(true)}>Custom</button>
                </div>
              )}
            </div>
            <div className="coin-input-row">
              <input
                className="amount-input-large"
                type="number"
                placeholder="0.00"
                min="0"
                step="0.001"
                value={amountIn}
                onChange={(e) => { setAmountIn(e.target.value); setQuote(null); }}
              />
              <span style={{ color: "var(--text-3)", fontSize: "14px", flexShrink: 0 }}>
                {coinLabel(coinIn)}
              </span>
            </div>
          </div>

          {/* Flip arrow */}
          <div className="swap-arrow">
            <button type="button" className="swap-arrow-btn" onClick={flip} title="Flip tokens">
              <SwapArrowIcon />
            </button>
          </div>

          {/* To */}
          <div className="coin-input-group" style={{ marginTop: "12px" }}>
            <label>You Receive</label>
            <div style={{ marginBottom: "10px" }}>
              {customOut ? (
                <input
                  className="coin-type-input"
                  style={{ width: "100%", background: "transparent", border: "none", outline: "none", padding: 0 }}
                  placeholder="Coin type"
                  value={coinOut}
                  onChange={(e) => { setCoinOut(e.target.value); setQuote(null); }}
                  onBlur={() => { if (!coinOut) setCustomOut(false); }}
                />
              ) : (
                <div style={{ display: "flex", gap: "8px" }}>
                  {KNOWN_COINS.filter((c) => c.type !== coinIn).map((c) => (
                    <button
                      key={c.type}
                      type="button"
                      className={`chain-btn${coinOut === c.type ? " active" : ""}`}
                      onClick={() => { setCoinOut(c.type); setQuote(null); }}
                    >
                      {c.symbol}
                    </button>
                  ))}
                  <button type="button" className="chain-btn" onClick={() => setCustomOut(true)}>Custom</button>
                </div>
              )}
            </div>
            <div className="coin-input-row">
              <span className="amount-input-large" style={{ color: quote ? "var(--text)" : "var(--text-3)", fontSize: "22px", fontWeight: 600 }}>
                {quote ? fromBaseUnits(quote.amount_out, coinOut) : "—"}
              </span>
              <span style={{ color: "var(--text-3)", fontSize: "14px", flexShrink: 0 }}>
                {coinLabel(coinOut)}
              </span>
            </div>
          </div>

          {quoteErr && <div className="error-msg mt-12">{quoteErr}</div>}

          {quote && (
            <div className="quote-box mt-12">
              Rate: <strong>1 {coinLabel(coinIn)} ≈ {quote.spot_price.toFixed(6)} {coinLabel(coinOut)}</strong>
              {" · "}Fee: <strong>{(quote.net_trade_fee_percentage * 100).toFixed(2)}%</strong>
            </div>
          )}

          {!quote ? (
            <button
              type="button"
              className="btn btn-primary btn-block"
              style={{ marginTop: "20px" }}
              disabled={!amountIn || !coinIn || !coinOut || coinIn === coinOut || quoting}
              onClick={getQuote}
            >
              {quoting ? <span className="spinner" /> : "Get Quote"}
            </button>
          ) : (
            <div>
              <div className="field" style={{ marginTop: "16px" }}>
                <label className="field-label">Transaction PIN</label>
                <input
                  type="password"
                  inputMode="numeric"
                  placeholder="Enter your PIN to confirm"
                  value={pin}
                  onChange={(e) => setPin(e.target.value)}
                />
              </div>
              {execErr && <div className="error-msg">{execErr}</div>}
              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  type="button"
                  className="btn btn-ghost"
                  style={{ flex: 1 }}
                  onClick={() => { setQuote(null); setPin(""); }}
                >
                  Back
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                  disabled={!pin || executing}
                  onClick={execute}
                >
                  {executing ? <span className="spinner" /> : "Confirm Swap"}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="info-msg mt-12">
          Swaps are routed through Aftermath Finance on Sui. Testnet availability depends on Aftermath's pool support.
        </div>
      </div>
    </div>
  );
}
