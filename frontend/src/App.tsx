import React, { useCallback, useEffect, useState } from "react";
import { useCurrentAccount, useDisconnectWallet, useSignPersonalMessage } from "@mysten/dapp-kit";
import { Dashboard } from "./components/Dashboard";
import { Landing } from "./components/Landing";
import { PinSetup } from "./components/PinSetup";
import { SendFlow } from "./components/SendFlow";
import { Swap } from "./components/Swap";
import { Receive } from "./components/Receive";
import { Profile } from "./components/Profile";
import { api } from "./lib/api";
import { establishSession } from "./lib/wallet";
import "./App.css";

type Tab = "dashboard" | "send" | "swap" | "receive" | "profile";

// ── Icons ─────────────────────────────────────────────────────────
function IconGrid()    { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>; }
function IconArrowUp() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>; }
function IconSwap()    { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>; }
function IconArrowDown(){ return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>; }
function IconUser()    { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>; }
function IconLogout()  { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>; }
function IconSun()     { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>; }
function IconMoon()    { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>; }
function IconZenPay()  { return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>; }

const NAV_ITEMS: { id: Tab; label: string; icon: () => React.ReactElement }[] = [
  { id: "dashboard", label: "Dashboard", icon: IconGrid },
  { id: "send",      label: "Send",      icon: IconArrowUp },
  { id: "swap",      label: "Swap",      icon: IconSwap },
  { id: "receive",   label: "Receive",   icon: IconArrowDown },
  { id: "profile",   label: "Profile",   icon: IconUser },
];

function useTheme() {
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    return (localStorage.getItem("zenpay-theme") as "dark" | "light") ?? "dark";
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme === "light" ? "light" : "";
    localStorage.setItem("zenpay-theme", theme);
  }, [theme]);

  const toggle = () => setTheme((t) => (t === "dark" ? "light" : "dark"));
  return { theme, toggle };
}

function Sidebar({ tab, onTab, onLogout, address }: {
  tab: Tab;
  onTab: (t: Tab) => void;
  onLogout: () => void;
  address: string;
}) {
  const { theme, toggle } = useTheme();
  const short = `${address.slice(0, 6)}…${address.slice(-4)}`;

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon"><IconZenPay /></div>
        <span className="sidebar-brand-name">ZenPay</span>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={`nav-item${tab === id ? " active" : ""}`}
            onClick={() => onTab(id)}
          >
            <Icon />
            {label}
          </button>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="sidebar-address" title={address}>{short}</div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button type="button" className="theme-toggle" onClick={toggle} title="Toggle theme">
            {theme === "dark" ? <IconSun /> : <IconMoon />}
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            style={{ flex: 1, fontSize: "13px", padding: "7px 12px", gap: "6px" }}
            onClick={onLogout}
          >
            <IconLogout />
            Sign out
          </button>
        </div>
      </div>
    </aside>
  );
}

function MobileNav({ tab, onTab }: { tab: Tab; onTab: (t: Tab) => void }) {
  return (
    <nav className="mobile-nav">
      <div className="mobile-nav-items">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={`mobile-nav-item${tab === id ? " active" : ""}`}
            onClick={() => onTab(id)}
          >
            <Icon />
            {label}
          </button>
        ))}
      </div>
    </nav>
  );
}

function App() {
  const currentAccount = useCurrentAccount();
  const { mutateAsync: signPersonalMessage } = useSignPersonalMessage();
  const { mutate: disconnectWallet } = useDisconnectWallet();

  const [suiAddress, setSuiAddress] = useState<string | null>(null);
  const [pinIsSet, setPinIsSet] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [signingIn, setSigningIn] = useState(false);
  const [tab, setTab] = useState<Tab>("dashboard");
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const me = await api.me();
        setSuiAddress(me.sui_address);
        const pinStatus = await api.pinStatus();
        setPinIsSet(pinStatus.is_set);

        const claimToken = new URLSearchParams(window.location.search).get("claim_token");
        if (claimToken) {
          window.history.replaceState(null, "", window.location.pathname);
          const claimed = await api.claimSend(claimToken);
          setNotice(`Claimed ${claimed.amount} USDC`);
        }

        if (window.location.pathname === "/verify-email") {
          const token = new URLSearchParams(window.location.search).get("token");
          window.history.replaceState(null, "", "/");
          if (token) {
            const bound = await api.confirmEmailBind(token);
            setNotice(`Bound ${bound.platform}:${bound.handle}`);
          }
        }
      } catch {
        setSuiAddress(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const signIn = useCallback(async () => {
    if (!currentAccount) return;
    setError(null);
    setSigningIn(true);
    try {
      const address = await establishSession(currentAccount.address, signPersonalMessage);
      setSuiAddress(address);
      const pinStatus = await api.pinStatus();
      setPinIsSet(pinStatus.is_set);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to sign in");
    } finally {
      setSigningIn(false);
    }
  }, [currentAccount, signPersonalMessage]);

  useEffect(() => {
    if (loading || suiAddress || !currentAccount) return;
    void Promise.resolve().then(() => signIn());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentAccount, loading]);

  async function handleLogout() {
    await api.logout();
    disconnectWallet();
    setSuiAddress(null);
  }

  if (loading) return null;

  if (!suiAddress) {
    return (
      <Landing
        connected={!!currentAccount}
        signingIn={signingIn}
        error={error}
        onRetry={signIn}
      />
    );
  }

  return (
    <div className="app-layout">
      <Sidebar tab={tab} onTab={setTab} onLogout={handleLogout} address={suiAddress} />

      <main className="main-content">
        {notice && (
          <div className="success-msg mb-16">{notice}</div>
        )}
        {error && (
          <div className="error-msg mb-16">{error}</div>
        )}

        {!pinIsSet && (
          <div className="pin-overlay">
            <PinSetup onSet={() => setPinIsSet(true)} />
          </div>
        )}

        {tab === "dashboard" && <Dashboard />}
        {tab === "send"      && <SendFlow />}
        {tab === "swap"      && <Swap />}
        {tab === "receive"   && <Receive address={suiAddress} />}
        {tab === "profile"   && <Profile />}
      </main>

      <MobileNav tab={tab} onTab={setTab} />
    </div>
  );
}

export default App;
