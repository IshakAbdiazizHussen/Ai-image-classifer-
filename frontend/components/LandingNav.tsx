import Link from "next/link";

// Landing-page-only nav (distinct from the "Classify"/"History" header used
// on /upload and /history — see app/(app)/layout.tsx). Wordmark split into
// a neutral half and a mint half, three anchor links, and a pill CTA into
// the real app.
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

        <Link href="/upload" className="landing-nav-cta">
          Upload an image
        </Link>
      </div>
    </header>
  );
}
