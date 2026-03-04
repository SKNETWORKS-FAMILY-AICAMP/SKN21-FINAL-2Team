"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";
import IntroOverlay from "./IntroOverlay";

const STORAGE_KEY = "introPlayed";

type IntroGateProps = {
  children: ReactNode;
};

export default function IntroGate({ children }: IntroGateProps) {
  const hasPlayedInSession = () => {
    if (typeof window === "undefined") return false;
    return window.sessionStorage.getItem(STORAGE_KEY) === "1";
  };

  const [show, setShow] = useState(() => {
    return !hasPlayedInSession();
  });
  const initialOverflow = useRef<string | null>(null);

  useEffect(() => {
    if (!show) {
      return;
    }
    initialOverflow.current = document.body.style.overflow || "";
    document.body.style.overflow = "hidden";

    return () => {
      if (initialOverflow.current !== null) {
        document.body.style.overflow = initialOverflow.current;
      }
    };
  }, [show]);

  const handleDone = () => {
    window.sessionStorage.setItem(STORAGE_KEY, "1");
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
