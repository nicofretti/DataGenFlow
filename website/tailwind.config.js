/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#10b981',
          dark: '#059669',
          light: '#34d399',
        },
        background: {
          DEFAULT: '#000000',
          dark: '#0a0a0a',
          card: '#1a1a1a',
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
