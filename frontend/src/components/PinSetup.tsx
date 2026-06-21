import { useState } from "react";
import { api } from "../lib/api";

export function PinSetup({ onSet }: { onSet: () => void }) {
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
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

  return (
    <div>
      <h2>Set a transaction PIN</h2>
      <p>Required before you can send, claim, or bind handles (brief §6).</p>
      <input
        type="password"
        inputMode="numeric"
        placeholder="4-6 digit PIN"
        value={pin}
        onChange={(e) => setPin(e.target.value)}
      />
      {error && <p style={{ color: "red" }}>{error}</p>}
      <button type="button" disabled={submitting || pin.length < 4} onClick={handleSubmit}>
        Set PIN
      </button>
    </div>
  );
}
