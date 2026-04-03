/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        portal: {
          // Primary brand blue — zakupki.mos.ru header/buttons
          blue: "#0050A0",
          "blue-light": "#1A6FC4",
          "blue-hover": "#003E80",
          "blue-pale": "#E8F1FA",
          // Accent — orange call-to-action
          accent: "#F26123",
          "accent-hover": "#D44E0E",
          // Backgrounds
          bg: "#F5F7FA",
          "bg-dark": "#EEF1F6",
          card: "#FFFFFF",
          // Text
          text: "#1D1D1D",
          "text-secondary": "#6C737A",
          "text-muted": "#9BA3AB",
          // Borders
          border: "#D9DDE3",
          "border-light": "#EAECF0",
          // Status colors
          success: "#1E7E34",
          "success-bg": "#EAF5EB",
          warning: "#C66A00",
          "warning-bg": "#FEF6EB",
          error: "#C62828",
          "error-bg": "#FDEAEA",
          info: "#0277BD",
          "info-bg": "#E3F2FD",
        },
      },
      fontFamily: {
        sans: ['"Inter"', '"Segoe UI"', '"PT Sans"', "Roboto", "sans-serif"],
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
      },
      boxShadow: {
        card: "0 1px 4px 0 rgba(0,0,0,0.08)",
        "card-hover": "0 4px 16px 0 rgba(0,0,0,0.12)",
        modal: "0 8px 40px 0 rgba(0,0,0,0.18)",
      },
      borderRadius: {
        portal: "6px",
      },
    },
  },
  plugins: [],
};
