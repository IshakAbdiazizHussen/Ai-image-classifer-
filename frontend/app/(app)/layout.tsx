import { LandingNav } from "@/components/LandingNav";

// Route-group layout (URL is unaffected by the "(app)" folder name) —
// scoped to /upload and /history. Now reuses LandingNav verbatim instead
// of its own separate .site-header, so the nav (wordmark, links, theme
// toggle, CTA) is identical everywhere, not just on "/". LandingNav's two
// anchor links point at "/#how-it-works" / "/#honest-stats" (not bare
// "#..."), so from here they navigate back to the landing page and land
// on the right section, rather than doing nothing (no matching id exists
// on this page).
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <LandingNav />
      {children}
    </>
  );
}
