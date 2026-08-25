// Landing-page footer. Brand text says "Image Classifier" (matching the
// nav's wordmark, per the earlier explicit rebrand away from
// "whatisthis"), not the "whatisthis" shown in the original reference —
// intentional, not an oversight. The right side was originally
// Source/Model card/Contact links; replaced with an attribution line.
export function Footer() {
  return (
    <footer className="landing-footer">
      <div className="landing-footer-inner">
        <span className="landing-footer-brand">Image Classifier · 2026</span>
        <span className="landing-footer-credit">Developed by Ishak Abdiaziz - AI Engineer</span>
      </div>
    </footer>
  );
}
