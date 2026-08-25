import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";

// Shared nav — used on the landing page AND reused verbatim on /upload
// and /history (see app/(app)/layout.tsx), so it's the same everywhere,
// not landing-page-only. Wordmark split into a neutral half and a mint
// half, two anchor links, and a pill CTA into the real app. ThemeToggle
// sets data-theme on <html>, so it themes every page, not just this
// header — see globals.css's theme-token comment and layout.tsx's
// beforeInteractive init script.
//
// The two anchor links use "/#..." (not bare "#...") on purpose: those
// sections only exist on "/". A bare "#how-it-works" would do nothing on
// /upload or /history (no matching id there); "/#how-it-works" navigates
// to the landing page and lands on the section, and still works as a
// same-page scroll when already on "/" (unchanged pathname + new hash is
// native browser behavior, doesn't force a reload).
export function LandingNav() {
  return (
    <header className="landing-nav">
      <div className="landing-nav-inner">
        <Link href="/" className="landing-nav-brand">
          Image <span className="landing-nav-brand-accent">Classifier</span>
        </Link>

        <nav className="landing-nav-links">
          <a href="/#how-it-works">How it works</a>
          <a href="/#honest-stats">Honest stats</a>
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
