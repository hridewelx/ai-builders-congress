/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: "#0B1F5C",
        "brand-blue": "#1F4FD8",
        tint: "#EAF0FF",
        ink: "#0F172A",
        muted: "#64748B",
        line: "#E2E8F0",
        accept: "#15803D",
        "accept-bg": "#DCFCE7",
        reject: "#B91C1C",
        "reject-bg": "#FEE2E2",
        hold: "#B45309",
        "hold-bg": "#FEF3C7",
        escalate: "#6D28D9",
        "escalate-bg": "#EDE9FE",
        info: "#0369A1",
        "info-bg": "#E0F2FE",
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
