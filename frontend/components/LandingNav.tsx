import Link from "next/link";

// Landing-page-only nav (distinct from the "Classify"/"History" header used
// on /upload and /history — see app/(app)/layout.tsx). Matches the supplied
// reference screenshot: wordmark split into a neutral half and a mint half,
// three anchor links into the page below, and a pill CTA into the real app.
export function LandingNav() {
  return (
    <header className="landing-nav">
      <Link href="/" className="landing-nav-brand">
        what<span className="landing-nav-brand-accent">isthis</span>
      </Link>

      <nav className="landing-nav-links">
        <a href="#how-it-works">How it works</a>
        <a href="#honest-stats">Honest stats</a>
        <a href="#under-the-hood">Under the hood</a>
      </nav>

      <Link href="/upload" className="landing-nav-cta">
        Upload an image
      </Link>
    </header>
  );
}
