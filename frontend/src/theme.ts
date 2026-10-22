import { createTheme, type PaletteOptions } from "@mui/material/styles";

/*
 * The one theme for the portal (ruleset 9.2). Every colour in the UI comes from here;
 * components use theme keys and `sx`, never hex. Values are carried over from the
 * retired app.css tokens so the look stays the same (WL-047).
 */

// Neutral ramp (--n0 .. --n900), one cool grey. The same in light and dark.
const n = {
  0: "#ffffff",
  50: "#f4f7f9",
  100: "#e9edf1",
  200: "#d8e0e5",
  300: "#c0cad1",
  400: "#919ba3",
  500: "#6d787f",
  600: "#5e686f",
  700: "#3e474d",
  800: "#262d32",
  900: "#14191d",
} as const;

const FONT = '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
const MONO = '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';

// Phones (<600px) get 16px body text and 48px touch targets (ruleset 9.3).
const PHONE = "@media (max-width:599.95px)";

declare module "@mui/material/styles" {
  // CSS variables are on, so theme.vars and theme.colorSchemes are typed.
  interface CssThemeVariables {
    enabled: true;
  }
  interface Palette {
    brand: string;
    surface: { ok: string; warn: string; crit: string; action: string; paper2: string };
    levels: { res: string; target: string; entry: string; ema20: string; ema50: string; support: string; stop: string };
  }
  interface PaletteOptions {
    brand?: string;
    surface?: Palette["surface"];
    levels?: Palette["levels"];
  }
  interface TypographyVariants {
    fontFamilyMono: string;
  }
  interface TypographyVariantsOptions {
    fontFamilyMono?: string;
  }
  interface Shape {
    radiusMd: number;
    radiusLg: number;
  }
  interface ShapeOptions {
    radiusMd?: number;
    radiusLg?: number;
  }
}

const light: PaletteOptions = {
  mode: "light",
  // --action, with --action-hover as dark and --action-pressed as the active shade.
  primary: { main: "#0b749e", dark: "#0a5d7e", light: "#e7f4fb", contrastText: "#ffffff" },
  secondary: { main: n[700], contrastText: n[0] },
  success: { main: "#2e7d32", contrastText: "#ffffff" },
  error: { main: "#ba1a1a", contrastText: "#ffffff" },
  warning: { main: "#a85300", contrastText: "#ffffff" },
  info: { main: "#0b749e", contrastText: "#ffffff" },
  grey: { 50: n[50], 100: n[100], 200: n[200], 300: n[300], 400: n[400], 500: n[500], 600: n[600], 700: n[700], 800: n[800], 900: n[900] },
  background: { default: n[50], paper: n[0] },
  text: { primary: n[900], secondary: n[500], disabled: n[400] },
  divider: n[200],
  action: { hover: "rgba(11, 116, 158, 0.06)", selected: "#e7f4fb", active: n[700], focus: "rgba(11, 116, 158, 0.24)" },
  brand: "#12b6f8",
  surface: { ok: "#e6f7ec", warn: "#fff4e5", crit: "#fdecec", action: "#e7f4fb", paper2: n[50] },
  levels: {
    res: "#c2410c",
    target: "#2e7d32",
    entry: "#0b749e",
    ema20: "#7a5af8",
    ema50: "#a63d7e",
    support: "#0f9d8f",
    stop: "#ba1a1a",
  },
};

const dark: PaletteOptions = {
  mode: "dark",
  primary: { main: "#3ba7d4", dark: "#5bb8de", light: "#0f2a36", contrastText: "#0b0e10" },
  secondary: { main: n[200], contrastText: n[900] },
  success: { main: "#5ccf7f", contrastText: "#0b0e10" },
  error: { main: "#ff8a80", contrastText: "#0b0e10" },
  warning: { main: "#f0a04b", contrastText: "#0b0e10" },
  info: { main: "#3ba7d4", contrastText: "#0b0e10" },
  grey: { 50: n[50], 100: n[100], 200: n[200], 300: n[300], 400: n[400], 500: n[500], 600: n[600], 700: n[700], 800: n[800], 900: n[900] },
  background: { default: "#0b0e10", paper: n[900] },
  text: { primary: "#eef2f5", secondary: n[400], disabled: n[500] },
  divider: n[800],
  action: { hover: "rgba(59, 167, 212, 0.08)", selected: "#0f2a36", active: n[200], focus: "rgba(59, 167, 212, 0.24)" },
  brand: "#12b6f8",
  surface: { ok: "#12291a", warn: "#2e1f0c", crit: "#33171a", action: "#0f2a36", paper2: "#1a2025" },
  levels: {
    res: "#fb923c",
    target: "#5ccf7f",
    entry: "#3ba7d4",
    ema20: "#a48bff",
    ema50: "#e07ab8",
    support: "#3fd1c0",
    stop: "#ff8a80",
  },
};

export const RAIL_WIDTH = 224;
export const RAIL_FOLDED = 64;
export const TOPBAR_HEIGHT = 52;

const theme = createTheme({
  cssVariables: { colorSchemeSelector: "data" },
  colorSchemes: { light: { palette: light }, dark: { palette: dark } },
  shape: { borderRadius: 6, radiusMd: 10, radiusLg: 16 },
  typography: {
    fontFamily: FONT,
    fontFamilyMono: MONO,
    fontSize: 14,
    h1: { fontSize: "1rem", fontWeight: 600 },
    h2: { fontSize: "1.375rem", fontWeight: 700, letterSpacing: "-0.01em" },
    h3: { fontSize: "0.9375rem", fontWeight: 600 },
    body1: { fontSize: "0.875rem", [PHONE]: { fontSize: "1rem" } },
    body2: { fontSize: "0.8125rem", [PHONE]: { fontSize: "1rem" } },
    caption: { fontSize: "0.75rem" },
    overline: { fontSize: "0.6875rem", fontWeight: 600, letterSpacing: "0.06em", lineHeight: 1.6 },
    button: { textTransform: "none", fontWeight: 600 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { [PHONE]: { fontSize: "1rem" } },
        // Numbers line up in tables and KPI tiles.
        "code, kbd": { fontFamily: MONO },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { minHeight: 36, whiteSpace: "nowrap", [PHONE]: { minHeight: 48 } } },
    },
    MuiIconButton: {
      styleOverrides: { root: { [PHONE]: { minWidth: 48, minHeight: 48 } } },
    },
    MuiToggleButton: {
      styleOverrides: { root: { textTransform: "none", fontWeight: 600, paddingTop: 4, paddingBottom: 4, [PHONE]: { minHeight: 48, minWidth: 44 } } },
    },
    MuiChip: {
      styleOverrides: { root: { fontWeight: 600 }, label: { paddingLeft: 8, paddingRight: 8 } },
    },
    MuiPaper: {
      styleOverrides: { rounded: { borderRadius: 10 } },
    },
    MuiCard: {
      defaultProps: { variant: "outlined" },
    },
    MuiDialog: {
      styleOverrides: { paper: { borderRadius: 16 } },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { paddingTop: 8, paddingBottom: 8, whiteSpace: "nowrap" },
        head: { fontSize: "0.6875rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" },
      },
    },
    MuiTooltip: {
      defaultProps: { arrow: true },
    },
    MuiListItemButton: {
      styleOverrides: { root: { [PHONE]: { minHeight: 48 } } },
    },
  },
});

export default theme;
