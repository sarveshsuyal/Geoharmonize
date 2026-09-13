/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Restrained, professional government-GIS palette - deliberately not a
        // "startup" gradient/neon palette per the design language requirements.
        ink: {
          900: "#0f172a",
          800: "#1e293b",
          700: "#334155",
          600: "#475569",
          500: "#64748b",
          200: "#e2e8f0",
          100: "#f1f5f9",
          50: "#f8fafc",
        },
        brand: {
          700: "#0b4f6c",
          600: "#0e6690",
          500: "#1583b3",
          100: "#e3f1f6",
        },
        status: {
          high: "#15803d",
          medium: "#b45309",
          low: "#b91c1c",
          info: "#1d4ed8",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
