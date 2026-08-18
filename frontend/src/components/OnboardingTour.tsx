"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  HelpCircle,
  LayoutDashboard,
  PartyPopper,
  Radar,
  Share2,
  ShieldAlert,
  ShieldCheck,
  ShieldHalf,
  Sparkles,
  TriangleAlert,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { getSupabase } from "@/lib/supabase";

// First run product tour. Mounted once from the (app) layout, it opens
// automatically for users who have never seen it (persisted in localStorage,
// keyed by the Supabase user id when available) and can be replayed anytime
// via the TourLaunchButton in the Topbar.
//
// Presentation: a true spotlight cutout (the highlighted feature stays fully
// sharp and undimmed while everything around it darkens) plus a compact card
// anchored next to the target with a pointer arrow. Steps without a visible
// target fall back to a centered card; on mobile the card docks to the bottom
// while the cutout still tracks the target.

const OPEN_EVENT = "policyai:tour:open";
const STORAGE_PREFIX = "policyai.tour.v1";

type Step = {
  key: string;
  title: string;
  desc: string;
  icon: LucideIcon;
  href?: string;
  hrefLabel?: string;
  /** matches a data-tour attribute on Sidebar / Topbar chrome */
  target?: string;
};

const STEPS: Step[] = [
  {
    key: "welcome",
    title: "Welcome to PolicyAI",
    desc: "Your compliance command center for RBI, SEBI and the wider Indian regulatory landscape. This one minute tour shows you what lives where.",
    icon: ShieldHalf,
  },
  {
    key: "dashboard",
    title: "See your posture at a glance",
    desc: "The dashboard tracks live KPIs: compliance score, open gaps, upcoming deadlines and the latest regulatory activity across your obligations and controls.",
    icon: LayoutDashboard,
    href: "/dashboard",
    target: "nav-dashboard",
  },
  {
    key: "horizon",
    title: "Never miss a new circular",
    desc: "PolicyAI watches the regulators for you. Use Scan now on the dashboard to pull fresh circulars on demand, and new alerts land in this bell as they arrive.",
    icon: Radar,
    href: "/dashboard",
    hrefLabel: "Open dashboard",
    target: "alerts",
  },
  {
    key: "obligations",
    title: "Know exactly what is required",
    desc: "Each regulation is broken down into structured obligations, mapped to the controls, policies and tasks that satisfy it, so nothing stays buried in a 60 page circular.",
    icon: ShieldAlert,
    href: "/obligations",
    target: "nav-obligations",
  },
  {
    key: "gaps",
    title: "Catch weak spots before auditors do",
    desc: "Gap analysis flags obligations that are not yet fully covered by your controls or policies, and helps you prioritise what to fix first.",
    icon: TriangleAlert,
    href: "/gaps",
    target: "nav-gaps",
  },
  {
    key: "controls",
    title: "Prove your controls really work",
    desc: "Maintain your control library, map every control to the obligations it covers, and record test results that feed your live compliance score.",
    icon: ShieldCheck,
    href: "/controls",
    target: "nav-controls",
  },
  {
    key: "knowledge-base",
    title: "Teach PolicyAI your business",
    desc: "Upload internal policies, registrations and licenses to the Knowledge Base. PolicyAI reads them to tailor gap analysis and answers to your firm.",
    icon: BookOpen,
    href: "/knowledge-base",
    hrefLabel: "Upload documents",
    target: "nav-knowledge-base",
  },
  {
    key: "copilot",
    title: "Ask anything, get cited answers",
    desc: "The PolicyAI Copilot answers questions across regulations and your own documents, grounded with citations. Press ⌘J to open it from anywhere.",
    icon: Sparkles,
    href: "/ask",
    hrefLabel: "Open Copilot",
    target: "ask",
  },
  {
    key: "workflow",
    title: "Run the whole flow from one page",
    desc: "The Workflow page shows the full journey, from a circular landing to audit-ready proof, and lets you assign every open task to a teammate with a due date.",
    icon: Share2,
    href: "/workflow",
    target: "nav-workflow",
  },
  {
    key: "done",
    title: "You are all set",
    desc: "That is the full lap. Replay this tour anytime from the help icon in the top bar, and press ⌘K to search from anywhere.",
    icon: PartyPopper,
  },
];

/** Programmatic replay trigger, safe to call from anywhere in the app shell. */
export function startTour() {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(OPEN_EVENT));
}

/** Subtle "Take the tour" affordance for the Topbar. */
export function TourLaunchButton() {
  return (
    <button
      onClick={startTour}
      title="Take the product tour"
      aria-label="Take the product tour"
      className="hidden h-9 w-9 flex-none items-center justify-center rounded-lg text-[var(--muted)] hover:bg-[#f2f2ef] sm:flex"
    >
      <HelpCircle size={18} />
    </button>
  );
}

type RingRect = { top: number; left: number; width: number; height: number };
type ArrowSide = "left" | "right" | "top" | "bottom";
type CardPos = {
  top: number;
  left: number;
  width: number;
  arrow: { side: ArrowSide; offset: number } | null;
};

const SPOT_PAD = 8; // breathing room around the highlighted element
const CARD_GAP = 14; // gap between the cutout and the anchored card
const VIEW_MARGIN = 16; // minimum distance from the viewport edges
const POLL_MS = 140;
const POLL_MAX = 20; // ~2.8s of waiting for a target after navigation

function arrowStyle(a: { side: ArrowSide; offset: number }): CSSProperties {
  switch (a.side) {
    case "left":
      return { left: -6, top: a.offset - 6 };
    case "right":
      return { right: -6, top: a.offset - 6 };
    case "top":
      return { top: -6, left: a.offset - 6 };
    case "bottom":
      return { bottom: -6, left: a.offset - 6 };
  }
}

export default function OnboardingTour() {
  const router = useRouter();
  const pathname = usePathname();
  const [phase, setPhase] = useState<"closed" | "open" | "closing">("closed");
  const [step, setStep] = useState(0);
  const [ring, setRing] = useState<RingRect | null>(null);
  const [pos, setPos] = useState<CardPos | null>(null);
  const [isMobile, setIsMobile] = useState(false);
  const storageKey = useRef(`${STORAGE_PREFIX}:anon`);
  const cardRef = useRef<HTMLDivElement>(null);
  const posRef = useRef<HTMLDivElement>(null);
  // Which steps we have already auto navigated for in this tour run, so a
  // missing target never triggers a router.push loop.
  const navigatedSteps = useRef<Set<number>>(new Set());

  const open = useCallback(() => {
    navigatedSteps.current = new Set();
    setStep(0);
    setRing(null);
    setPos(null);
    setPhase("open");
  }, []);

  const close = useCallback((completed: boolean) => {
    const state = completed ? "done" : "skipped";
    try {
      window.localStorage.setItem(storageKey.current, state);
    } catch {
      // storage unavailable: the tour will simply offer itself again next visit
    }
    // Also persist on the auth user, so a new device or cleared browser does
    // not restart the tour for someone who already finished it.
    getSupabase()
      ?.auth.updateUser({ data: { policyai_tour: state } })
      .catch(() => {});
    setPhase("closing");
    window.setTimeout(() => setPhase("closed"), 240);
  }, []);

  const back = useCallback(() => setStep((s) => Math.max(s - 1, 0)), []);
  const next = useCallback(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), []);

  // First run: resolve the storage key (Supabase user id when signed in) and
  // auto open if this user has never completed or skipped the tour.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      let id = "anon";
      let doneOnServer = false;
      try {
        const supabase = getSupabase();
        if (supabase) {
          const { data } = await supabase.auth.getUser();
          if (data.user?.id) id = data.user.id;
          doneOnServer = Boolean(data.user?.user_metadata?.policyai_tour);
        }
      } catch {
        // fall back to the generic key
      }
      if (cancelled) return;
      storageKey.current = `${STORAGE_PREFIX}:${id}`;
      if (doneOnServer) return;
      try {
        if (!window.localStorage.getItem(storageKey.current)) {
          window.setTimeout(() => {
            if (!cancelled) open();
          }, 650);
        }
      } catch {
        // no storage, skip auto open rather than nagging on every navigation
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open]);

  // Replay trigger from the Topbar help button.
  useEffect(() => {
    const onOpen = () => open();
    window.addEventListener(OPEN_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_EVENT, onOpen);
  }, [open]);

  // Keyboard: Escape skips, arrows navigate.
  useEffect(() => {
    if (phase !== "open") return;
    const last = step === STEPS.length - 1;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        close(false);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        if (last) close(true);
        else next();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        back();
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [phase, step, close, next, back]);

  // Mobile layout: card docks to the bottom but the cutout still tracks the
  // target.
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const update = () => setIsMobile(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  // Spotlight: locate the step target (data-tour attributes on the chrome)
  // and keep the cutout in sync with resize, scroll and step changes. If the
  // target is missing and the step has a route, navigate there and poll
  // briefly for the element; if it never appears, fall back to the centered
  // card (ring stays null).
  useEffect(() => {
    if (phase === "closed") return;
    const stepDef = STEPS[step];
    const target = stepDef.target;
    if (!target) {
      setRing(null);
      return;
    }

    const measure = () => {
      const el = document.querySelector(`[data-tour="${target}"]`);
      if (!el) {
        setRing(null);
        return false;
      }
      const r = el.getBoundingClientRect();
      const visible =
        r.width > 4 &&
        r.height > 4 &&
        r.left >= 0 &&
        r.top >= 0 &&
        r.right <= window.innerWidth &&
        r.bottom <= window.innerHeight;
      if (!visible) {
        setRing(null);
        return false;
      }
      const nextRing: RingRect = {
        top: r.top - SPOT_PAD,
        left: r.left - SPOT_PAD,
        width: r.width + 2 * SPOT_PAD,
        height: r.height + 2 * SPOT_PAD,
      };
      setRing((prev) =>
        prev &&
        prev.top === nextRing.top &&
        prev.left === nextRing.left &&
        prev.width === nextRing.width &&
        prev.height === nextRing.height
          ? prev
          : nextRing
      );
      return true;
    };

    let tries = 0;
    let interval: number | undefined;
    const kickoff = () => {
      if (measure()) return;
      // Target not on screen: prefer navigating to the step's page, then keep
      // polling briefly for the element to mount.
      if (stepDef.href && pathname !== stepDef.href && !navigatedSteps.current.has(step)) {
        navigatedSteps.current.add(step);
        router.push(stepDef.href);
      }
      interval = window.setInterval(() => {
        tries += 1;
        if (measure() || tries >= POLL_MAX) {
          window.clearInterval(interval);
          interval = undefined;
        }
      }, POLL_MS);
    };

    const t = window.setTimeout(kickoff, 60);
    const onMove = () => measure();
    window.addEventListener("resize", onMove);
    window.addEventListener("scroll", onMove, true);
    return () => {
      window.clearTimeout(t);
      if (interval) window.clearInterval(interval);
      window.removeEventListener("resize", onMove);
      window.removeEventListener("scroll", onMove, true);
    };
  }, [phase, step, pathname, router]);

  // Card anchoring: place the card next to the cutout (prefer the side with
  // room: right of sidebar items, below topbar items) and keep it fully
  // inside the viewport with 16px margins. Runs before paint so the card
  // never flashes at a stale position.
  const computePos = useCallback(() => {
    const el = posRef.current;
    if (!el) return;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const clamp = (v: number, lo: number, hi: number) => Math.min(Math.max(v, lo), Math.max(lo, hi));
    const measureH = (w: number) => {
      el.style.width = `${w}px`;
      return el.offsetHeight;
    };
    const centered = (): CardPos => {
      const w = Math.min(430, vw - 2 * VIEW_MARGIN);
      const h = measureH(w);
      return {
        top: Math.max(VIEW_MARGIN, (vh - h) / 2),
        left: Math.max(VIEW_MARGIN, (vw - w) / 2),
        width: w,
        arrow: null,
      };
    };

    if (isMobile) {
      const w = vw - 24;
      const h = measureH(w);
      setPos({ top: Math.max(12, vh - h - 12), left: 12, width: w, arrow: null });
      return;
    }
    if (!ring) {
      setPos(centered());
      return;
    }

    const w = Math.min(360, vw - 2 * VIEW_MARGIN);
    const h = measureH(w);
    const cx = ring.left + ring.width / 2;
    const cy = ring.top + ring.height / 2;

    let top: number;
    let left: number;
    let side: ArrowSide;
    if (ring.left + ring.width + CARD_GAP + w <= vw - VIEW_MARGIN) {
      // card to the right of the target, arrow on the card's left edge
      side = "left";
      left = ring.left + ring.width + CARD_GAP;
      top = clamp(cy - h / 2, VIEW_MARGIN, vh - h - VIEW_MARGIN);
    } else if (ring.top + ring.height + CARD_GAP + h <= vh - VIEW_MARGIN) {
      // card below the target, arrow on top
      side = "top";
      top = ring.top + ring.height + CARD_GAP;
      left = clamp(cx - w / 2, VIEW_MARGIN, vw - w - VIEW_MARGIN);
    } else if (ring.left - CARD_GAP - w >= VIEW_MARGIN) {
      // card to the left of the target, arrow on the right edge
      side = "right";
      left = ring.left - CARD_GAP - w;
      top = clamp(cy - h / 2, VIEW_MARGIN, vh - h - VIEW_MARGIN);
    } else if (ring.top - CARD_GAP - h >= VIEW_MARGIN) {
      // card above the target, arrow on the bottom
      side = "bottom";
      top = ring.top - CARD_GAP - h;
      left = clamp(cx - w / 2, VIEW_MARGIN, vw - w - VIEW_MARGIN);
    } else {
      setPos(centered());
      return;
    }
    const offset =
      side === "left" || side === "right"
        ? clamp(cy - top, 18, h - 18)
        : clamp(cx - left, 18, w - 18);
    setPos({ top, left, width: w, arrow: { side, offset } });
  }, [ring, isMobile]);

  useLayoutEffect(() => {
    if (phase === "closed") return;
    computePos();
    window.addEventListener("resize", computePos);
    return () => window.removeEventListener("resize", computePos);
    // step is a dependency because the card's content (and therefore its
    // height) changes per step even when the ring does not.
  }, [computePos, phase, step]);

  useEffect(() => {
    if (phase === "open") cardRef.current?.focus();
  }, [phase]);

  if (phase === "closed") return null;

  const s = STEPS[step];
  const last = step === STEPS.length - 1;
  const Icon = s.icon;

  // The spotlight is a rounded rect whose giant box-shadow paints the dim
  // layer, so the cutout itself is a real transparent hole: the highlighted
  // feature stays fully sharp and undimmed. With no visible target the hole
  // collapses to a point at the viewport center, which reads as a full dim.
  const spot: RingRect = ring ?? {
    top: typeof window !== "undefined" ? window.innerHeight / 2 : 0,
    left: typeof window !== "undefined" ? window.innerWidth / 2 : 0,
    width: 0,
    height: 0,
  };

  return (
    <div
      className={"pai-tour" + (phase === "closing" ? " pai-tour-closing" : "")}
      role="dialog"
      aria-modal="true"
      aria-label="PolicyAI product tour"
    >
      {/* invisible click catcher: click anywhere outside the card to skip */}
      <div className="fixed inset-0 z-[90]" onClick={() => close(false)} aria-hidden />

      {/* spotlight cutout: dims everything except the target */}
      <div
        className="pai-tour-spot"
        style={{ top: spot.top, left: spot.left, width: spot.width, height: spot.height }}
        aria-hidden
      />

      {/* pulsing ring accent around the cutout */}
      {ring && (
        <div
          className="pai-tour-ring"
          style={{ top: ring.top, left: ring.left, width: ring.width, height: ring.height }}
          aria-hidden
        />
      )}

      {/* card: anchored next to the target, centered without one, docked on mobile */}
      <div
        ref={posRef}
        className="pai-tour-pos fixed z-[100]"
        style={{
          top: pos?.top,
          left: pos?.left,
          width: pos?.width,
          visibility: pos ? "visible" : "hidden",
        }}
      >
        {pos?.arrow && <span className="pai-tour-arrow" style={arrowStyle(pos.arrow)} aria-hidden />}
        <div
          ref={cardRef}
          tabIndex={-1}
          className="pai-tour-card relative z-[1] overflow-hidden rounded-2xl border border-[var(--border)] bg-white shadow-[0_20px_60px_rgba(17,18,27,.35)] outline-none"
        >
          {/* slim brand strip instead of a tall header, so the card never
              covers the feature it is describing */}
          <div className="brand-grad h-1" aria-hidden />

          <div key={`body-${s.key}`} className="pai-tour-body px-5 pb-4 pt-4">
            <div className="flex items-start gap-3">
              <div className="brand-grad flex h-10 w-10 flex-none items-center justify-center rounded-xl shadow-[0_6px_16px_rgba(67,56,184,.35)]">
                <Icon size={19} className="text-white" />
              </div>
              <div className="min-w-0 flex-1 pt-0.5">
                <div className="text-[10.5px] font-bold uppercase tracking-[.09em] text-[var(--muted-2)]">
                  {last ? "Tour complete" : `Step ${step + 1} of ${STEPS.length}`}
                </div>
                <h2 className="serif mt-0.5 text-[18px] font-medium leading-snug tracking-[-.01em] text-[var(--text)]">
                  {s.title}
                </h2>
              </div>
              <button
                onClick={() => close(false)}
                className="-mr-1.5 -mt-1 flex flex-none items-center gap-1 rounded-full px-2 py-1 text-[11px] font-semibold text-[var(--muted-2)] transition-colors hover:bg-[#f2f2ef] hover:text-[var(--text-2)]"
              >
                Skip tour
                <X size={11} />
              </button>
            </div>

            <p className="mt-2.5 text-[13px] leading-relaxed text-[var(--muted)]">{s.desc}</p>

            {s.href && (
              <button
                onClick={() => router.push(s.href!)}
                className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-[#E4E0F7] bg-[#F8F7FE] px-3 py-1.5 text-[12.5px] font-bold text-[var(--brand-ink)] transition-colors hover:bg-[#F1EEFC]"
              >
                {s.hrefLabel ?? "Go there"}
                <ArrowUpRight size={13} />
              </button>
            )}
          </div>

          {/* footer: progress dots + navigation */}
          <div className="flex items-center justify-between gap-3 border-t border-[var(--border-soft)] px-5 py-3">
            <div className="flex items-center gap-1.5">
              {STEPS.map((st, i) => (
                <button
                  key={st.key}
                  onClick={() => setStep(i)}
                  aria-label={`Go to step ${i + 1}`}
                  className={
                    "h-1.5 rounded-full transition-all duration-300 " +
                    (i === step
                      ? "w-5 bg-[var(--brand)]"
                      : i < step
                        ? "w-1.5 bg-[#B7B1DF] hover:bg-[#C6C2E0]"
                        : "w-1.5 bg-[#DDDBEA] hover:bg-[#C6C2E0]")
                  }
                />
              ))}
            </div>
            <div className="flex flex-none items-center gap-2">
              {step > 0 && (
                <button
                  onClick={back}
                  className="rounded-[10px] border border-[var(--border)] px-3 py-2 text-[12.5px] font-semibold text-[var(--muted)] transition-colors hover:bg-[#f2f2ef] hover:text-[var(--text-2)]"
                >
                  Back
                </button>
              )}
              <button
                onClick={last ? () => close(true) : next}
                className="brand-grad inline-flex items-center gap-1.5 rounded-[10px] px-3.5 py-2 text-[12.5px] font-bold text-white shadow-[0_2px_8px_rgba(67,56,184,.32)]"
              >
                {last ? "Get started" : "Next"}
                {!last && <ArrowRight size={14} />}
              </button>
            </div>
          </div>
        </div>
      </div>

      <style jsx global>{`
        .pai-tour-spot {
          position: fixed;
          z-index: 91;
          pointer-events: none;
          border-radius: 14px;
          box-shadow: 0 0 0 200vmax rgba(16, 17, 26, 0.55);
          transition:
            top 0.3s cubic-bezier(0.22, 0.9, 0.26, 1),
            left 0.3s cubic-bezier(0.22, 0.9, 0.26, 1),
            width 0.3s cubic-bezier(0.22, 0.9, 0.26, 1),
            height 0.3s cubic-bezier(0.22, 0.9, 0.26, 1);
          animation: paiTourFade 0.28s ease both;
        }
        .pai-tour-ring {
          position: fixed;
          z-index: 92;
          pointer-events: none;
          border-radius: 14px;
          border: 2px solid rgba(255, 255, 255, 0.9);
          transition:
            top 0.3s cubic-bezier(0.22, 0.9, 0.26, 1),
            left 0.3s cubic-bezier(0.22, 0.9, 0.26, 1),
            width 0.3s cubic-bezier(0.22, 0.9, 0.26, 1),
            height 0.3s cubic-bezier(0.22, 0.9, 0.26, 1);
          animation: paiTourPulse 1.8s ease-in-out infinite;
        }
        .pai-tour-pos {
          transition:
            top 0.3s cubic-bezier(0.22, 0.9, 0.26, 1),
            left 0.3s cubic-bezier(0.22, 0.9, 0.26, 1),
            width 0.3s cubic-bezier(0.22, 0.9, 0.26, 1);
        }
        .pai-tour-arrow {
          position: absolute;
          z-index: 0;
          width: 12px;
          height: 12px;
          background: #fff;
          border: 1px solid var(--border);
          transform: rotate(45deg);
        }
        .pai-tour-card {
          animation: paiTourPop 0.34s cubic-bezier(0.2, 0.9, 0.3, 1.15) both;
        }
        .pai-tour-body {
          animation: paiTourStep 0.3s ease both;
        }
        .pai-tour-closing .pai-tour-spot,
        .pai-tour-closing .pai-tour-ring {
          animation: paiTourFadeOut 0.22s ease both;
        }
        .pai-tour-closing .pai-tour-card {
          animation: paiTourPopOut 0.22s ease both;
        }
        @keyframes paiTourFade {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes paiTourFadeOut {
          from { opacity: 1; }
          to { opacity: 0; }
        }
        @keyframes paiTourPop {
          from { opacity: 0; transform: translateY(12px) scale(0.96); }
          to { opacity: 1; transform: none; }
        }
        @keyframes paiTourPopOut {
          from { opacity: 1; transform: none; }
          to { opacity: 0; transform: translateY(10px) scale(0.97); }
        }
        @keyframes paiTourStep {
          from { opacity: 0; transform: translateY(6px); }
          to { opacity: 1; transform: none; }
        }
        @keyframes paiTourPulse {
          0%, 100% { box-shadow: 0 0 0 5px rgba(91, 79, 214, 0.4), 0 0 30px 6px rgba(91, 79, 214, 0.45); }
          50% { box-shadow: 0 0 0 9px rgba(91, 79, 214, 0.18), 0 0 38px 10px rgba(91, 79, 214, 0.3); }
        }
        @media (prefers-reduced-motion: reduce) {
          .pai-tour-spot,
          .pai-tour-ring,
          .pai-tour-pos,
          .pai-tour-arrow,
          .pai-tour-card,
          .pai-tour-body {
            animation: none !important;
            transition: none !important;
          }
        }
      `}</style>
    </div>
  );
}
