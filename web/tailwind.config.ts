/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        morva: {
          50: "#f8fafd",
          100: "#f0f6fb",
          200: "#e1ecf5",
          300: "#c8dae9",
          400: "#a8c2d8",
          500: "#7a9ec6",
          600: "#5a7fb0",
          700: "#45618d",
          800: "#384e73",
          900: "#304259",
          950: "#1e3a4f",
        },
      },
      fontFamily: {
        sans: ["Vazirmatn", "system-ui", "sans-serif"],
      },
      fontSize: {
        xs: ["12px", "16px"],
        sm: ["14px", "20px"],
        base: ["16px", "24px"],
        lg: ["18px", "28px"],
        xl: ["20px", "28px"],
        "2xl": ["24px", "32px"],
        "3xl": ["30px", "36px"],
        "4xl": ["36px", "44px"],
      },
      spacing: {
        xs: "4px",
        sm: "8px",
        md: "12px",
        lg: "16px",
        xl: "24px",
        "2xl": "32px",
        "3xl": "48px",
      },
      borderRadius: {
        sm: "8px",
        md: "12px",
        lg: "16px",
        xl: "20px",
        "2xl": "24px",
      },
      boxShadow: {
        sm: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        md: "0 4px 12px 0 rgba(0, 0, 0, 0.08)",
        lg: "0 8px 24px 0 rgba(0, 0, 0, 0.12)",
        xl: "0 12px 32px 0 rgba(0, 0, 0, 0.15)",
      },
    },
  },
  plugins: [require("@tailwindcss/forms"), require("@tailwindcss/typography")],
  important: false,
};
