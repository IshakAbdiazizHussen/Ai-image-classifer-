import { LandingNav } from "@/components/LandingNav";

// Marketing landing page at "/". Deliberately outside the (app) route
// group's layout — it uses LandingNav instead of the "Classify"/"History"
// app header. Note: LandingNav's "How it works" / "Honest stats" / "Under
// the hood" links point to #how-it-works etc., which have no matching
// section here anymore — they're currently dead anchors.
export default function LandingPage() {
  return (
    <>
      <LandingNav />
    </>
  );
}
