import { useEffect, useState } from "react";
import { Dashboard } from "./components/Dashboard";
import { PinSetup } from "./components/PinSetup";
import { SendFlow } from "./components/SendFlow";
import { api } from "./lib/api";
import { beginGoogleLogin, completeGoogleLogin } from "./lib/zklogin";
import "./App.css";

function App() {
  const [suiAddress, setSuiAddress] = useState<string | null>(null);
  const [pinIsSet, setPinIsSet] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [claimResult, setClaimResult] = useState<string | null>(null);
  const [bindResult, setBindResult] = useState<string | null>(null);
  const [tab, setTab] = useState<"send" | "dashboard">("send");

  useEffect(() => {
    (async () => {
      try {
        const addressFromCallback = await completeGoogleLogin();
        const me = addressFromCallback
          ? { sui_address: addressFromCallback }
          : await api.me();
        setSuiAddress(me.sui_address);

        const pinStatus = await api.pinStatus();
        setPinIsSet(pinStatus.is_set);

        const claimToken = new URLSearchParams(window.location.search).get("claim_token");
        if (claimToken) {
          window.history.replaceState(null, "", window.location.pathname);
          const claimed = await api.claimSend(claimToken);
          setClaimResult(`Claimed ${claimed.amount} USDC`);
        }

        if (window.location.pathname === "/verify-email") {
          const token = new URLSearchParams(window.location.search).get("token");
          window.history.replaceState(null, "", "/");
          if (token) {
            const bound = await api.confirmEmailBind(token);
            setBindResult(`Bound ${bound.platform}:${bound.handle}`);
          }
        }
      } catch {
        setSuiAddress(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  async function handleLogin() {
    setError(null);
    try {
      await beginGoogleLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start login");
    }
  }

  async function handleLogout() {
    await api.logout();
    setSuiAddress(null);
  }

  if (loading) return null;

  return (
    <section id="center">
      <h1>Umbra</h1>
      {suiAddress ? (
        <>
          <p>Signed in as</p>
          <code>{suiAddress}</code>
          <div>
            <button type="button" onClick={handleLogout}>
              Sign out
            </button>
          </div>
          {claimResult && <p>{claimResult}</p>}
          {bindResult && <p>{bindResult}</p>}
          {pinIsSet ? (
            <>
              <div>
                <button type="button" disabled={tab === "send"} onClick={() => setTab("send")}>
                  Send
                </button>
                <button
                  type="button"
                  disabled={tab === "dashboard"}
                  onClick={() => setTab("dashboard")}
                >
                  Dashboard
                </button>
              </div>
              {tab === "send" ? <SendFlow /> : <Dashboard />}
            </>
          ) : (
            <PinSetup onSet={() => setPinIsSet(true)} />
          )}
        </>
      ) : (
        <div>
          <button type="button" onClick={handleLogin}>
            Sign in with Google
          </button>
        </div>
      )}
      {error && <p style={{ color: "red" }}>{error}</p>}
    </section>
  );
}

export default App;
