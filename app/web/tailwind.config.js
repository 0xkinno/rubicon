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
        // Rubicon accent: deep crimson → warm amber (threshold line)
        rubicon: {
          crimson: '#8B0000',
          red: '#C0392B',
          threshold: '#DC143C',
          amber: '#D97706',
          warmAmber: '#F59E0B',
        },
        // Surface palette
        surface: {
          bg: '#FFFFFF',
          paper: '#F7F8FA',
          card: '#FAFAFA',
          border: '#E5E7EB',
          dark: '#0F0F0F',
          darkCard: '#1A1A1A',
          darkBorder: '#2A2A2A',
        },
        // Text
        ink: {
          DEFAULT: '#1F2328',
          muted: '#57606A',
          subtle: '#9CA3AF',
          inverse: '#F9FAFB',
        },
      },
      fontFamily: {
        display: ['"Helvetica Neue"', 'Helvetica', '-apple-system', 'sans-serif'],
        sans: ['"IBM Plex Sans"', '-apple-system', '"Segoe UI"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', '"Fira Code"', 'monospace'],
      },
      fontSize: {
        'hero': ['clamp(2.5rem, 6vw, 5rem)', { lineHeight: '1.05', letterSpacing: '-0.03em' }],
        'display': ['clamp(1.75rem, 3.5vw, 3rem)', { lineHeight: '1.15', letterSpacing: '-0.02em' }],
      },
      animation: {
        'threshold-pulse': 'thresholdPulse 4s ease-in-out infinite',
        'fade-up': 'fadeUp 0.6s ease-out',
        'count-up': 'countUp 1s ease-out',
      },
      keyframes: {
        thresholdPulse: {
          '0%, 100%': { opacity: '0.7', transform: 'scaleX(1)' },
          '50%': { opacity: '1', transform: 'scaleX(1.002)' },
        },
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        countUp: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
