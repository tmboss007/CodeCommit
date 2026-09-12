/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: '#F4F5F7',
        surface: '#FFFFFF',
        surface2: '#F8F9FB',
        line: '#D9DDE3',
        ink: '#171A1F',
        muted: '#626A75',
        brand: '#243B53',
        accent: '#7A2634',
        critical: '#B42318',
        high: '#C75B12',
        warning: '#A15C00',
        success: '#176B47',
        neutral: '#59636E',
      },
      fontSize: {
        page: ['2rem', { lineHeight: '1.2', fontWeight: '700' }],
        metric: ['1.875rem', { lineHeight: '1.2', fontWeight: '600' }],
      },
      borderRadius: {
        eoc: '8px',
      },
    },
  },
  plugins: [],
};
