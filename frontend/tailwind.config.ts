import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        app: {
          main: 'var(--bg-main)',
          panel: 'var(--bg-panel)',
          accent: 'var(--accent)',
          strong: 'var(--accent-strong)',
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
