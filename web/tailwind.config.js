/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
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
    },
  },
  plugins: [],
};
