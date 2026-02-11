"use client";

import { useEffect, useRef, useState } from "react";
import IntroOverlay from "./IntroOverlay";

const STORAGE_KEY = "introPlayed";

export default function IntroGate() {
  const [show, setShow] = useState(false);
  const initialOverflow = useRef<string | null>(null);

  useEffect(() => {
    const played = sessionStorage.getItem(STORAGE_KEY);
    // if (!played) {
    initialOverflow.current = document.body.style.overflow || "";
    document.body.style.overflow = "hidden";
    setShow(true);
    // }

    return () => {
      if (initialOverflow.current !== null) {
        document.body.style.overflow = initialOverflow.current;
      }
    };
  }, []);

  const handleDone = () => {
    sessionStorage.setItem(STORAGE_KEY, "1");
    setShow(false);
    document.body.style.overflow = initialOverflow.current || "auto";
  };

  if (!show) return null;
  return <IntroOverlay onDone={handleDone} />;
}
