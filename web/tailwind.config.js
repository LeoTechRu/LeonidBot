module.exports = {
  content: [
    "./templates/**/*.{html,htm}",
    "./src/**/*.{ts,js}"
  ],
  theme: {
    extend: {
      colors: {
        accent1: "var(--color-accent-1)",
        accent2: "var(--color-accent-2)"
      },
      borderRadius: {
        base: "var(--radius)"
      }
    }
  },
  plugins: []
};
