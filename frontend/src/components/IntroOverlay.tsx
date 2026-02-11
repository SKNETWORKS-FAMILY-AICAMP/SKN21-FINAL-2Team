"use client";

import { useEffect, useRef } from "react";
import styles from "./intro.module.css";

type Props = { onDone: () => void };

// GSAP 없이 타임라인을 수동 구성해 동일한 연출을 구현합니다.
export default function IntroOverlay({ onDone }: Props) {
  const overlayRef = useRef<HTMLDivElement>(null);

  const phraseRef = useRef<HTMLDivElement>(null); // Polaris Korea AI
  const leftRef = useRef<HTMLDivElement>(null); // Pola / Korea AI
  const rightRef = useRef<HTMLDivElement>(null); // P / Korea
  const logoRef = useRef<HTMLDivElement>(null); // PK

  useEffect(() => {
    const overlay = overlayRef.current;
    const phrase = phraseRef.current;
    const left = leftRef.current;
    const right = rightRef.current;
    const logo = logoRef.current;
    if (!overlay || !phrase || !left || !right || !logo) return;

    const timers: ReturnType<typeof setTimeout>[] = [];

    const setOpacity = (el: HTMLElement, value: number, transition = "opacity 150ms ease-out") => {
      el.style.transition = transition;
      el.style.opacity = value.toString();
    };

    const setX = (el: HTMLElement, value: number, transition = "transform 200ms ease-out") => {
      el.style.transition = transition;
      el.style.setProperty("--tx", `${value}px`);
    };

    // 초기 상태
    [phrase, left, right, logo].forEach((el) => {
      setOpacity(el, 0, "none");
    });
    [left, right].forEach((el) => setX(el, 0, "none"));
    overlay.style.opacity = "1";

    // 1) "POLARIS RECOMMENDATIONS" 천천히 등장
    timers.push(
      setTimeout(() => {
        setOpacity(phrase, 1, "opacity 260ms ease-out");
      }, 0)
    );

    // 2) 글리치 + 밝아짐 (요청으로 비활성화)
    // timers.push(setTimeout(() => phrase.classList.add(styles.glitchOn), 600));
    // timers.push(setTimeout(() => phrase.classList.remove(styles.glitchOn), 900));

    // 3) 문구 페이드아웃
    timers.push(
      setTimeout(() => setOpacity(phrase, 0, "opacity 260ms ease-out"), 1200)
    );

    // Pola / Korea AI 스냅 전환
    timers.push(
      setTimeout(() => {
        left.textContent = "Polaris";
        right.textContent = "Korea AI";
        left.classList.add(styles.glitchOn);
        right.classList.add(styles.glitchOn);
        setOpacity(left, 1, "opacity 50ms linear");
        setOpacity(right, 1, "opacity 50ms linear");
      }, 1450)
    );

    // 좌우 벌어짐
    timers.push(
      setTimeout(() => {
        setX(left, -140, "transform 260ms cubic-bezier(0.42,0,1,1)");
        setX(right, 140, "transform 260ms cubic-bezier(0.42,0,1,1)");
      }, 1550)
    );

    // 텍스트 정리
    timers.push(
      setTimeout(() => {
        left.textContent = "Pola";
        right.textContent = "Korea AI";
      }, 1900)
    );

    // 중앙으로 재결합
    timers.push(
      setTimeout(() => {
        setX(left, 0, "transform 260ms ease-in-out");
        setX(right, 0, "transform 260ms ease-in-out");
      }, 2050)
    );

    // 오버레이 페이드아웃
    timers.push(
      setTimeout(() => {
        overlay.style.transition = "opacity 260ms ease-out";
        overlay.style.opacity = "0";
        overlay.style.pointerEvents = "none";
      }, 3000)
    );

    // 종료 콜백
    timers.push(
      setTimeout(() => {
        onDone();
      }, 3500)
    );

    return () => {
      timers.forEach(clearTimeout);
      overlay.style.opacity = "";
      overlay.style.pointerEvents = "";
      [phrase, left, right, logo].forEach((el) => {
        el.style.transition = "";
        el.style.opacity = "";
        el.style.transform = "";
        el.classList.remove(styles.glitchOn);
      });
      logo.style.left = "";
    };
  }, [onDone]);

  return (
    <div ref={overlayRef} className={styles.overlay} aria-hidden="true">
      <div className={styles.center}>
        <div
          ref={phraseRef}
          className={`${styles.word} ${styles.glitch} ${styles.layerCenter}`}
          data-text="POLARIS RECOMMENDATIONS"
        >
          POLARIS RECOMMENDATIONS
        </div>

        <div className={`${styles.splitRow} ${styles.layer}`}>
          <div
            ref={leftRef}
            className={`${styles.word} ${styles.glitch}`}
            data-text="POLARIS"
          >
            POLARIS
          </div>
          <div
            ref={rightRef}
            className={`${styles.word} ${styles.glitch}`}
            data-text="RECOMMENDATIONS"
          >
            RECOMMENDATIONS
          </div>
        </div>

        <div
          ref={logoRef}
          className={`${styles.word} ${styles.glitch} ${styles.layerCenter}`}
          data-text="POLARIS RECOMMENDATIONS"
        >
          POLARIS-K
        </div>
      </div>
    </div>
  );
}
