import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        shell: {
          950: "#07111f",
          900: "#0b1728",
          800: "#11233a"
        },
        ember: "#ff7a59",
        teal: "#4fd1c5",
        sand: "#f0d7b8"
      },
      boxShadow: {
        glow: "0 20px 80px rgba(79, 209, 197, 0.18)"
      },
      fontFamily: {
        sans: ["var(--font-sans)"]
      }
    }
  },
  plugins: []
};

export default config;
