/**
 * Arjuna AI design system.
 *
 * Palette discipline: deep forest for navigation and anchors, medium green for
 * interactive elements, soft sage for section backgrounds, white / off-white for
 * content surfaces, neutral grey for secondary text and borders. Nothing in the
 * UI is near-black or neon.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        forest: {
          50: "#EEF5F1",
          100: "#D6E7DD",
          200: "#AECFBC",
          300: "#7FB096",
          400: "#4E8A6D",
          500: "#2B6B4E",
          600: "#1B5740",
          700: "#124433",
          800: "#0C3326",
          900: "#07251B",
        },
        brand: {
          50: "#EDF9F1",
          100: "#D3F0DE",
          200: "#A8E1C0",
          300: "#73CC9D",
          400: "#44B47C",
          500: "#229A63",
          600: "#187C4F",
          700: "#156240",
          800: "#124E34",
          900: "#0E3F2B",
        },
        sage: {
          50: "#F5FAF6",
          100: "#EAF4EC",
          200: "#DCEBE0",
          300: "#C7DCCD",
          400: "#AAC7B3",
        },
        ink: {
          900: "#13241C",
          800: "#1D3328",
          700: "#2C463A",
          600: "#43594F",
          500: "#5F736A",
          400: "#7D8F86",
          300: "#A3B1AA",
        },
        line: {
          DEFAULT: "#E1EAE4",
          strong: "#CBDAD1",
        },
        surface: {
          DEFAULT: "#FFFFFF",
          muted: "#FBFDFC",
          sunken: "#F5FAF6",
        },
        warn: { 50: "#FFF8EB", 500: "#C9872B", 700: "#8A5B13" },
        danger: { 50: "#FDF1F0", 500: "#C0493D", 700: "#8F3129" },
        info: { 50: "#EEF4FB", 500: "#3B6DA8", 700: "#2A4F7C" },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        suits: ["Playfair Display", "Georgia", "serif"],
        display: ["Plus Jakarta Sans", "Inter", "system-ui", "sans-serif"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1.125rem",
        "3xl": "1.5rem",
      },
      boxShadow: {
        card: "0 1px 2px rgba(19, 36, 28, 0.04), 0 8px 24px -12px rgba(19, 36, 28, 0.12)",
        "card-hover":
          "0 2px 4px rgba(19, 36, 28, 0.05), 0 16px 40px -16px rgba(19, 36, 28, 0.20)",
        float: "0 20px 60px -24px rgba(7, 37, 27, 0.35)",
        inset: "inset 0 1px 0 rgba(255,255,255,0.6)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "slide-in-right": {
          "0%": { opacity: "0", transform: "translateX(16px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.97)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "pulse-ring": {
          "0%": { transform: "scale(0.9)", opacity: "0.6" },
          "70%": { transform: "scale(1.25)", opacity: "0" },
          "100%": { opacity: "0" },
        },
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.45s cubic-bezier(0.22, 1, 0.36, 1) both",
        "fade-in": "fade-in 0.3s ease-out both",
        "slide-in-right": "slide-in-right 0.35s cubic-bezier(0.22, 1, 0.36, 1) both",
        "scale-in": "scale-in 0.25s cubic-bezier(0.22, 1, 0.36, 1) both",
        shimmer: "shimmer 1.6s infinite",
        "pulse-ring": "pulse-ring 2.4s cubic-bezier(0.24, 0, 0.38, 1) infinite",
        float: "float 5s ease-in-out infinite",
      },
      transitionTimingFunction: {
        smooth: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },
  plugins: [],
};
