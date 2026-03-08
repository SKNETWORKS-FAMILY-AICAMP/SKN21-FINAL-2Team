import { Header } from "@/app/components/Header";
import { Hero } from "@/app/components/Hero";
import { Features } from "@/app/components/Features";
import { Destinations } from "@/app/components/Destinations";
import { ReviewSection } from "@/app/components/ReviewSection";
import { CTA } from "@/app/components/CTA";
import { Footer } from "@/app/components/Footer";

export function HomePage() {
  return (
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
  );
}
