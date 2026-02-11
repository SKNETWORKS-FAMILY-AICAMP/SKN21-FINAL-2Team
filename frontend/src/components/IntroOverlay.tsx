"use client";

import { useEffect, useRef, useState } from "react";

type Props = { onDone: () => void };

// Lightweight manual tweening to avoid relying on external downloads.
export default function IntroOverlay({ onDone }: Props) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const logoRef = useRef<HTMLDivElement>(null);
  const [count, setCount] = useState(0);

  useEffect(() => {
    const overlay = overlayRef.current;
    const logo = logoRef.current;
    if (!overlay || !logo) return;

    let rafId: number;
    let glitchTimeout: ReturnType<typeof setTimeout>;
    let exitTimeout: ReturnType<typeof setTimeout>;

    const duration = 1800;
    const start = performance.now();

    const animateCounter = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      const value = Math.floor(progress * 100);
      setCount(value);
      if (progress < 1) {
        rafId = requestAnimationFrame(animateCounter);
      } else {
        setCount(100);
        startGlitch();
      }
    };

    const startGlitch = () => {
      logo.classList.add("logo-shake");
      glitchTimeout = setTimeout(() => {
        logo.classList.remove("logo-shake");
        startExit();
      }, 500);
    };

    const startExit = () => {
      const handleDone = () => {
        overlay.removeEventListener("transitionend", handleDone);
        onDone();
      };
      overlay.addEventListener("transitionend", handleDone);
      overlay.classList.add("intro-exit");
      // Fallback in case transitionend doesn't fire
      exitTimeout = setTimeout(() => {
        overlay.removeEventListener("transitionend", handleDone);
        onDone();
      }, 1300);
    };

    rafId = requestAnimationFrame(animateCounter);

    return () => {
      cancelAnimationFrame(rafId);
      clearTimeout(glitchTimeout);
      clearTimeout(exitTimeout);
      overlay.classList.remove("intro-exit");
      logo.classList.remove("logo-shake");
    };
  }, [onDone]);

  return (
    <div ref={overlayRef} className="intro">
      <div className="intro-inner">
        <div className="counter">{count}%</div>
        <div ref={logoRef} className="logo glitch" data-text="Polaris-K">
          Polaris-K
        </div>
      </div>
    </div>
  );
}
