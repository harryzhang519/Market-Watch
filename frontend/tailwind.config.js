/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        obsidian: '#0B0B0F',
        bone: '#F4F1EB',
        ember: '#E94E1B',
        smoke: '#6E6A61',
        limestone: '#D8D3C6',
        graphite: '#2B2A27',
        mist: '#E7E4DD',
        paper: '#FAFAF7',
        fog: '#C9C4BA',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
