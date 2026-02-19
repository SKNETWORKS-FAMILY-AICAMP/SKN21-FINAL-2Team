"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";
import IntroOverlay from "./IntroOverlay";

const STORAGE_KEY = "introPlayed";

type IntroGateProps = {
  children: ReactNode;
};

export default function IntroGate({ children }: IntroGateProps) {
  const [show, setShow] = useState(true);
  const initialOverflow = useRef<string | null>(null);

  useEffect(() => {
    const played = localStorage.getItem(STORAGE_KEY);
    if (played) {
      setShow(false);
      return;
    }
    initialOverflow.current = document.body.style.overflow || "";
    document.body.style.overflow = "hidden";

    return () => {
      if (initialOverflow.current !== null) {
        document.body.style.overflow = initialOverflow.current;
      }
    };
  }, []);

  const handleDone = () => {
    localStorage.setItem(STORAGE_KEY, "1");
    setShow(false);
    document.body.style.overflow = initialOverflow.current || "auto";
  };

  return (
    <>
      {children}
      {show && <IntroOverlay onDone={handleDone} />}
    </>
  );
}
