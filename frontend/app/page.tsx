import { LandingNav } from "@/components/LandingNav";
import { Hero } from "@/components/Hero";
import { ExampleCards } from "@/components/ExampleCards";
import { HowItWorks } from "@/components/HowItWorks";
import { HonestStats } from "@/components/HonestStats";
import { Footer } from "@/components/Footer";

// Marketing landing page at "/". Deliberately outside the (app) route
// group's layout — it uses LandingNav instead of the "Classify"/"History"
// app header.
export default function LandingPage() {
  return (
    <>
      <LandingNav />
      <Hero />
      <ExampleCards />
      <HowItWorks />
      <HonestStats />
      <Footer />
    </>
  );
}
