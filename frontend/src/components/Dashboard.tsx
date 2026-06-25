import { useEffect, useState } from "react";
import {
  api,
  type BalanceOut,
  type BoundHandleOut,
  type HistoryDecrypted,
  type HistoryItem,
  type PersonalVolume,
  type PlatformVolume,
} from "../lib/api";
import { beginPinResetReauth, completePinResetReauth } from "../lib/zklogin";

const PIN_RESET_STORAGE_KEY = "umbra.pendingPinReset";

interface PendingPinReset {
  resetToken: string;
  availableAt: string;
}

export function Dashboard() {
  return (
    <div className="panel dashboard">
      <Balances />
      <Volume />
      <History />
      <Handles />
      <Security />
    </div>
  );
}

function Balances() {
  const [balances, setBalances] = useState<BalanceOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getBalances().then(setBalances).catch((err) => setError(err instanceof Error ? err.message : "Failed to load balances"));
  }, []);

  return (
    <section className="card">
      <h3>Balances</h3>
      {error && <p className="error">{error}</p>}
      {balances === null && !error && <p className="hint">Loading…</p>}
      {balances !== null && (
        <ul className="list">
          {balances
            .filter((b) => b.symbol !== null)
            .map((b) => (
              <li className="list-row" key={b.coin_type}>
                <span>
                  {b.amount} {b.symbol}
                </span>
                {b.value_usd !== null && <span>~${b.value_usd.toFixed(2)}</span>}
              </li>
            ))}
          {balances.filter((b) => b.symbol === null).length > 0 && (
            <li className="list-row">
              +{balances.filter((b) => b.symbol === null).length} other token(s)
            </li>
          )}
        </ul>
      )}
    </section>
  );
}

function Volume() {
  const [personal, setPersonal] = useState<PersonalVolume | null>(null);
  const [platform, setPlatform] = useState<PlatformVolume | null>(null);

  useEffect(() => {
    api.getVolume().then(setPersonal).catch(() => setPersonal(null));
    api.getPlatformVolume().then(setPlatform).catch(() => setPlatform(null));
  }, []);

  return (
    <section className="card">
      <h3>Volume</h3>
      {personal && (
        <p className="hint">
          You've sent {personal.total_sent} USDC, received {personal.total_received} USDC, and
          made {personal.swap_count} swap(s).
        </p>
      )}
      {platform && (
        <p className="hint">
          Umbra-wide: {platform.total_volume} USDC moved across {platform.send_count} send(s).
        </p>
      )}
    </section>
  );
}

function History() {
  const [items, setItems] = useState<HistoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [decrypted, setDecrypted] = useState<Record<number, HistoryDecrypted>>({});

  useEffect(() => {
    api.getHistory().then(setItems).catch((err) => setError(err instanceof Error ? err.message : "Failed to load history"));
  }, []);

  async function reveal(recordId: number) {
    try {
      const payload = await api.decryptHistoryItem(recordId);
      setDecrypted((prev) => ({ ...prev, [recordId]: payload }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to decrypt record");
    }
  }

  return (
    <section className="card">
      <h3>Transaction history</h3>
      {error && <p className="error">{error}</p>}
      {items === null && !error && <p className="hint">Loading…</p>}
      {items !== null && items.length === 0 && <p className="hint">No activity yet.</p>}
      {items !== null && items.length > 0 && (
        <ul className="list">
          {items.map((item) => {
            const reveal_ = decrypted[item.record_id];
            return (
              <li className="list-row" key={`${item.kind}-${item.record_id}`}>
                <span>
                  [{item.kind}
                  {item.direction ? `:${item.direction}` : ""}] {item.counterparty ?? "—"} —{" "}
                  {item.status} — {new Date(item.created_at).toLocaleString()}
                  {reveal_ && (
                    <>
                      {" "}
                      → {reveal_.amount} {reveal_.token}
                      {reveal_.memo ? ` ("${reveal_.memo}")` : ""}
                    </>
                  )}
                </span>
                {item.can_decrypt && !reveal_ && (
                  <button type="button" className="btn" onClick={() => reveal(item.record_id)}>
                    Decrypt
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function Handles() {
  const [handles, setHandles] = useState<BoundHandleOut[] | null>(null);
  const [email, setEmail] = useState("");
  const [bindStarted, setBindStarted] = useState(false);
  const [unbindPin, setUnbindPin] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    api.listHandles().then(setHandles).catch(() => setHandles([]));
  }

  useEffect(refresh, []);

  async function handleStartBind() {
    setError(null);
    try {
      await api.startEmailBind(email);
      setBindStarted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start binding");
    }
  }

  async function handleUnbind(platform: string, handle: string) {
    setError(null);
    try {
      await api.unbindHandle(platform, handle, unbindPin[`${platform}:${handle}`] ?? "");
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to unbind");
    }
  }

  return (
    <section className="card">
      <h3>Bound handles</h3>
      {error && <p className="error">{error}</p>}
      {handles !== null && handles.length === 0 && <p className="hint">No handles bound yet.</p>}
      {handles !== null && handles.length > 0 && (
        <ul className="list">
          {handles.map((h) => (
            <li className="list-row" key={`${h.platform}:${h.handle}`}>
              <span>
                {h.platform}:{h.handle}
              </span>
              <div className="field">
                <input
                  type="password"
                  inputMode="numeric"
                  placeholder="PIN"
                  value={unbindPin[`${h.platform}:${h.handle}`] ?? ""}
                  onChange={(e) =>
                    setUnbindPin((prev) => ({
                      ...prev,
                      [`${h.platform}:${h.handle}`]: e.target.value,
                    }))
                  }
                />
              </div>
              <button type="button" className="btn" onClick={() => handleUnbind(h.platform, h.handle)}>
                Unbind
              </button>
            </li>
          ))}
        </ul>
      )}

      {bindStarted ? (
        <p className="hint">Check your email for a verification link to finish binding.</p>
      ) : (
        <div className="inline-form">
          <input
            type="email"
            placeholder="Bind an email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button type="button" className="btn" disabled={!email} onClick={handleStartBind}>
            Bind
          </button>
        </div>
      )}
    </section>
  );
}

function Security() {
  const [pending, setPending] = useState<PendingPinReset | null>(() => {
    const raw = localStorage.getItem(PIN_RESET_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as PendingPinReset) : null;
  });
  const [newPin, setNewPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  function setPendingAndPersist(value: PendingPinReset | null) {
    setPending(value);
    if (value) localStorage.setItem(PIN_RESET_STORAGE_KEY, JSON.stringify(value));
    else localStorage.removeItem(PIN_RESET_STORAGE_KEY);
  }

  // Resumes here on redirect back from the re-auth Google sign-in this
  // section itself triggered — a no-op (returns null) on any other load.
  useEffect(() => {
    completePinResetReauth()
      .then((result) => {
        if (result) setPendingAndPersist({ resetToken: result.resetToken, availableAt: result.availableAt });
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to request PIN reset"));
  }, []);

  useEffect(() => {
    if (!pending) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [pending]);

  function startReset() {
    beginPinResetReauth(); // redirects to Google; resumes above on return
  }

  async function confirmReset() {
    if (!pending) return;
    setError(null);
    try {
      await api.confirmPinReset(pending.resetToken, newPin);
      setDone(true);
      setPendingAndPersist(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset PIN");
    }
  }

  const availableAt = pending ? new Date(pending.availableAt).getTime() : null;
  const cooldownRemainingMs = availableAt !== null ? availableAt - now : 0;

  return (
    <section className="card">
      <h3>Security</h3>
      {done && <p className="hint">PIN reset.</p>}
      {!pending && !done && (
        <div>
          <p className="hint">
            Forgot your PIN, or think someone else might know it? Reset it via a fresh Google
            sign-in.
          </p>
          <button type="button" className="btn" onClick={startReset}>
            Reset PIN
          </button>
        </div>
      )}
      {pending && cooldownRemainingMs > 0 && (
        <p className="hint">
          Reset requested — available in {Math.ceil(cooldownRemainingMs / 1000)}s (brief §6
          cooldown, in case this wasn't you).
        </p>
      )}
      {pending && cooldownRemainingMs <= 0 && (
        <div className="inline-form">
          <input
            type="password"
            inputMode="numeric"
            placeholder="New 4-6 digit PIN"
            value={newPin}
            onChange={(e) => setNewPin(e.target.value)}
          />
          <button type="button" className="btn" disabled={newPin.length < 4} onClick={confirmReset}>
            Confirm new PIN
          </button>
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </section>
  );
}
