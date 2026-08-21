import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        md: "calc(var(--radius) - 2px)",
        lg: "var(--radius)",
      },
      keyframes: {
        "slide-in-right": {
          "0%": { transform: "translateX(100%)", opacity: "0" },
          "100%": { transform: "translateX(0)", opacity: "1" },
        },
      },
      animation: {
        "slide-in-right": "slide-in-right 0.3s ease-out forwards",
      },
      typography: () => ({
        DEFAULT: {
          css: {
            "--tw-prose-body": "inherit",
            "--tw-prose-headings": "inherit",
            "--tw-prose-lead": "inherit",
            "--tw-prose-bold": "inherit",
            "--tw-prose-counters": "inherit",
            "--tw-prose-bullets": "inherit",
            "--tw-prose-hr": "hsl(var(--border))",
            "--tw-prose-quotes": "inherit",
            "--tw-prose-quote-borders": "hsl(var(--border))",
            "--tw-prose-captions": "inherit",
            "--tw-prose-code": "inherit",
            "--tw-prose-th-borders": "hsl(var(--border))",
            "--tw-prose-td-borders": "hsl(var(--border))",
            maxWidth: "none",
            color: "inherit",
            code: {
              backgroundColor: "hsl(var(--muted))",
              borderRadius: "0.25rem",
              padding: "0.15rem 0.4rem",
              fontWeight: "500",
            },
            "code::before": { content: "none" },
            "code::after": { content: "none" },
            pre: {
              backgroundColor: "hsl(var(--muted))",
              color: "inherit",
            },
          },
        },
      }),
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
