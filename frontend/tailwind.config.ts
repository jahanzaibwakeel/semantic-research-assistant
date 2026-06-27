import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172026",
        paper: "#f7f5ef",
        panel: "#ffffff",
        teal: "#0f766e",
        coral: "#c2410c"
      },
      boxShadow: {
        soft: "0 16px 45px rgba(23, 32, 38, 0.10)"
      }
    }
  },
  plugins: []
};

export default config;
