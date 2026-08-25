import Link from "next/link";

// Route-group layout (URL is unaffected by the "(app)" folder name) —
// scoped to /upload and /history only, so the functional app header
// doesn't leak onto the marketing landing page at "/", which has its own
// LandingNav instead.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <header className="site-header">
        <span className="site-title">Image Classifier</span>
        <nav>
          <Link href="/upload">Classify</Link>
          <Link href="/history">History</Link>
        </nav>
      </header>
      {children}
    </>
  );
}
