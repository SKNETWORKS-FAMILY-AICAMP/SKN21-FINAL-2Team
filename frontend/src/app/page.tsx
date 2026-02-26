import { Header } from "@/components/landing/Header";
import { Hero } from "@/components/landing/Hero";
import { Features } from "@/components/landing/Features";
import { Destinations } from "@/components/landing/Destinations";
import { ReviewSection } from "@/components/landing/ReviewSection";
import { CTA } from "@/components/landing/CTA";
import { Footer } from "@/components/landing/Footer";

import IntroGate from "@/components/IntroGate";

export default function Home() {
  return (
    <IntroGate>
      <div className="min-h-screen bg-white font-sans text-black selection:bg-black selection:text-white scroll-smooth">
        <Header />
        <main>
          <Hero />
          <Features />
          <Destinations />
          <ReviewSection />
          <CTA />
        </main>
        <Footer />
      </div>
    </IntroGate>
  );
}
