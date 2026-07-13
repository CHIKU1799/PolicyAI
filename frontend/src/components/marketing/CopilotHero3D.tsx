"use client";

/**
 * 3D hero for the Copilot blog post: an orbiting carousel of regulation cards
 * around a pulsing Copilot core, on a pointer-tracked parallax stage. Pure CSS
 * transforms (no WebGL dependency), respects prefers-reduced-motion.
 */

import { useRef, useState } from "react";

const CARDS = [
  { reg: "RBI", chip: "High impact", title: "Digital Lending Directions", sub: "4 obligations · Microfinance" },
  { reg: "SEBI", chip: "Medium", title: "Cybersecurity & resilience framework", sub: "12 requirements extracted" },
  { reg: "RBI", chip: "Critical", title: "KYC Master Direction amendments", sub: "CKYCR · UCIC · CDD" },
  { reg: "IRDAI", chip: "Medium", title: "Policyholder protection norms", sub: "7 requirements extracted" },
  { reg: "RBI", chip: "High impact", title: "Scale Based Regulation framework", sub: "layer-wise applicability" },
  { reg: "SEBI", chip: "Low", title: "Valuation of AIF portfolios", sub: "disclosure calendar updated" },
];

const CHIP_STYLE: Record<string, { color: string; bg: string }> = {
  Critical: { color: "#C0392B", bg: "#FBEBEB" },
  "High impact": { color: "#C0392B", bg: "#FBEBEB" },
  Medium: { color: "#A6691B", bg: "#FBF1E1" },
  Low: { color: "#1F9D5B", bg: "#E6F4EC" },
};

export default function CopilotHero3D() {
  const stage = useRef<HTMLDivElement>(null);
  const [tilt, setTilt] = useState({ x: -12, y: 0 });

  function onMove(e: React.PointerEvent) {
    const r = stage.current?.getBoundingClientRect();
    if (!r) return;
    const nx = (e.clientX - r.left) / r.width - 0.5;
    const ny = (e.clientY - r.top) / r.height - 0.5;
    setTilt({ x: -12 - ny * 10, y: nx * 14 });
  }

  return (
    <div
      ref={stage}
      onPointerMove={onMove}
      onPointerLeave={() => setTilt({ x: -12, y: 0 })}
      className="pai-stage relative mx-auto my-4 h-[380px] w-full max-w-4xl overflow-hidden rounded-3xl"
      style={{
        background:
          "radial-gradient(ellipse 75% 90% at 50% 120%, rgba(46,107,247,.35), transparent 60%), linear-gradient(160deg, #171436, #0C1A38 70%)",
        perspective: "1100px",
      }}
    >
      {/* starfield dust */}
      <div className="pai-dust" aria-hidden />

      {/* the 3D scene */}
      <div
        className="absolute left-1/2 top-1/2 h-0 w-0"
        style={{
          transformStyle: "preserve-3d",
          transform: `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`,
          transition: "transform .25s ease-out",
        }}
      >
        {/* orbit ring guides */}
        <div className="pai-ring" style={{ width: 460, height: 460 }} aria-hidden />
        <div className="pai-ring" style={{ width: 620, height: 620, opacity: 0.5 }} aria-hidden />

        {/* the Copilot core */}
        <div className="pai-core" aria-hidden>
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
            <path
              d="M12 3l1.8 4.6L18.5 9l-4.7 1.4L12 15l-1.8-4.6L5.5 9l4.7-1.4L12 3z"
              fill="#fff"
            />
          </svg>
        </div>
        <div className="pai-pulse" aria-hidden />
        <div className="pai-pulse" style={{ animationDelay: "1.4s" }} aria-hidden />

        {/* orbiting regulation cards */}
        <div className="pai-orbit" style={{ transformStyle: "preserve-3d" }}>
          {CARDS.map((c, i) => {
            const chip = CHIP_STYLE[c.chip];
            return (
              <div
                key={i}
                className="pai-card"
                style={{
                  transform: `rotateY(${i * 60}deg) translateZ(300px) rotateY(${-i * 60}deg)`,
                }}
              >
                <div className="pai-card-inner" style={{ animationDelay: `${i * -3.33}s` }}>
                  <div className="mb-1 flex items-center gap-1.5">
                    <span className="font-mono text-[9px] font-extrabold" style={{ color: "#7EA4FF" }}>
                      {c.reg}
                    </span>
                    <span
                      className="rounded px-1 py-px text-[8px] font-bold"
                      style={{ color: chip.color, background: chip.bg }}
                    >
                      {c.chip}
                    </span>
                  </div>
                  <div className="text-[11px] font-semibold leading-tight text-white">{c.title}</div>
                  <div className="mt-0.5 text-[9px]" style={{ color: "#9FA6C8" }}>
                    {c.sub}
                  </div>
                  <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full" style={{ background: "rgba(255,255,255,.12)" }}>
                    <div className="pai-scan h-full rounded-full" style={{ background: "linear-gradient(90deg,#2E6BF7,#7EA4FF)" }} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* caption */}
      <div className="absolute bottom-4 left-0 right-0 text-center text-[11px] tracking-wide" style={{ color: "#8B93B8" }}>
        Every orbiting circular is read, extracted, and weighed against your firm&apos;s profile
      </div>

      <style jsx>{`
        .pai-dust {
          position: absolute;
          inset: 0;
          background-image: radial-gradient(1px 1px at 12% 30%, rgba(255, 255, 255, 0.5), transparent),
            radial-gradient(1px 1px at 68% 18%, rgba(255, 255, 255, 0.4), transparent),
            radial-gradient(1.5px 1.5px at 84% 60%, rgba(126, 164, 255, 0.5), transparent),
            radial-gradient(1px 1px at 30% 74%, rgba(255, 255, 255, 0.35), transparent),
            radial-gradient(1.5px 1.5px at 50% 40%, rgba(126, 164, 255, 0.35), transparent);
          animation: pai-drift 14s ease-in-out infinite alternate;
        }
        .pai-ring {
          position: absolute;
          left: 50%;
          top: 50%;
          transform: translate(-50%, -50%) rotateX(90deg);
          border: 1px solid rgba(126, 164, 255, 0.22);
          border-radius: 50%;
        }
        .pai-core {
          position: absolute;
          left: -26px;
          top: -26px;
          width: 52px;
          height: 52px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 16px;
          background: linear-gradient(135deg, #2e6bf7, #1746d6);
          box-shadow: 0 0 40px 8px rgba(46, 107, 247, 0.55);
          animation: pai-bob 5s ease-in-out infinite;
        }
        .pai-pulse {
          position: absolute;
          left: -26px;
          top: -26px;
          width: 52px;
          height: 52px;
          border-radius: 16px;
          border: 1.5px solid rgba(126, 164, 255, 0.7);
          animation: pai-pulse 2.8s ease-out infinite;
        }
        .pai-orbit {
          position: absolute;
          animation: pai-spin 26s linear infinite;
        }
        .pai-card {
          position: absolute;
          left: -78px;
          top: -52px;
          width: 156px;
        }
        .pai-card-inner {
          border-radius: 12px;
          padding: 10px;
          background: rgba(23, 28, 58, 0.82);
          border: 1px solid rgba(126, 164, 255, 0.28);
          backdrop-filter: blur(4px);
          box-shadow: 0 14px 34px -12px rgba(0, 0, 0, 0.65);
          animation: pai-float 6.5s ease-in-out infinite;
        }
        .pai-scan {
          width: 40%;
          animation: pai-scan 2.4s ease-in-out infinite alternate;
        }
        @keyframes pai-spin {
          from {
            transform: rotateY(0deg);
          }
          to {
            transform: rotateY(360deg);
          }
        }
        @keyframes pai-float {
          0%,
          100% {
            transform: translateY(0);
          }
          50% {
            transform: translateY(-8px);
          }
        }
        @keyframes pai-bob {
          0%,
          100% {
            transform: translateY(0) scale(1);
          }
          50% {
            transform: translateY(-6px) scale(1.04);
          }
        }
        @keyframes pai-pulse {
          from {
            transform: scale(1);
            opacity: 0.8;
          }
          to {
            transform: scale(3.2);
            opacity: 0;
          }
        }
        @keyframes pai-scan {
          from {
            width: 22%;
          }
          to {
            width: 92%;
          }
        }
        @keyframes pai-drift {
          from {
            transform: translateY(0);
          }
          to {
            transform: translateY(-14px);
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .pai-orbit,
          .pai-card-inner,
          .pai-core,
          .pai-pulse,
          .pai-scan,
          .pai-dust {
            animation: none;
          }
        }
      `}</style>
    </div>
  );
}
