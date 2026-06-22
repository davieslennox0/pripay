import { useEffect, useState } from "react";
import { api, type SearchResult, type SendExecuteResponse } from "../lib/api";

const PLATFORMS = ["email", "twitter", "discord", "telegram", "facebook", "twitch"] as const;

export function SendFlow() {
  const [platform, setPlatform] = useState<string>("email");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [handle, setHandle] = useState("");
  const [amount, setAmount] = useState("");
  const [quoteError, setQuoteError] = useState<string | null>(null);
  const [receiverGets, setReceiverGets] = useState<number | null>(null);
  const [pin, setPin] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [result, setResult] = useState<SendExecuteResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Typeahead search against the internal bound-handle index (brief §2) —
  // only finds handles that have actually been bound; the user can still
  // send to an unbound handle by typing it in directly (escrow path).
  useEffect(() => {
    if (query.trim().length === 0) return;
    const id = setTimeout(() => {
      api.searchHandles(platform, query).then(setResults).catch(() => setResults([]));
    }, 300);
    return () => clearTimeout(id);
  }, [platform, query]);

  useEffect(() => {
    if (!handle || !amount) return;
    const parsed = Number(amount);
    if (!Number.isFinite(parsed) || parsed <= 0) return;

    const id = setTimeout(() => {
      api
        .sendQuote(platform, handle, parsed)
        .then((q) => {
          setReceiverGets(q.receiver_gets);
          setQuoteError(null);
        })
        .catch((err) => {
          setReceiverGets(null);
          setQuoteError(err instanceof Error ? err.message : "Failed to get quote");
        });
    }, 300);
    return () => clearTimeout(id);
  }, [platform, handle, amount]);

  async function handleSubmit() {
    setSubmitError(null);
    setSubmitting(true);
    try {
      const res = await api.sendExecute(platform, handle, Number(amount), pin);
      setResult(res);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Send failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (result) {
    const claimLink = result.claim_token
      ? `${window.location.origin}/?claim_token=${result.claim_token}`
      : null;
    return (
      <div>
        <h2>Sent</h2>
        <p>Status: {result.status}</p>
        <p>Recipient gets: {result.receiver_gets} USDC</p>
        {claimLink && (
          <p>
            Recipient hasn't bound this handle yet. Share this claim link:
            <br />
            <code>{claimLink}</code>
          </p>
        )}
        {result.tx_ref && <p>Tx ref: {result.tx_ref}</p>}
        {result.tee_provider && (
          <p>
            Settled in <code>{result.tee_provider}</code> enclave · attestation{" "}
            <code>{result.tee_attestation?.slice(0, 16)}…</code>
          </p>
        )}
        <button type="button" onClick={() => setResult(null)}>
          Send another
        </button>
      </div>
    );
  }

  return (
    <div>
      <h2>Send</h2>
      <div>
        {PLATFORMS.map((p) => (
          <button
            key={p}
            type="button"
            disabled={p === platform}
            onClick={() => {
              setPlatform(p);
              setHandle("");
              setQuery("");
              setResults([]);
            }}
          >
            {p}
          </button>
        ))}
      </div>

      <div>
        <input
          placeholder={`${platform} handle`}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setHandle(e.target.value);
            if (e.target.value.trim().length === 0) setResults([]);
          }}
        />
        {results.length > 0 && (
          <ul>
            {results.map((r) => (
              <li key={r.sui_address}>
                <button
                  type="button"
                  onClick={() => {
                    setHandle(r.handle);
                    setQuery(r.handle);
                    setResults([]);
                  }}
                >
                  {r.handle}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <input
          type="number"
          placeholder="Amount (USDC)"
          value={amount}
          onChange={(e) => {
            setAmount(e.target.value);
            if (!handle || !e.target.value) {
              setQuoteError(null);
              setReceiverGets(null);
            }
          }}
        />
      </div>
      {quoteError && <p style={{ color: "red" }}>{quoteError}</p>}
      {receiverGets !== null && <p>Recipient receives: {receiverGets} USDC (after 0.10 fee)</p>}

      <div>
        <input
          type="password"
          inputMode="numeric"
          placeholder="PIN"
          value={pin}
          onChange={(e) => setPin(e.target.value)}
        />
      </div>

      {submitError && <p style={{ color: "red" }}>{submitError}</p>}
      <button type="button" disabled={!handle || !amount || !pin || submitting} onClick={handleSubmit}>
        {submitting ? "Sending..." : "Send"}
      </button>
    </div>
  );
}
