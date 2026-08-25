import { LandingNav } from "@/components/LandingNav";
import { Hero } from "@/components/Hero";
import { ExampleCards } from "@/components/ExampleCards";

// Marketing landing page at "/". Deliberately outside the (app) route
// group's layout — it uses LandingNav instead of the "Classify"/"History"
// app header. Note: LandingNav's "How it works" / "Honest stats" / "Under
// the hood" links, and the Hero's "See how it performs" link, point to
// anchors (#how-it-works etc.) with no matching section here yet — still
// dead anchors below ExampleCards.
export default function LandingPage() {
  return (
    <>
      <LandingNav />
      <Hero />
      <ExampleCards />
    </>
  );
}
