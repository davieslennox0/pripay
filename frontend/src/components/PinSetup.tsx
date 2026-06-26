import { useState } from "react";
import { api } from "../lib/api";

export function PinSetup({ onSet }: { onSet: () => void }) {
  const [pin,        setPin]        = useState("");
  const [error,      setError]      = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    setError(null);
    setSubmitting(true);
    try {
      await api.setPin(pin);
      onSet();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to set PIN");
    } finally {
      setSubmitting(false);
    }
  }

  const dots = Array.from({ length: 6 });

  return (
    <div className="pin-card">
      <div style={{ marginBottom: "8px" }}>
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ margin: "0 auto 16px", display: "block" }}>
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        </svg>
        <h2 style={{ fontSize: "20px", fontWeight: 700, color: "var(--text)", marginBottom: "8px" }}>
          Set Transaction PIN
        </h2>
        <p className="text-sm" style={{ color: "var(--text-2)" }}>
          Choose a 4–6 digit PIN. Required to confirm payments.
        </p>
      </div>

      {/* Dot indicator */}
      <div className="pin-dots">
        {dots.map((_, i) => (
          <div key={i} className={`pin-dot${i < pin.length ? " filled" : ""}`} />
        ))}
      </div>

      <div className="field">
        <input
          type="password"
          inputMode="numeric"
          placeholder="4–6 digit PIN"
          value={pin}
          maxLength={6}
          onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
          autoComplete="new-password"
          style={{ textAlign: "center", fontSize: "20px", letterSpacing: "0.3em" }}
        />
      </div>

      {error && <div className="error-msg">{error}</div>}

      <button
        type="button"
        className="btn btn-primary btn-block"
        disabled={submitting || pin.length < 4}
        onClick={handleSubmit}
      >
        {submitting ? <span className="spinner" /> : "Set PIN"}
      </button>
    </div>
  );
}
