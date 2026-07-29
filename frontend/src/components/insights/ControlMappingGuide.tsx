"use client";

// Collapsible "How control mapping works" guide for the Controls page.
// Collapsed by default; the open state persists in localStorage. The steps
// mirror the real data flow: controls -> obligation_controls links -> control
// tests -> effectiveness rollup (DB trigger raises control_failed alerts and
// the dashboard posture score reads effectiveness + coverage).

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  BookOpen,
  ChevronDown,
  ClipboardCheck,
  HelpCircle,
  Link2,
  ListPlus,
} from "lucide-react";

const STORAGE_KEY = "policyai_control_mapping_guide_open";

const STEPS = [
  {
    icon: ListPlus,
    title: "Create your controls",
    body: (
      <>
        Add each check or process your team actually runs: a ref code, whether it is
        preventive, detective or corrective, an owner, and a test frequency. One clean
        register means nothing you rely on is invisible to auditors.
      </>
    ),
  },
  {
    icon: Link2,
    title: "Link each control to the obligations it satisfies",
    body: (
      <>
        Open an obligation from the{" "}
        <Link href="/obligations" className="font-semibold text-[var(--brand)] underline decoration-dotted underline-offset-2">
          Obligations register
        </Link>{" "}
        and map the controls that address it. Every link raises your coverage score;
        an obligation with no linked control is flagged on the dashboard as exposure.
      </>
    ),
  },
  {
    icon: ClipboardCheck,
    title: "Test on schedule and record the result",
    body: (
      <>
        At each control&apos;s frequency, run the test and record pass, partial or fail
        with the evidence you checked. The evidence note is what turns a rating into a
        defensible audit trail.
      </>
    ),
  },
  {
    icon: Activity,
    title: "Results roll up automatically",
    body: (
      <>
        A failed test instantly marks the control ineffective and raises a
        control-failed alert, no manual step needed. Effectiveness then feeds the
        pass-rate trend on this page and your overall compliance posture score, so
        fixing a failing control visibly lifts your score.
      </>
    ),
  },
];

export default function ControlMappingGuide() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    try {
      setOpen(window.localStorage.getItem(STORAGE_KEY) === "1");
    } catch {
      // localStorage unavailable: stay collapsed
    }
  }, []);

  function toggle() {
    setOpen((cur) => {
      const next = !cur;
      try {
        window.localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
      } catch {
        // ignore persistence failures
      }
      return next;
    });
  }

  return (
    <div className="card mb-4 overflow-hidden">
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        className="flex w-full items-center gap-2.5 px-4 py-3 text-left"
      >
        <HelpCircle size={16} className="flex-none text-[var(--brand)]" />
        <span className="text-sm font-semibold text-slate-800">How control mapping works</span>
        <span className="ml-1 hidden text-[12px] text-[var(--muted)] sm:inline">
          4 steps from register to posture score
        </span>
        <ChevronDown
          size={16}
          className={`ml-auto flex-none text-[var(--muted)] transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="border-t border-[var(--border)] px-4 pb-4 pt-3">
          <ol className="grid gap-3 lg:grid-cols-2">
            {STEPS.map((s, i) => (
              <li key={s.title} className="flex gap-3 rounded-xl border border-[var(--border-soft)] bg-[#FBFBF9] p-3">
                <span className="flex h-7 w-7 flex-none items-center justify-center rounded-lg bg-[#F4F3FC] text-[var(--brand)]">
                  <s.icon size={15} />
                </span>
                <div className="min-w-0">
                  <div className="text-[13px] font-semibold text-slate-800">
                    {i + 1}. {s.title}
                  </div>
                  <p className="mt-0.5 text-[12.5px] leading-relaxed text-slate-600">{s.body}</p>
                </div>
              </li>
            ))}
          </ol>
          <div className="mt-3 flex items-start gap-2 rounded-xl bg-[#F8F7FE] px-3 py-2.5 text-[12px] leading-relaxed text-slate-600">
            <BookOpen size={14} className="mt-0.5 flex-none text-[var(--brand)]" />
            <span>
              Tip: your uploaded policies in the{" "}
              <Link href="/knowledge-base" className="font-semibold text-[var(--brand)] underline decoration-dotted underline-offset-2">
                Knowledge base
              </Link>{" "}
              decide which obligations apply to you. Keep them current so your control
              mappings always point at live obligations.
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
