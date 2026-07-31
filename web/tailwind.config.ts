import type { Config } from "tailwindcss";
import generated from "./tokens.json";

// Colours are NOT written by hand here. They are generated from
// dashboard/components/theme.py by scripts/export_web_data.py, and a design gate in the
// Python test suite fails if this file's source drifts from the Streamlit theme.
const t = generated.tokens;

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Surfaces
        page: t.bg_page,
        frame: t.bg_frame,
        card: t.bg_card,
        tile: t.bg_tile,
        // Lines. Named "line" rather than "border" so the utility class stays readable.
        line: t.border,
        "line-dark": t.border_dark,
        "line-soft": t.border_soft,
        grid: t.grid,
        court: t.court_line,
        // Text. Named "ink" so `text-ink` does not collide with the text colour scale.
        ink: t.text,
        "ink-soft": t.text_soft,
        "ink-muted": t.text_muted,
        "ink-faint": t.text_faint,
        // Data semantics: green = good, yellow = mid, red = weak. Fixed everywhere.
        good: t.good,
        mid: t.mid,
        weak: t.weak,
        primary: t.primary,
        "primary-soft": t.primary_soft,
        "weak-soft": t.weak_soft,
        special: t.special,
      },
      fontFamily: {
        body: ["var(--font-inter)", "sans-serif"],
        display: ["var(--font-inter-tight)", "sans-serif"],
        mono: ["ui-monospace", "monospace"],
      },
      borderRadius: {
        card: "14px",
        shell: "18px",
      },
      maxWidth: {
        shell: "1280px",
      },
    },
  },
  plugins: [],
};

export default config;
