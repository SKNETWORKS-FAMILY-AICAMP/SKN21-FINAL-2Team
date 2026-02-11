"use client";

import { useEffect, useRef } from "react";
import styles from "./intro.module.css";

type Props = { onDone: () => void };

// 단일 페이드인/페이드아웃만 남긴 간소화 버전
export default function IntroOverlay({ onDone }: Props) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const overlay = overlayRef.current;
    const title = titleRef.current;
    if (!overlay || !title) return;

    const timers: ReturnType<typeof setTimeout>[] = [];

    const setOpacity = (el: HTMLElement, value: number, transition = "opacity 500ms ease-out") => {
      el.style.transition = transition;
      el.style.opacity = value.toString();
    };

    // 초기 상태
    setOpacity(title, 0, "none");
    overlay.style.opacity = "1";

    // 1) 텍스트 페이드인
    timers.push(setTimeout(() => setOpacity(title, 1, "opacity 700ms ease-out"), 0));

    // 2) 잠시 유지 후 페이드아웃
    timers.push(setTimeout(() => setOpacity(title, 0, "opacity 600ms ease-out"), 1400));

    // 3) 오버레이 페이드아웃
    timers.push(
      setTimeout(() => {
        overlay.style.transition = "opacity 700ms ease-out";
        overlay.style.opacity = "0";
        overlay.style.pointerEvents = "none";
      }, 2000)
    );

    // 4) 완료 콜백
    timers.push(setTimeout(() => onDone(), 2700));

    return () => {
      timers.forEach(clearTimeout);
      overlay.style.opacity = "";
      overlay.style.pointerEvents = "";
      title.style.transition = "";
      title.style.opacity = "";
    };
  }, [onDone]);

  return (
    <div ref={overlayRef} className={styles.overlay}>
      <div className={styles.center}>
        <div ref={titleRef} className={`${styles.word} ${styles.layerCenter}`}>
          POLARIS KOREA RECOMMENDATIONS
        </div>
      </div>
    </div>
  );
}
