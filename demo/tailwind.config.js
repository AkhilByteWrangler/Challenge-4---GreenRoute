/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: {
          primary: { dark: '#0a0e1a', light: '#ffffff' },
          secondary: { dark: '#111827', light: '#f8fafc' },
          card: { dark: '#1a2235', light: '#f1f5f9' },
        },
        accent: {
          green: '#10b981',
          amber: '#f59e0b',
          cyan: '#06b6d4',
          red: '#ef4444',
          orange: '#f97316',
          blue: '#3b82f6',
          purple: '#a855f7',
        },
        border: { dark: '#1e293b', light: '#e2e8f0' },
      },
      fontFamily: {
        sans: ['IBM Plex Sans', 'system-ui', 'sans-serif'],
        mono: ['Space Mono', 'monospace'],
        display: ['IBM Plex Sans', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
