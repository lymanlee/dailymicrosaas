import typography from '@tailwindcss/typography';

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        primary: '#2563EB',
        secondary: '#10B981',
        accent: '#F59E0B',
        ink: '#0F172A',
      },
      boxShadow: {
        soft: '0 24px 80px -32px rgba(15, 23, 42, 0.35)',
      },
      backgroundImage: {
        'hero-glow': 'radial-gradient(circle at top, rgba(37, 99, 235, 0.18), transparent 55%)',
      },
    },
  },
  plugins: [typography],
}
