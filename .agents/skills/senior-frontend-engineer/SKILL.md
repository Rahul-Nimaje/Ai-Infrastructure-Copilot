---
name: senior-frontend-engineer
description: >-
  Use this skill when building, styling, refactoring, or optimizing user interfaces in Next.js, React, TypeScript, state management, design systems (Vanilla CSS/Tailwind), web accessibility (WCAG), real-time updates, and web performance.
---

# Senior Frontend Engineer Skill

This skill outlines design system implementations, modern UI architecture, performance optimization, and component state patterns for the AI Infrastructure Copilot Web application.

## 1. UI Design & Styling Philosophy

- **Modern & Premium Aesthetics**:
  - Implement vibrant, cohesive color palettes with subtle dark mode gradients, glassmorphism, clean typography (e.g., Inter, Roboto), and responsive layouts.
  - Avoid basic browser defaults or unstyled generic tables/forms.
  - Utilize dynamic micro-animations and smooth transitions (`transition-all`, `ease-in-out`) to enhance visual hierarchy and interactive responsiveness.
- **Component Architecture**:
  - Build reusable, single-responsibility components with strict TypeScript prop interfaces.
  - Maintain a clear separation of concerns: UI Presentation vs Custom Hooks / Data Fetching.

## 2. Next.js & React Performance Optimization

- **State Management & Data Fetching**:
  - Leverage Server Components for data fetching where appropriate to minimize client-side JavaScript bundle sizes.
  - Use React Query / TanStack Query or SWR for client-side caching, background revalidation, optimistic UI updates, and error state handling.
- **Core Web Vitals**:
  - Optimize Largest Contentful Paint (LCP) and Cumulative Layout Shift (CLS) through fixed layout dimensions, dynamic image optimization, and font preloading.
  - Code-split heavy dependencies using `React.lazy` or Next.js `dynamic()` imports.

## 3. Real-Time Interactions & Accessibility (a11y)

- **Streaming & Real-Time UX**:
  - Integrate SSE (Server-Sent Events) or WebSockets for real-time AI response rendering, auto-scrolling chat interfaces, and live status progress indicators.
  - Provide immediate feedback during long-running background operations with skeleton loaders, spinners, and disable state management.
- **Accessibility & SEO**:
  - Ensure full keyboard navigation support, proper ARIA attributes (`aria-expanded`, `aria-describedby`, `role`), and semantic HTML5 (`<main>`, `<nav>`, `<header>`, `<footer>`).
  - Maintain descriptive document titles, meta descriptions, and unique interactive element IDs for end-to-end testing.

## 4. UI Diagnostics & Debugging Runbook

1. **Fixing Visual Glitches & Layout Shift**:
   - Inspect layout containment and CSS flex/grid overflow settings (`overflow-hidden`, `min-w-0`).
   - Check browser autofill overrides (`-webkit-autofill`) to ensure input backgrounds and icons render cleanly.
2. **Optimizing Component Re-Renders**:
   - Use React DevTools Profiler to identify unnecessary parent component re-renders.
   - Memoize expensive calculations (`useMemo`) and callbacks (`useCallback`) passed down to child list items.
