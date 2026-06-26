import { useState } from "react";
import { api, type ReceiveQuoteResponse } from "../lib/api";

const CHAINS: { key: string; name: string; nativeToken: string; nativeAddress: string }[] = [
  { key: "ETH", name: "Ethereum",  nativeToken: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE", nativeAddress: "" },
  { key: "ARB", name: "Arbitrum",  nativeToken: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE", nativeAddress: "" },
  { key: "BAS", name: "Base",      nativeToken: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE", nativeAddress: "" },
  { key: "OPT", name: "Optimism",  nativeToken: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE", nativeAddress: "" },
  { key: "POL", name: "Polygon",   nativeToken: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE", nativeAddress: "" },
  { key: "AVA", name: "Avalanche", nativeToken: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE", nativeAddress: "" },
];

const USDC_ON_CHAIN: Record<string, string> = {
  ETH: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
  ARB: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
  BAS: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  OPT: "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
  POL: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
  AVA: "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
};

const CopyIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
  </svg>
);

const QrIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
    <rect x="3" y="14" width="7" height="7"/>
    <line x1="14" y1="14" x2="14" y2="14"/><line x1="17" y1="14" x2="17" y2="14"/>
    <line x1="20" y1="14" x2="20" y2="14"/><line x1="14" y1="17" x2="14" y2="17"/>
    <line x1="17" y1="17" x2="17" y2="17"/><line x1="20" y1="20" x2="20" y2="20"/>
    <line x1="14" y1="20" x2="17" y2="20"/><line x1="20" y1="17" x2="20" y2="17"/>
  </svg>
);

export function Receive({ address }: { address: string }) {
  const [chain,       setChain]       = useState("ETH");
  const [fromToken,   setFromToken]   = useState("");
  const [fromAmount,  setFromAmount]  = useState("");
  const [fromAddress, setFromAddress] = useState("");
  const [useUsdc,     setUseUsdc]     = useState(true);
  const [quote,       setQuote]       = useState<ReceiveQuoteResponse | null>(null);
  const [quoting,     setQuoting]     = useState(false);
  const [quoteErr,    setQuoteErr]    = useState<string | null>(null);
  const [copied,      setCopied]      = useState(false);

  const selectedChain = CHAINS.find((c) => c.key === chain)!;
  const resolvedToken  = useUsdc ? (USDC_ON_CHAIN[chain] ?? "") : (fromToken || selectedChain.nativeToken);

  function copyAddress() {
    navigator.clipboard.writeText(address).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  async function getQuote() {
    if (!fromAmount || !fromAddress) return;
    setQuoting(true);
    setQuoteErr(null);
    setQuote(null);
    try {
      const amountBase = Math.round(parseFloat(fromAmount) * 1e6).toString();
      const q = await api.receiveQuote(chain, resolvedToken, amountBase, fromAddress);
      setQuote(q);
    } catch (e) {
      setQuoteErr(e instanceof Error ? e.message : "Failed to get quote");
    } finally {
      setQuoting(false);
    }
  }

  const estimatedMin = quote ? (Number(quote.to_amount_min) / 1e6).toFixed(2) : null;
  const estimatedOut  = quote ? (Number(quote.to_amount) / 1e6).toFixed(2) : null;

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Receive</div>
          <div className="page-subtitle">Get funds from any chain as USDC on Sui</div>
        </div>
      </div>

      <div className="flow-container">
        {/* Your Sui address */}
        <div className="card" style={{ marginBottom: "16px" }}>
          <div className="card-title">Your Sui Address</div>

          <div className="qr-placeholder">
            <QrIcon />
            <span>QR Code</span>
            <span className="text-xs">{address.slice(0, 8)}…</span>
          </div>

          <div className="address-display">
            <div className="address-text">{address}</div>
            <button type="button" className="copy-btn" onClick={copyAddress} title="Copy address">
              {copied ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
              ) : <CopyIcon />}
            </button>
          </div>

          {copied && <div className="success-msg" style={{ marginTop: "4px" }}>Address copied!</div>}
        </div>

        {/* Cross-chain bridge */}
        <div className="card">
          <div className="card-title">Cross-Chain Receive (via LI.FI)</div>

          <div style={{ marginBottom: "16px" }}>
            <label className="field-label">Source Chain</label>
            <div className="chain-grid">
              {CHAINS.map((c) => (
                <button
                  key={c.key}
                  type="button"
                  className={`chain-btn${chain === c.key ? " active" : ""}`}
                  onClick={() => { setChain(c.key); setQuote(null); setFromToken(""); }}
                >
                  {c.name}
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label className="field-label">Token</label>
            <div style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
              <button
                type="button"
                className={`chain-btn${useUsdc ? " active" : ""}`}
                onClick={() => { setUseUsdc(true); setFromToken(""); setQuote(null); }}
              >
                USDC
              </button>
              <button
                type="button"
                className={`chain-btn${!useUsdc ? " active" : ""}`}
                onClick={() => { setUseUsdc(false); setQuote(null); }}
              >
                Native / Custom
              </button>
            </div>
            {!useUsdc && (
              <input
                type="text"
                placeholder="Token contract address"
                value={fromToken}
                onChange={(e) => { setFromToken(e.target.value); setQuote(null); }}
              />
            )}
            {useUsdc && USDC_ON_CHAIN[chain] && (
              <div className="text-xs text-mono" style={{ color: "var(--text-3)", padding: "4px 0" }}>
                {USDC_ON_CHAIN[chain]}
              </div>
            )}
          </div>

          <div className="field">
            <label className="field-label">Amount (in source token)</label>
            <input
              type="number"
              placeholder="0.00"
              min="0"
              step="0.01"
              value={fromAmount}
              onChange={(e) => { setFromAmount(e.target.value); setQuote(null); }}
            />
          </div>

          <div className="field">
            <label className="field-label">Your Source-Chain Address</label>
            <input
              type="text"
              placeholder="0x... (your wallet on the source chain)"
              value={fromAddress}
              onChange={(e) => { setFromAddress(e.target.value); setQuote(null); }}
            />
            <div className="text-xs" style={{ color: "var(--text-3)", marginTop: "4px" }}>
              The wallet you'll send from (required for LI.FI route generation)
            </div>
          </div>

          {quoteErr && <div className="error-msg">{quoteErr}</div>}

          {quote && (
            <div className="quote-box mt-12">
              Via: <strong>{quote.tool}</strong>
              {" · "}You receive: <strong>{estimatedOut} USDC</strong> (min: {estimatedMin} USDC)
              {" · "}ETA: <strong>~{Math.round(quote.estimated_duration_seconds / 60)}min</strong>
            </div>
          )}

          <button
            type="button"
            className="btn btn-primary btn-block"
            style={{ marginTop: "16px" }}
            disabled={!fromAmount || !fromAddress || quoting}
            onClick={getQuote}
          >
            {quoting ? <span className="spinner" /> : "Get Bridge Quote"}
          </button>

          {quote?.transaction_request && (
            <div className="info-msg mt-12">
              Quote obtained. Sign the transaction in your source-chain wallet using the route data from LI.FI.
              The funds will arrive as USDC at your Sui address above.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
