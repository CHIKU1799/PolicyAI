"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

/**
 * Ambient 3D depth layer for the landing hero: blurred gradient orbs and
 * slowly rotating perspective rings floating behind the text. The whole field
 * responds to mouse position, scroll, and arrow keys with a lerped parallax,
 * and goes fully static under prefers-reduced-motion.
 */
export function AmbientDepth() {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let targetX = 0;
    let targetY = 0;
    let curX = 0;
    let curY = 0;
    let scrollY = 0;
    let raf = 0;

    const onPointer = (e: PointerEvent) => {
      targetX = (e.clientX / window.innerWidth - 0.5) * 2;
      targetY = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    const onScroll = () => {
      scrollY = window.scrollY;
    };
    const onKey = (e: KeyboardEvent) => {
      const step = 0.35;
      if (e.key === "ArrowLeft") targetX = Math.max(-1, targetX - step);
      else if (e.key === "ArrowRight") targetX = Math.min(1, targetX + step);
      else if (e.key === "ArrowUp") targetY = Math.max(-1, targetY - step);
      else if (e.key === "ArrowDown") targetY = Math.min(1, targetY + step);
    };

    const tick = () => {
      curX += (targetX - curX) * 0.055;
      curY += (targetY - curY) * 0.055;
      const s = Math.min(scrollY, 900);
      root.style.setProperty("--px", curX.toFixed(4));
      root.style.setProperty("--py", curY.toFixed(4));
      root.style.setProperty("--sy", s.toFixed(1));
      raf = requestAnimationFrame(tick);
    };

    window.addEventListener("pointermove", onPointer, { passive: true });
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("keydown", onKey);
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", onPointer);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  return (
    <div ref={rootRef} className="pai-depth" aria-hidden>
      {/* blurred depth orbs, each on its own parallax rate */}
      <div className="pai-orb" style={{ width: 520, height: 520, left: "-8%", top: "-12%", background: "radial-gradient(circle at 35% 35%, rgba(46,107,247,.34), rgba(46,107,247,0) 68%)", ["--rate" as string]: "26" }} />
      <div className="pai-orb" style={{ width: 420, height: 420, right: "-6%", top: "6%", background: "radial-gradient(circle at 60% 40%, rgba(126,164,255,.30), rgba(126,164,255,0) 70%)", ["--rate" as string]: "-38" }} />
      <div className="pai-orb" style={{ width: 360, height: 360, left: "30%", bottom: "-20%", background: "radial-gradient(circle at 50% 50%, rgba(23,70,214,.22), rgba(23,70,214,0) 70%)", ["--rate" as string]: "16" }} />

      {/* 3D orbit rings on a tilted plane */}
      <div className="pai-scene" style={{ right: "4%", top: "2%" }}>
        <div className="pai-ring3d" style={{ width: 460, height: 460, animationDuration: "52s" }} />
        <div className="pai-ring3d" style={{ width: 330, height: 330, animationDuration: "38s", animationDirection: "reverse", opacity: 0.7 }} />
        <div className="pai-ring3d pai-ring3d-dot" style={{ width: 210, height: 210, animationDuration: "26s" }} />
      </div>
      <div className="pai-scene" style={{ left: "-2%", bottom: "-6%", opacity: 0.55 }}>
        <div className="pai-ring3d" style={{ width: 380, height: 380, animationDuration: "64s", animationDirection: "reverse" }} />
        <div className="pai-ring3d pai-ring3d-dot" style={{ width: 250, height: 250, animationDuration: "44s" }} />
      </div>

      <style jsx global>{`
        .pai-depth {
          position: absolute;
          inset: -80px 0 -40px 0;
          overflow: hidden;
          pointer-events: none;
          z-index: 0;
          --px: 0;
          --py: 0;
          --sy: 0;
        }
        .pai-orb {
          position: absolute;
          border-radius: 50%;
          filter: blur(46px);
          transform: translate3d(
            calc(var(--px) * var(--rate, 20) * 1px),
            calc(var(--py) * var(--rate, 20) * 1px - var(--sy) * 0.06px),
            0
          );
          will-change: transform;
        }
        .pai-scene {
          position: absolute;
          perspective: 900px;
          transform: translate3d(
            calc(var(--px) * -14px),
            calc(var(--py) * -10px - var(--sy) * 0.05px),
            0
          );
          will-change: transform;
        }
        .pai-ring3d {
          position: absolute;
          right: 0;
          top: 0;
          border: 1px solid rgba(46, 107, 247, 0.2);
          border-radius: 50%;
          transform-style: preserve-3d;
          animation: pai-orbit 40s linear infinite;
        }
        .pai-ring3d-dot::after {
          content: "";
          position: absolute;
          top: -5px;
          left: 50%;
          width: 9px;
          height: 9px;
          border-radius: 50%;
          background: #2e6bf7;
          box-shadow: 0 0 16px 4px rgba(46, 107, 247, 0.5);
        }
        @keyframes pai-orbit {
          from {
            transform: rotateX(68deg) rotateZ(0deg);
          }
          to {
            transform: rotateX(68deg) rotateZ(360deg);
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .pai-ring3d {
            animation: none;
          }
          .pai-orb,
          .pai-scene {
            transform: none;
          }
        }
      `}</style>
    </div>
  );
}

/**
 * Scroll-reveal wrapper: children fade-rise into place the first time they
 * enter the viewport. Instant under prefers-reduced-motion.
 */
export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setShown(true);
          io.disconnect();
        }
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.08 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: shown ? 1 : 0,
        transform: shown ? "none" : "translateY(26px)",
        transition: `opacity .7s cubic-bezier(.22,.9,.26,1) ${delay}ms, transform .7s cubic-bezier(.22,.9,.26,1) ${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}
