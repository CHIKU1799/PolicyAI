"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
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
    key: "graph",
    title: "Explore how everything connects",
    desc: "The Regulation Graph links circulars, topics, entities and deadlines, so you can trace any requirement back to its source in a couple of hops.",
    icon: Share2,
    href: "/graph",
    target: "nav-graph",
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

export default function OnboardingTour() {
  const router = useRouter();
  const pathname = usePathname();
  const [phase, setPhase] = useState<"closed" | "open" | "closing">("closed");
  const [step, setStep] = useState(0);
  const [ring, setRing] = useState<RingRect | null>(null);
  const storageKey = useRef(`${STORAGE_PREFIX}:anon`);
  const cardRef = useRef<HTMLDivElement>(null);

  const open = useCallback(() => {
    setStep(0);
    setRing(null);
    setPhase("open");
  }, []);

  const close = useCallback((completed: boolean) => {
    try {
      window.localStorage.setItem(storageKey.current, completed ? "done" : "skipped");
    } catch {
      // storage unavailable: the tour will simply offer itself again next visit
    }
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
      try {
        const supabase = getSupabase();
        if (supabase) {
          const { data } = await supabase.auth.getUser();
          if (data.user?.id) id = data.user.id;
        }
      } catch {
        // fall back to the generic key
      }
      if (cancelled) return;
      storageKey.current = `${STORAGE_PREFIX}:${id}`;
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

  // Spotlight: locate the step target (data-tour attributes on the chrome)
  // and keep the ring in sync with layout changes.
  useEffect(() => {
    if (phase === "closed") return;
    const target = STEPS[step].target;
    const measure = () => {
      if (!target) return setRing(null);
      const el = document.querySelector(`[data-tour="${target}"]`);
      if (!el) return setRing(null);
      const r = el.getBoundingClientRect();
      const visible =
        r.width > 4 &&
        r.height > 4 &&
        r.left >= 0 &&
        r.top >= 0 &&
        r.right <= window.innerWidth &&
        r.bottom <= window.innerHeight;
      if (!visible) return setRing(null);
      setRing({ top: r.top - 6, left: r.left - 6, width: r.width + 12, height: r.height + 12 });
    };
    const t = window.setTimeout(measure, 80);
    window.addEventListener("resize", measure);
    return () => {
      window.clearTimeout(t);
      window.removeEventListener("resize", measure);
    };
  }, [phase, step, pathname]);

  useEffect(() => {
    if (phase === "open") cardRef.current?.focus();
  }, [phase]);

  if (phase === "closed") return null;

  const s = STEPS[step];
  const last = step === STEPS.length - 1;
  const Icon = s.icon;

  return (
    <div
      className={"pai-tour" + (phase === "closing" ? " pai-tour-closing" : "")}
      role="dialog"
      aria-modal="true"
      aria-label="PolicyAI product tour"
    >
      <div className="pai-tour-overlay fixed inset-0 z-[90]" onClick={() => close(false)} aria-hidden />

      {ring && (
        <div
          className="pai-tour-ring"
          style={{ top: ring.top, left: ring.left, width: ring.width, height: ring.height }}
          aria-hidden
        />
      )}

      <div className="fixed inset-x-3 bottom-3 z-[100] sm:inset-x-auto sm:bottom-auto sm:left-1/2 sm:top-1/2 sm:w-[430px] sm:-translate-x-1/2 sm:-translate-y-1/2">
        <div
          ref={cardRef}
          tabIndex={-1}
          className="pai-tour-card overflow-hidden rounded-2xl border border-[var(--border)] bg-white shadow-[0_24px_70px_rgba(17,18,27,.38)] outline-none"
        >
          {/* header: animated icon scene on the brand gradient */}
          <div className="brand-grad relative">
            <button
              onClick={() => close(false)}
              className="absolute right-3 top-3 z-10 flex items-center gap-1 rounded-full bg-white/15 px-2.5 py-1 text-[11.5px] font-semibold text-white/90 transition-colors hover:bg-white/25"
            >
              Skip tour
              <X size={12} />
            </button>
            <div key={s.key} className="pai-tour-scene relative flex h-[116px] items-center justify-center overflow-hidden">
              <span className="pai-tour-halo" aria-hidden />
              <span className="pai-tour-halo pai-tour-halo-2" aria-hidden />
              <div className="pai-tour-tile flex h-14 w-14 items-center justify-center rounded-2xl border border-white/25 bg-white/15 shadow-[0_10px_28px_rgba(0,0,0,.22)]">
                <Icon size={26} className="text-white" />
              </div>
              <Sparkles size={13} className="pai-tour-orb pai-tour-orb-a text-white/70" aria-hidden />
              <CheckCircle2 size={13} className="pai-tour-orb pai-tour-orb-b text-white/60" aria-hidden />
            </div>
          </div>

          {/* body */}
          <div key={`body-${s.key}`} className="pai-tour-body px-5 pb-3.5 pt-4">
            <div className="text-[10.5px] font-bold uppercase tracking-[.09em] text-[var(--muted-2)]">
              {last ? "Tour complete" : `Step ${step + 1} of ${STEPS.length}`}
            </div>
            <h2 className="serif mt-1 text-[20px] font-medium leading-snug tracking-[-.01em] text-[var(--text)]">
              {s.title}
            </h2>
            <p className="mt-1.5 text-[13.5px] leading-relaxed text-[var(--muted)]">{s.desc}</p>
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
          <div className="flex items-center justify-between gap-3 border-t border-[var(--border-soft)] px-5 py-3.5">
            <div className="flex items-center gap-1.5">
              {STEPS.map((st, i) => (
                <button
                  key={st.key}
                  onClick={() => setStep(i)}
                  aria-label={`Go to step ${i + 1}`}
                  className={
                    "h-1.5 rounded-full transition-all " +
                    (i === step ? "w-5 bg-[var(--brand)]" : "w-1.5 bg-[#DDDBEA] hover:bg-[#C6C2E0]")
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
        .pai-tour-overlay {
          background: rgba(16, 17, 26, 0.44);
          backdrop-filter: blur(3px);
          -webkit-backdrop-filter: blur(3px);
          animation: paiTourFade 0.28s ease both;
        }
        .pai-tour-card {
          animation: paiTourPop 0.32s cubic-bezier(0.2, 0.9, 0.3, 1.15) both;
        }
        .pai-tour-closing .pai-tour-overlay {
          animation: paiTourFadeOut 0.22s ease both;
        }
        .pai-tour-closing .pai-tour-card {
          animation: paiTourPopOut 0.22s ease both;
        }
        .pai-tour-closing .pai-tour-ring {
          animation: paiTourFadeOut 0.22s ease both;
        }
        .pai-tour-body,
        .pai-tour-scene {
          animation: paiTourStep 0.3s ease both;
        }
        .pai-tour-ring {
          position: fixed;
          z-index: 95;
          pointer-events: none;
          border-radius: 14px;
          border: 2px solid rgba(255, 255, 255, 0.9);
          background: radial-gradient(closest-side, rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0));
          transition: top 0.3s ease, left 0.3s ease, width 0.3s ease, height 0.3s ease;
          animation: paiTourPulse 1.8s ease-in-out infinite;
        }
        .pai-tour-tile {
          animation: paiTourFloat 3.2s ease-in-out infinite;
        }
        .pai-tour-halo {
          position: absolute;
          width: 84px;
          height: 84px;
          border-radius: 9999px;
          border: 1.5px solid rgba(255, 255, 255, 0.35);
          animation: paiTourHalo 2.6s ease-out infinite;
        }
        .pai-tour-halo-2 {
          animation-delay: 1.3s;
        }
        .pai-tour-orb {
          position: absolute;
          animation: paiTourFloat 2.6s ease-in-out infinite;
        }
        .pai-tour-orb-a {
          left: 27%;
          top: 27%;
          animation-delay: 0.3s;
        }
        .pai-tour-orb-b {
          right: 26%;
          bottom: 24%;
          animation-delay: 1.1s;
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
          from { opacity: 0; transform: translateY(14px) scale(0.96); }
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
        @keyframes paiTourFloat {
          0%, 100% { transform: translateY(2px); }
          50% { transform: translateY(-4px); }
        }
        @keyframes paiTourHalo {
          from { transform: scale(0.7); opacity: 0.9; }
          to { transform: scale(1.9); opacity: 0; }
        }
        @keyframes paiTourPulse {
          0%, 100% { box-shadow: 0 0 0 5px rgba(91, 79, 214, 0.4), 0 0 30px 6px rgba(91, 79, 214, 0.45); }
          50% { box-shadow: 0 0 0 9px rgba(91, 79, 214, 0.18), 0 0 38px 10px rgba(91, 79, 214, 0.3); }
        }
        @media (prefers-reduced-motion: reduce) {
          .pai-tour-overlay,
          .pai-tour-card,
          .pai-tour-body,
          .pai-tour-scene,
          .pai-tour-tile,
          .pai-tour-halo,
          .pai-tour-orb,
          .pai-tour-ring {
            animation: none !important;
            transition: none !important;
          }
        }
      `}</style>
    </div>
  );
}
