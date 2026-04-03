/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        portal: {
          blue: "#0D47A1",
          "blue-light": "#1565C0",
          "blue-hover": "#0B3D91",
          accent: "#FF6F00",
          bg: "#F5F7FA",
          card: "#FFFFFF",
          text: "#1A1A1A",
          "text-secondary": "#6B7280",
          border: "#E5E7EB",
          success: "#2E7D32",
          warning: "#F57F17",
        },
      },
      fontFamily: {
        sans: ['"Inter"', '"Segoe UI"', "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};
