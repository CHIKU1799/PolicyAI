/** Small building blocks shared by the marketing pages, matching the landing template. */

export function Hero({ eyebrow, title, lede }: { eyebrow: string; title: React.ReactNode; lede: string }) {
  return (
    <section className="px-5 pb-10 pt-16 text-center">
      <div className="mx-auto max-w-3xl">
        <div
          className="mx-auto mb-4 inline-block rounded-full border bg-white px-3 py-1 text-[11px] font-semibold tracking-wide"
          style={{ borderColor: "#E2E1DC", color: "#1746D6" }}
        >
          {eyebrow}
        </div>
        <h1
          className="text-[44px] font-medium leading-[1.08] tracking-tight md:text-[54px]"
          style={{ fontFamily: "var(--font-serif), serif", color: "#15254E" }}
        >
          {title}
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-[15px] leading-relaxed" style={{ color: "#54565E" }}>
          {lede}
        </p>
      </div>
    </section>
  );
}

export function Section({
  id,
  step,
  title,
  body,
  bullets,
  flip,
  children,
}: {
  id?: string;
  step?: string;
  title: string;
  body: string;
  bullets?: string[];
  flip?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24 px-5 py-8">
      <div
        className={`mx-auto grid max-w-5xl items-center gap-8 rounded-2xl border bg-white p-8 md:grid-cols-2 ${
          flip ? "md:[&>*:first-child]:order-2" : ""
        }`}
        style={{ borderColor: "#EAE9E5", boxShadow: "0 8px 24px -14px rgba(35,32,74,.16)" }}
      >
        <div>
          {step && (
            <div className="mb-2 text-[11px] font-bold uppercase tracking-wider" style={{ color: "#1E5EF6" }}>
              {step}
            </div>
          )}
          <h2
            className="text-[26px] font-medium leading-snug"
            style={{ fontFamily: "var(--font-serif), serif", color: "#15254E" }}
          >
            {title}
          </h2>
          <p className="mt-2.5 text-[13.5px] leading-relaxed" style={{ color: "#54565E" }}>
            {body}
          </p>
          {bullets && (
            <ul className="mt-4 space-y-2">
              {bullets.map((b) => (
                <li key={b} className="flex items-start gap-2 text-[13px]" style={{ color: "#3A3D44" }}>
                  <span
                    className="mt-0.5 flex h-4 w-4 flex-none items-center justify-center rounded-full text-[9px] font-bold text-white"
                    style={{ background: "#1F9D5B" }}
                  >
                    ✓
                  </span>
                  {b}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="min-h-[180px] rounded-xl p-5" style={{ background: "#F5F4F2" }}>
          {children}
        </div>
      </div>
    </section>
  );
}

export function Cta({ title, body }: { title: string; body: string }) {
  return (
    <section className="px-5 py-14">
      <div
        className="mx-auto max-w-4xl rounded-3xl px-8 py-12 text-center"
        style={{ background: "linear-gradient(150deg,#23204A,#101A38)" }}
      >
        <h2
          className="text-[32px] font-medium text-white"
          style={{ fontFamily: "var(--font-serif), serif" }}
        >
          {title}
        </h2>
        <p className="mx-auto mt-2 max-w-md text-[13.5px] leading-relaxed" style={{ color: "#A8A4D6" }}>
          {body}
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <a
            href="/login"
            className="rounded-xl px-6 py-3 text-[14px] font-semibold text-white no-underline"
            style={{ background: "linear-gradient(135deg,#2E6BF7,#1746D6)" }}
          >
            Explore the platform →
          </a>
          <a
            href="/contact?intent=sales"
            className="rounded-xl border px-6 py-3 text-[14px] font-semibold no-underline"
            style={{ borderColor: "rgba(255,255,255,.25)", color: "#E4E2F4" }}
          >
            Talk to sales
          </a>
        </div>
      </div>
    </section>
  );
}

/** Mock mini-card, in the landing's mock visual style. */
export function MockCard({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="rounded-xl border bg-white p-3.5 text-[12px]"
      style={{ borderColor: "#EAE9E5", boxShadow: "0 8px 24px -10px rgba(35,32,74,.22)" }}
    >
      {children}
    </div>
  );
}

export function Chip({ children, tone = "blue" }: { children: React.ReactNode; tone?: "blue" | "red" | "green" | "amber" }) {
  const tones: Record<string, [string, string]> = {
    blue: ["#1746D6", "#E8F0FE"],
    red: ["#C0392B", "#FBEBEB"],
    green: ["#1F9D5B", "#E6F4EC"],
    amber: ["#A6691B", "#FBF1E1"],
  };
  const [color, bg] = tones[tone];
  return (
    <span className="rounded-md px-1.5 py-0.5 text-[10px] font-bold" style={{ color, background: bg }}>
      {children}
    </span>
  );
}
