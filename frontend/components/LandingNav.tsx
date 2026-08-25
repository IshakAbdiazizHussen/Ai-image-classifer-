import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";

// Landing-page-only nav (distinct from the "Classify"/"History" header used
// on /upload and /history — see app/(app)/layout.tsx). Wordmark split into
// a neutral half and a mint half, three anchor links, and a pill CTA into
// the real app. ThemeToggle sets data-theme on <html>, so it themes every
// page, not just this header — see globals.css's theme-token comment and
// layout.tsx's beforeInteractive init script.
export function LandingNav() {
  return (
    <header className="landing-nav">
      <div className="landing-nav-inner">
        <Link href="/" className="landing-nav-brand">
          Image <span className="landing-nav-brand-accent">Classifier</span>
        </Link>

        <nav className="landing-nav-links">
          <a href="#how-it-works">How it works</a>
          <a href="#honest-stats">Honest stats</a>
          <a href="#under-the-hood">Under the hood</a>
        </nav>

        <div className="landing-nav-actions">
          <Link href="/upload" className="landing-nav-cta">
            Upload an image
          </Link>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
