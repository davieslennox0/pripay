import { ConnectButton } from "@mysten/dapp-kit";

const FEATURES = [
  { title: "Non-custodial",     body: "Your keys, your funds — sign in with any Sui wallet." },
  { title: "Handle payments",   body: "Pay by @handle, not wallet address." },
  { title: "Encrypted",         body: "Amounts sealed in a TEE, never exposed on-chain." },
  { title: "Cross-chain",       body: "Receive from ETH, Arbitrum, Base and more." },
];

interface LandingProps {
  connected: boolean;
  signingIn: boolean;
  error: string | null;
  onRetry: () => void;
}

export function Landing({ connected, signingIn, error, onRetry }: LandingProps) {
  return (
    <div className="landing-page">
      <div className="landing-card">
        <div className="landing-logo">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>

        <h1 className="landing-title">ZenPay</h1>
        <p className="landing-tagline">
          Privacy-first social-handle crypto payments on Sui
        </p>

        <div className="landing-features">
          {FEATURES.map((f) => (
            <div className="landing-feature" key={f.title}>
              <h4>{f.title}</h4>
              <p>{f.body}</p>
            </div>
          ))}
        </div>

        {connected ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px" }}>
            {signingIn ? (
              <p style={{ fontSize: "14px", color: "var(--text-2)" }}>
                <span className="spinner" style={{ marginRight: "8px", verticalAlign: "middle" }} />
                Waiting for wallet signature…
              </p>
            ) : (
              <>
                <p style={{ fontSize: "14px", color: "var(--text-2)" }}>Connected. Confirming sign-in.</p>
                {error && (
                  <button type="button" className="btn btn-primary" onClick={onRetry}>
                    Try again
                  </button>
                )}
              </>
            )}
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
            <ConnectButton connectText="Connect Wallet" />
            <p style={{ fontSize: "12px", color: "var(--text-3)" }}>
              Slush or any Sui Wallet Standard wallet
            </p>
          </div>
        )}

        {error && (
          <div className="error-msg mt-12">{error}</div>
        )}
      </div>
    </div>
  );
}
