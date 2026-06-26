import type { ThemeVars } from "@mysten/dapp-kit";

const shared = {
  blurs: { modalOverlay: "blur(0)" },
  radii: { small: "3px", medium: "3px", large: "4px", xlarge: "4px" },
  fontWeights: { normal: "400", medium: "500", bold: "600" },
  fontSizes: { small: "13px", medium: "15px", large: "17px", xlarge: "20px" },
  typography: {
    fontFamily: "system-ui, 'Segoe UI', Roboto, sans-serif",
    fontStyle: "normal",
    lineHeight: "1.45",
    letterSpacing: "0.1px",
  },
};

/** Mirrors the CSS variables in index.css (--accent/--bg/--code-bg/--border/
 * --text/--text-h) so the wallet connect modal matches the rest of the app
 * instead of dapp-kit's own default look. */
function buildTheme(opts: {
  accent: string;
  accentHover: string;
  bg: string;
  codeBg: string;
  border: string;
  text: string;
  textHeading: string;
}): ThemeVars {
  return {
    ...shared,
    backgroundColors: {
      primaryButton: opts.accent,
      primaryButtonHover: opts.accentHover,
      outlineButtonHover: opts.codeBg,
      walletItemHover: opts.codeBg,
      walletItemSelected: opts.codeBg,
      modalOverlay: "rgba(24, 24, 27, 0.5)",
      modalPrimary: opts.bg,
      modalSecondary: opts.codeBg,
      iconButton: "transparent",
      iconButtonHover: opts.codeBg,
      dropdownMenu: opts.bg,
      dropdownMenuSeparator: opts.border,
    },
    borderColors: { outlineButton: opts.border },
    colors: {
      primaryButton: "#fff",
      outlineButton: opts.textHeading,
      body: opts.textHeading,
      bodyMuted: opts.text,
      bodyDanger: "#9f3a38",
      iconButton: opts.textHeading,
    },
    shadows: {
      primaryButton: "none",
      walletItemSelected: "none",
    },
  };
}

export const umbraWalletTheme = [
  {
    variables: buildTheme({
      accent: "#52525b",
      accentHover: "#3f3f46",
      bg: "#fff",
      codeBg: "#eef0f2",
      border: "#d4d4d8",
      text: "#71717a",
      textHeading: "#18181b",
    }),
  },
  {
    mediaQuery: "(prefers-color-scheme: dark)",
    variables: buildTheme({
      accent: "#a1a1aa",
      accentHover: "#71717a",
      bg: "#18181b",
      codeBg: "#27272a",
      border: "#3f3f46",
      text: "#9ca3af",
      textHeading: "#f3f4f6",
    }),
  },
];
