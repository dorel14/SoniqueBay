module.exports = {
  content: ['./**/*.py'], // NiceGUI génère les classes depuis ton code Python
  theme: {
    extend: {},
  },
  plugins: [
    require('@tailwindcss/line-clamp'),
    require('@tailwindcss/aspect-ratio'),
  ],
}