/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Semantic colors from CSS vars (switch via .light on root)
        background: "var(--color-background)",
        surface: "var(--color-surface)",
        "surface-hover": "var(--color-surface-hover)",
        border: "var(--color-border)",
        "border-focus": "var(--color-border-focus)",
        "text-primary": "var(--color-text-primary)",
        "text-secondary": "var(--color-text-secondary)",
        "text-muted": "var(--color-text-muted)",
        accent: "#FFC53D",
        "accent-hover": "#FFD60A",
        "on-accent": "#111111",
        "on-accent-muted": "#666666",
        recording: "#EF4444",
        success: "#22C55E",
        warning: "#F59E0B",
        error: "#EF4444",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      fontSize: {
        xs: "11px",
        sm: "13px",
        base: "13px",
        lg: "15px",
      },
      letterSpacing: {
        caps: "0.08em",
      },
      borderRadius: {
        panel: "14px",
        input: "8px",
      },
      spacing: {
        panel: "20px",
        section: "16px",
        "gap-sm": "8px",
        "gap-md": "12px",
        "gap-lg": "20px",
        // v2 layout tokens
        "nav-width": "220px",
        "header-height": "52px",
        "content-padding": "32px",
        "section-gap": "32px",
        "nav-item-height": "36px",
      },
      width: {
        panel: "380px",
        "nav": "220px",
        "content-max": "560px",
      },
      height: {
        "header": "52px",
        "nav-item": "36px",
      },
      maxWidth: {
        "content": "560px",
      },
      padding: {
        "content": "32px",
      },
      boxShadow: {
        panel:
          "0 24px 64px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.06)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
