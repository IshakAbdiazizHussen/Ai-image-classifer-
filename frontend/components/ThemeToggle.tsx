"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark";

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  try {
    window.localStorage.setItem("theme", theme);
  } catch {
    // Private browsing / disabled storage — theme still applies for this
    // page load, it just won't persist to the next one.
  }
}

// Circular icon button in LandingNav, right of "Upload an image". The
// actual initial theme is decided before this ever mounts, by the inline
// beforeInteractive script in layout.tsx (localStorage, else OS
// prefers-color-scheme, else dark) — this component only reflects and
// toggles document.documentElement.dataset.theme, it never guesses a
// value of its own.
//
// `mounted` gates the real render: SSR has no access to that attribute,
// so the server-rendered markup can't know the real theme. Rendering
// theme-dependent output before mount would mismatch what the server
// sent and trigger a hydration warning — an unstyled placeholder for one
// frame is the standard fix (same approach next-themes uses).
export function ThemeToggle() {
  const [mounted, setMounted] = useState(false);
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    setTheme((document.documentElement.dataset.theme as Theme) || "dark");
    setMounted(true);
  }, []);

  function toggle() {
    const next: Theme = theme === "light" ? "dark" : "light";
    applyTheme(next);
    setTheme(next);
  }

  if (!mounted) {
    return <span className="theme-toggle theme-toggle-placeholder" aria-hidden="true" />;
  }

  const isLight = theme === "light";

  return (
    <button
      type="button"
      className="theme-toggle"
      role="switch"
      aria-checked={isLight}
      aria-label={isLight ? "Switch to dark mode" : "Switch to light mode"}
      onClick={toggle}
    >
      {/* key={theme} forces a remount on every toggle, which replays the
          CSS entrance animation (rotate + scale + fade) defined on
          .theme-toggle-icon — that's what gives the swap its motion,
          rather than an abrupt icon swap. */}
      <span className="theme-toggle-icon" key={theme}>
        {isLight ? (
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <circle cx="12" cy="12" r="4.5" fill="currentColor" />
            <g stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M12 2.5v2.5M12 19v2.5M4.2 4.2l1.8 1.8M18 18l1.8 1.8M2.5 12H5M19 12h2.5M4.2 19.8L6 18M18 6l1.8-1.8" />
            </g>
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path
              fill="currentColor"
              d="M20.5 14.4A8.5 8.5 0 1 1 9.6 3.5a7 7 0 0 0 10.9 10.9Z"
            />
          </svg>
        )}
      </span>
    </button>
  );
}
