import type { Config } from "tailwindcss";

// CareerOS design tokens — mirrors mobile/lib/core/design (see
// .claude/skills/careeros-ui-system/references/design-tokens.md and admin-design.md).
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#071A38",
        brand: {
          DEFAULT: "#1677FF",
          light: "#249BFF",
        },
        cyan: "#13BDEB",
        background: "#F6F8FC",
        card: "#FFFFFF",
        ink: "#10213D",
        muted: "#66758C",
        line: "#E6EBF2",
        success: "#18B76A",
        warning: "#F5A623",
        danger: "#E84D5B",
        violet: "#7557FF",
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', "Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
      borderRadius: {
        lg: "8px",
        xl: "12px",
        "2xl": "16px",
      },
      boxShadow: {
        // Hairline border + soft shadow in one token, so every existing `shadow-sm` surface gets the
        // refined CareerOS card treatment.
        sm: "0 0 0 1px #E6EBF2, 0 4px 16px rgba(7, 26, 56, 0.04)",
        md: "0 0 0 1px #E6EBF2, 0 10px 24px rgba(7, 26, 56, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
