export function Profile() {
  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Profile</div>
          <div className="page-subtitle">Account settings and handles</div>
        </div>
      </div>

      <div className="card">
        <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-3)" }}>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ margin: "0 auto 12px", display: "block" }}>
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
          <div style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-2)", marginBottom: "6px" }}>
            Profile coming soon
          </div>
          <div className="text-sm">
            Handle management and account settings are available on the Dashboard tab.
          </div>
        </div>
      </div>
    </div>
  );
}
