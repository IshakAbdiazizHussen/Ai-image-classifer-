import Link from "next/link";

// Landing-page hero, placed directly below LandingNav. Copy/structure
// matches the supplied reference exactly: eyebrow badge, three-line
// headline, subtitle, and a primary/secondary CTA pair.
export function Hero() {
  return (
    <section className="hero">
      <span className="hero-badge">Ten categories · about 40 ms per guess</span>

      <h1 className="hero-title">
        Show it a picture. It tells you what it sees — and how sure it is.
      </h1>

      <p className="hero-subtitle">
        Drop in a JPEG, PNG or WebP. You get one answer, a confidence score,
        and the full list of what else it considered. It is often right,
        sometimes wrong, and always shows its work.
      </p>

      <div className="hero-actions">
        <Link href="/upload" className="hero-cta-primary">
          Try it now
        </Link>
        <a href="#honest-stats" className="hero-cta-secondary">
          See how it performs
        </a>
      </div>
    </section>
  );
}
