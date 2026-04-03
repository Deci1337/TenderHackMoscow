/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        portal: {
          // --- Primary ---
          blue:        "#264B82",   // Main Blue  — кнопки, активные табы, теги
          "blue-gray": "#D4DBE6",   // Gray Blue  — обводки, линии
          "blue-pale": "#E7EEF7",   // Pale Blue  — фон страницы / карточки
          red:         "#DB2B21",   // Red        — destructive, иллюстрации
          black:       "#1A1A1A",   // Black      — основной текст
          "gray-text": "#8C8C8C",   // Pale Black — вторичный текст

          // --- Additional ---
          green:       "#0D9B68",   // статусы
          "sea-dark":  "#167C85",   // статусы
          "sea-clear": "#48B8C2",   // статусы
          orange:      "#F67319",   // статусы
          gray:        "#7F8792",   // статусы
          "gray-light":"#C9D1DF",   // статусы

          // --- Aliases для удобства (бывшие portal-*) ---
          bg:                "#E7EEF7",
          "bg-card":         "#FFFFFF",
          text:              "#1A1A1A",
          "text-secondary":  "#8C8C8C",
          "text-muted":      "#7F8792",
          border:            "#D4DBE6",
          "border-light":    "#E7EEF7",
          "blue-hover":      "#1C3A6B",
          "blue-light":      "#3A63A8",
          success:           "#0D9B68",
          "success-bg":      "#E6F7F1",
          warning:           "#F67319",
          "warning-bg":      "#FEF3EB",
          error:             "#DB2B21",
          "error-bg":        "#FDECEA",
          info:              "#167C85",
          "info-bg":         "#E5F4F5",
        },
      },
      fontFamily: {
        sans: ['"Inter"', '"Segoe UI"', "Roboto", "sans-serif"],
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
      },
      boxShadow: {
        card:       "0 1px 3px 0 rgba(38,75,130,0.08)",
        "card-hover":"0 4px 16px 0 rgba(38,75,130,0.14)",
        modal:      "0 8px 40px 0 rgba(0,0,0,0.18)",
      },
      borderRadius: {
        portal: "6px",
      },
    },
  },
  plugins: [],
};
