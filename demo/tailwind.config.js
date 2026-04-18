/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#0a0e1a',
          secondary: '#111827',
          card: '#1a2235',
        },
        accent: {
          green: '#00e676',
          amber: '#ffb300',
          cyan: '#00bcd4',
          red: '#ff5252',
          orange: '#ff9800',
          blue: '#40c4ff',
          purple: '#bb86fc',
        },
        border: '#1e293b',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
};
