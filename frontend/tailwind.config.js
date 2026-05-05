/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#15201b",
        moss: "#426854",
        mint: "#d7efe3",
        coral: "#ee765f",
        paper: "#fbfaf5"
      }
    }
  },
  plugins: []
};
