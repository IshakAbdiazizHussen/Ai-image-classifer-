import { LandingNav } from "@/components/LandingNav";
import { Hero } from "@/components/Hero";
import { ExampleCards } from "@/components/ExampleCards";
import { HowItWorks } from "@/components/HowItWorks";

// Marketing landing page at "/". Deliberately outside the (app) route
// group's layout — it uses LandingNav instead of the "Classify"/"History"
// app header. Note: the Hero's "See how it performs" link, and LandingNav's
// "Honest stats" / "Under the hood" links, still point to anchors
// (#honest-stats, #under-the-hood) with no matching section yet —
// "How it works" is now wired up via HowItWorks below.
export default function LandingPage() {
  return (
    <>
      <LandingNav />
      <Hero />
      <ExampleCards />
      <HowItWorks />
    </>
  );
}
