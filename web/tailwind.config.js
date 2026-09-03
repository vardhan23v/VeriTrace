/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0a0a0f",
        panel: "#14141c",
        accent: "#6ee7b7",
        accent2: "#38bdf8",
        muted: "#9ca3af"
      }
    }
  },
  plugins: []
}
