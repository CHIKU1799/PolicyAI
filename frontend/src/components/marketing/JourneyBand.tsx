/**
 * Landing-page band: "a Tuesday with PolicyAI". Replaces the abstract knowledge
 * graph with the story a compliance head actually buys — one real circular
 * flowing publication → alert → obligation → owner → tested proof, in a day.
 * Pure CSS motion (traveling pulse + sequential card glow); respects
 * prefers-reduced-motion.
 */

const STAGES = [
  {
    time: "09:04",
    label: "RBI PUBLISHES",
    title: "Review of pricing of credit — NBFC-MFIs",
    detail: "Picked up seconds after it lands on rbi.org.in",
    chip: { text: "RBI", bg: "rgba(255,255,255,.14)", color: "#C7C4E8" },
  },
  {
    time: "09:06",
    label: "ALERT — APPLIES TO YOU",
    title: "Matched to your profile: NBFC-MFI",
    detail: "Severity scored against your business, not generically",
    chip: { text: "HIGH", bg: "rgba(224,104,60,.22)", color: "#FFB08A" },
  },
  {
    time: "09:12",
    label: "OBLIGATION DRAFTED",
    title: "Align loan pricing to the revised cap",
    detail: "With citation, penalty and evidence required",
    chip: { text: "DUE 90 DAYS", bg: "rgba(75,64,196,.35)", color: "#B9B2F1" },
  },
  {
    time: "11:30",
    label: "GAP OPENED · OWNER SET",
    title: "Fair Practices Code §4 is outdated",
    detail: "Assigned to Head of Credit with remediation steps",
    chip: { text: "HEAD OF CREDIT", bg: "rgba(255,255,255,.14)", color: "#C7C4E8" },
  },
  {
    time: "FRI",
    label: "CONTROL TESTED",
    title: "Spread-cap check passed, evidence attached",
    detail: "Audit-ready record, citable to the paragraph",
    chip: { text: "✓ AUDIT-READY", bg: "rgba(52,211,153,.18)", color: "#34D399" },
  },
];

const STATS = [
  { value: "2 min", label: "publication → alert" },
  { value: "2,500+", label: "regulations tracked live" },
  { value: "4", label: "regulators watched 24/7" },
  { value: "100%", label: "answers cited to source" },
];

export default function JourneyBand() {
  return (
    <div
      className="relative overflow-hidden rounded-[22px] p-6 md:p-9"
      style={{ background: "linear-gradient(135deg,#23204A 0%,#15132E 100%)" }}
    >
      {/* ambient glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full"
        style={{ background: "radial-gradient(circle,rgba(91,79,214,.4),transparent 70%)" }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-32 -left-16 h-72 w-72 rounded-full"
        style={{ background: "radial-gradient(circle,rgba(52,211,153,.14),transparent 70%)" }}
      />

      {/* traveling pulse along the connector (desktop) */}
      <div aria-hidden className="jb-track relative z-10 mb-4 hidden lg:block">
        <div className="jb-dot" />
      </div>

      <div className="relative z-10 grid gap-3 lg:grid-cols-5">
        {STAGES.map((s, i) => (
          <div
            key={s.label}
            className="jb-card flex flex-col gap-2 rounded-[16px] border p-4"
            style={{
              borderColor: "rgba(255,255,255,.10)",
              background: "rgba(255,255,255,.045)",
              animationDelay: `${i * 2}s`,
            }}
          >
            <div className="flex items-center justify-between">
              <span className="mono text-[11px] font-bold tracking-[.08em]" style={{ color: "#8F8ACD" }}>
                {s.time}
              </span>
              <span
                className="mono rounded-[6px] px-1.5 py-0.5 text-[9.5px] font-bold tracking-[.06em]"
                style={{ background: s.chip.bg, color: s.chip.color }}
              >
                {s.chip.text}
              </span>
            </div>
            <div className="mono text-[9.5px] font-bold tracking-[.14em]" style={{ color: "#6F6AAE" }}>
              {s.label}
            </div>
            <div className="text-[13.5px] font-semibold leading-snug text-white">{s.title}</div>
            <div className="text-pretty text-[12px] leading-relaxed" style={{ color: "#A8A4D6" }}>
              {s.detail}
            </div>
          </div>
        ))}
      </div>

      {/* payoff stats */}
      <div
        className="relative z-10 mt-6 grid grid-cols-2 gap-4 border-t pt-5 md:grid-cols-4"
        style={{ borderColor: "rgba(255,255,255,.10)" }}
      >
        {STATS.map((s) => (
          <div key={s.label}>
            <div className="text-[26px] font-extrabold tracking-[-.02em] text-white">{s.value}</div>
            <div className="mt-0.5 text-[11.5px]" style={{ color: "#9D99CC" }}>
              {s.label}
            </div>
          </div>
        ))}
      </div>

      <style>{`
        .jb-track {
          height: 2px;
          border-radius: 2px;
          background: linear-gradient(90deg, rgba(91,79,214,.5), rgba(52,211,153,.5));
          opacity: .55;
        }
        .jb-dot {
          position: absolute;
          top: -3px;
          left: 0;
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #fff;
          box-shadow: 0 0 12px 3px rgba(139,125,224,.9);
          animation: jbTravel 10s linear infinite;
        }
        @keyframes jbTravel {
          from { left: 0; }
          to { left: calc(100% - 8px); }
        }
        .jb-card { animation: jbGlow 10s ease-in-out infinite; }
        @keyframes jbGlow {
          0%, 24%, 100% { border-color: rgba(255,255,255,.10); background: rgba(255,255,255,.045); }
          8%, 14% { border-color: rgba(139,125,224,.55); background: rgba(91,79,214,.14); }
        }
        @media (prefers-reduced-motion: reduce) {
          .jb-dot, .jb-card { animation: none; }
        }
      `}</style>
    </div>
  );
}
