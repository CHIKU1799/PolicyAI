/**
 * Static, faithful recreation of the PolicyAI dashboard inside a browser-chrome
 * frame, for the marketing landing page. Pure markup: no client hooks, so it
 * renders on the server. Entrance/idle animations are CSS-only and respect
 * prefers-reduced-motion via the global .anim-* utilities.
 */

/** Deterministic PRNG (mulberry32), identical to the design mockup. */
function rng(seed: number) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Seeded sparkline path used by KPI cards and control rows. */
export function sparkPath(seed: number, up: boolean): string {
  const r = rng(seed);
  let p = "M0 " + (up ? 20 : 8);
  for (let i = 1; i <= 11; i++) {
    p +=
      " L" +
      i * 11 +
      " " +
      Math.max(3, Math.min(23, (up ? 20 - i * 1.4 : 8 + i * 0.7) + (r() - 0.5) * 7)).toFixed(1);
  }
  return p;
}

const SIDEBAR: { label: string; count: string }[] = [
  { label: "Dashboard", count: "24" },
  { label: "Horizon scan", count: "9" },
  { label: "Obligations", count: "142" },
  { label: "Gap analysis", count: "12" },
  { label: "Controls", count: "68" },
  { label: "Policies", count: "31" },
  { label: "Tasks", count: "17" },
  { label: "Knowledge graph", count: "" },
  { label: "Ask PolicyAI", count: "" },
];

const KPIS = [
  { label: "Open obligations", value: "142", delta: "+8", deltaColor: "#C0392B", path: sparkPath(11, false), stroke: "#4B40C4" },
  { label: "Controls passing", value: "91%", delta: "+3", deltaColor: "#1F9D5B", path: sparkPath(22, true), stroke: "#1F9D5B" },
  { label: "Gaps closed (30d)", value: "37", delta: "+12", deltaColor: "#1F9D5B", path: sparkPath(33, true), stroke: "#1F9D5B" },
  { label: "Overdue tasks", value: "4", delta: "-2", deltaColor: "#1F9D5B", path: sparkPath(44, false), stroke: "#E0683C" },
];

const OBLIGATIONS = [
  { id: "OBL-1044", text: "Offer key-fact statement before disbursal", status: "No owner", chipBg: "#FDECEC", chipFg: "#C0392B", due: "02 Aug" },
  { id: "OBL-1045", text: "No fees levied on active repayment plans", status: "In review", chipBg: "#FFF3E6", chipFg: "#B4661F", due: "09 Aug" },
  { id: "OBL-1046", text: "Evidence borrower-consent rationale", status: "Mapped", chipBg: "#E8F6EE", chipFg: "#1F7A49", due: "15 Aug" },
  { id: "OBL-1047", text: "Report concentration risk to the board", status: "No owner", chipBg: "#FDECEC", chipFg: "#C0392B", due: "21 Aug" },
  { id: "OBL-1051", text: "Publish grievance escalation matrix", status: "Mapped", chipBg: "#E8F6EE", chipFg: "#1F7A49", due: "30 Aug" },
];

const COVERAGE = [
  { label: "Audit trail for forbearance", pct: 28, color: "#C0392B" },
  { label: "Board concentration reporting", pct: 76, color: "#E0683C" },
  { label: "Fairness testing: credit", pct: 45, color: "#E0683C" },
  { label: "Enhanced CDD triggers", pct: 85, color: "#1F9D5B" },
];

export default function DashboardMock() {
  return (
    <section className="anim-rise relative" style={{ animationDelay: "0.12s" }}>
      {/* soft indigo glow under the frame */}
      <div
        aria-hidden
        className="absolute"
        style={{
          inset: "auto 8% -34px 8%",
          height: 120,
          background: "radial-gradient(60% 100% at 50% 0%, rgba(75,64,196,.16), transparent 70%)",
          filter: "blur(14px)",
        }}
      />
      {/* browser-chrome frame */}
      <div
        className="relative overflow-hidden rounded-[22px] border bg-white"
        style={{ borderColor: "#EAE9E5", boxShadow: "0 30px 70px -30px rgba(17,18,27,.35)" }}
      >
        <div
          className="flex items-center gap-3 border-b px-[18px] py-3.5"
          style={{ borderColor: "#F0F0EC", background: "#FCFCFB" }}
        >
          <div className="flex gap-[7px]" aria-hidden>
            <span className="h-[11px] w-[11px] rounded-full" style={{ background: "#E5E4E0" }} />
            <span className="h-[11px] w-[11px] rounded-full" style={{ background: "#E5E4E0" }} />
            <span className="h-[11px] w-[11px] rounded-full" style={{ background: "#E5E4E0" }} />
          </div>
          <div className="mono flex-1 text-center text-[12px]" style={{ color: "#9A9DA4" }}>
            app.policyai.com/dashboard
          </div>
        </div>
        <div className="grid md:grid-cols-[196px_1fr]">
          {/* sidebar */}
          <aside
            className="hidden flex-col gap-[3px] border-r px-3 py-4 md:flex"
            style={{ borderColor: "#F0F0EC", background: "#FCFCFB" }}
          >
            <div className="flex items-center gap-[9px] px-2 pb-3.5 pt-1.5">
              <span className="brand-grad h-[22px] w-[22px] rounded-[7px]" aria-hidden />
              <span className="text-[14px] font-bold tracking-tight">PolicyAI</span>
            </div>
            {SIDEBAR.map((item, i) => (
              <div
                key={item.label}
                className="flex items-center gap-[9px] rounded-[10px] px-[9px] py-[7px] text-[12.5px] font-semibold"
                style={{
                  color: i === 0 ? "#4B40C4" : "#5B5E66",
                  background: i === 0 ? "rgba(75,64,196,0.09)" : "transparent",
                }}
              >
                <span
                  className="h-1.5 w-1.5 rounded-[2px]"
                  style={{ background: i === 0 ? "#4B40C4" : "#D3D3CD" }}
                  aria-hidden
                />
                {item.label}
                <span className="mono ml-auto text-[10px]" style={{ color: "#B6B9BF" }}>
                  {item.count}
                </span>
              </div>
            ))}
          </aside>
          {/* main pane */}
          <div className="flex flex-col gap-4 bg-white p-4 sm:p-5">
            {/* KPI cards */}
            <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
              {KPIS.map((k) => (
                <div
                  key={k.label}
                  className="flex flex-col gap-2 rounded-[14px] border px-3.5 py-[13px]"
                  style={{ borderColor: "#EAE9E5" }}
                >
                  <div className="text-[11px] font-semibold" style={{ color: "#71757E" }}>
                    {k.label}
                  </div>
                  <div className="flex items-baseline gap-[7px]">
                    <span className="text-[25px] font-bold tracking-tight">{k.value}</span>
                    <span className="text-[11px] font-semibold" style={{ color: k.deltaColor }}>
                      {k.delta}
                    </span>
                  </div>
                  <svg viewBox="0 0 120 26" preserveAspectRatio="none" className="h-[26px] w-full" aria-hidden>
                    <path
                      d={k.path}
                      fill="none"
                      stroke={k.stroke}
                      strokeWidth="1.6"
                      strokeLinecap="round"
                      className="anim-dash"
                    />
                  </svg>
                </div>
              ))}
            </div>
            <div className="grid gap-3.5 lg:grid-cols-[1.45fr_1fr]">
              {/* obligations table */}
              <div className="overflow-hidden rounded-[14px] border" style={{ borderColor: "#EAE9E5" }}>
                <div
                  className="flex items-center gap-2 border-b px-3.5 py-[11px]"
                  style={{ borderColor: "#F4F4F1" }}
                >
                  <span className="text-[12.5px] font-bold">Obligations needing action</span>
                  <span
                    className="mono rounded-[5px] px-1.5 py-0.5 text-[10px]"
                    style={{ color: "#71757E", background: "#F5F4F2" }}
                  >
                    12 open
                  </span>
                  <span
                    className="anim-pulse-soft ml-auto text-[10.5px] font-semibold"
                    style={{ color: "#1F9D5B" }}
                  >
                    ● Live sync
                  </span>
                </div>
                {OBLIGATIONS.map((o) => (
                  <div
                    key={o.id}
                    className="grid grid-cols-[74px_1fr_auto] items-center gap-2.5 border-b px-3.5 py-[9px] sm:grid-cols-[74px_1fr_auto_auto]"
                    style={{ borderColor: "#F7F7F4" }}
                  >
                    <span className="mono text-[10px] font-semibold" style={{ color: "#4B40C4" }}>
                      {o.id}
                    </span>
                    <span
                      className="overflow-hidden text-ellipsis whitespace-nowrap text-[12px]"
                      style={{ color: "#3A3D44" }}
                    >
                      {o.text}
                    </span>
                    <span
                      className="rounded-md px-[7px] py-0.5 text-[10px] font-bold"
                      style={{ background: o.chipBg, color: o.chipFg }}
                    >
                      {o.status}
                    </span>
                    <span className="mono hidden text-[10px] sm:block" style={{ color: "#9A9DA4" }}>
                      {o.due}
                    </span>
                  </div>
                ))}
              </div>
              {/* coverage + copilot */}
              <div className="flex flex-col gap-3.5">
                <div className="rounded-[14px] border p-3.5" style={{ borderColor: "#EAE9E5" }}>
                  <div className="mb-[11px] text-[12.5px] font-bold">Control coverage</div>
                  {COVERAGE.map((c, i) => (
                    <div key={c.label} className="mb-[9px]">
                      <div
                        className="mb-1 flex justify-between text-[10.5px]"
                        style={{ color: "#54565E" }}
                      >
                        <span>{c.label}</span>
                        <span>{c.pct}%</span>
                      </div>
                      <div
                        className="h-1.5 overflow-hidden rounded-full"
                        style={{ background: "#F0F0EC" }}
                      >
                        <div
                          className="anim-grow h-full rounded-full"
                          style={{
                            width: `${c.pct}%`,
                            background: c.color,
                            animationDelay: `${0.15 + i * 0.1}s`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
                <div
                  className="rounded-[14px] border p-3.5"
                  style={{ borderColor: "#EAE9E5", background: "linear-gradient(180deg,#FBFAFF,#fff)" }}
                >
                  <div className="mb-[9px] flex items-center gap-2">
                    <span
                      className="grid h-5 w-5 place-items-center rounded-[7px] text-[11px] text-white"
                      style={{ background: "#4B40C4" }}
                      aria-hidden
                    >
                      ✦
                    </span>
                    <span className="text-[12.5px] font-bold" style={{ color: "#4B40C4" }}>
                      Copilot
                    </span>
                  </div>
                  <div className="text-[12px] leading-relaxed" style={{ color: "#3A3D44" }}>
                    2 obligations from the RBI Digital Lending Directions still need a control owner.
                  </div>
                  <div className="mt-2.5 flex gap-1.5">
                    {["OBL-1044", "OBL-1047"].map((id) => (
                      <span
                        key={id}
                        className="mono rounded-md px-[7px] py-[3px] text-[10px]"
                        style={{ background: "#FDECEC", color: "#C0392B" }}
                      >
                        {id}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      {/* floating alert toast */}
      <div
        className="anim-float absolute hidden w-[252px] rounded-2xl border bg-white px-[17px] py-[15px] xl:block"
        style={{
          left: -26,
          top: 210,
          borderColor: "#EAE9E5",
          boxShadow: "0 22px 44px -20px rgba(17,18,27,.4)",
        }}
      >
        <div className="mb-2 flex items-center gap-2">
          <span className="mono text-[11px] font-bold" style={{ color: "#1E5EF6" }}>
            RBI
          </span>
          <span
            className="rounded-md px-[7px] py-0.5 text-[10.5px] font-bold"
            style={{ background: "#FDECEC", color: "#C0392B" }}
          >
            High impact
          </span>
          <span
            className="anim-pulse-soft ml-auto h-[7px] w-[7px] rounded-full"
            style={{ background: "#1F9D5B" }}
            aria-hidden
          />
        </div>
        <div className="text-[14px] font-bold leading-snug">New forbearance obligations detected</div>
        <div className="mt-[5px] text-[12px] leading-normal" style={{ color: "#71757E" }}>
          AI mapped 4 obligations to your Microfinance line · 41 min ago
        </div>
      </div>
    </section>
  );
}
