import { useEffect, useState } from "react";
import { api } from "./lib/api";
import { beginGoogleLogin, completeGoogleLogin } from "./lib/zklogin";
import "./App.css";

function App() {
  const [suiAddress, setSuiAddress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const addressFromCallback = await completeGoogleLogin();
        if (addressFromCallback) {
          setSuiAddress(addressFromCallback);
          return;
        }
        const me = await api.me();
        setSuiAddress(me.sui_address);
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
