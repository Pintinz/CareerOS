import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#081B3A",
        brand: {
          DEFAULT: "#1677FF",
          light: "#12A8FF",
        },
        background: "#F6F8FC",
        card: "#FFFFFF",
        ink: "#10213D",
        muted: "#718096",
        success: "#19B36B",
        warning: "#F5A623",
        danger: "#E84D5B",
        violet: "#7557FF",
      },
      borderRadius: {
        xl: "16px",
        "2xl": "24px",
      },
    },
  },
  plugins: [],
};

export default config;
