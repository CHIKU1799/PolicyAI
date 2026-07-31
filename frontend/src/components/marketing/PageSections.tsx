/**
 * Section primitives shared by the marketing subpages (/platform, /solutions),
 * in the exact design language of the landing page: mono kickers, serif
 * display headings, #4B40C4 accent, rounded white cards on #F5F4F2 paper.
 * Server-safe: no client hooks.
 */

import Link from "next/link";

/* ---------------------------------- hero ---------------------------------- */

export function PageHero({
  kicker,
  title,
  lede,
}: {
  kicker: string;
  title: React.ReactNode;
  lede: string;
}) {
  return (
    <section className="anim-rise flex flex-col items-center gap-5 text-center md:gap-[22px]">
      <span className="mono text-[11px] font-semibold tracking-[.18em]" style={{ color: "#71757E" }}>
        {kicker}
      </span>
      <h1 className="serif m-0 max-w-[18ch] text-balance text-[38px] font-medium leading-[1.06] tracking-[-0.02em] sm:text-[48px] md:text-[56px] md:leading-[1.05]">
        {title}
      </h1>
      <p className="m-0 max-w-[58ch] text-pretty text-[16px] leading-relaxed md:text-[17px]" style={{ color: "#5B5E66" }}>
        {lede}
      </p>
    </section>
  );
}

/* ------------------------------ split section ------------------------------ */

export function SplitSection({
  id,
  kicker,
  title,
  body,
  bullets,
  flip,
  cta,
  anchors,
  children,
}: {
  id?: string;
  kicker: string;
  title: React.ReactNode;
  body: string;
  bullets?: string[];
  flip?: boolean;
  cta?: { label: string; href: string };
  /** Extra hash targets that should land on this section (no layout impact). */
  anchors?: string[];
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="relative grid scroll-mt-24 items-center gap-8 lg:grid-cols-2 lg:gap-[52px]">
      {anchors?.map((a) => (
        <span key={a} id={a} aria-hidden className="absolute top-0 h-0 w-0 scroll-mt-24" />
      ))}
      <div className={`min-w-0 ${flip ? "lg:order-2" : ""}`}>
        <span className="mono text-[11px] font-semibold tracking-[.14em]" style={{ color: "#4B40C4" }}>
          {kicker}
        </span>
        <h2 className="serif mb-0 mt-3 text-balance text-[28px] font-medium leading-[1.12] tracking-[-0.02em] md:text-[34px]">
          {title}
        </h2>
        <p className="mb-0 mt-3.5 text-pretty text-[15px] leading-[1.65]" style={{ color: "#5B5E66" }}>
          {body}
        </p>
        {bullets && (
          <div className="mt-4 flex flex-col gap-[7px]">
            {bullets.map((b) => (
              <div key={b} className="flex gap-[9px] text-[13.5px]" style={{ color: "#3A3D44" }}>
                <span className="font-bold" style={{ color: "#1F9D5B" }} aria-hidden>
                  ✓
                </span>
                {b}
              </div>
            ))}
          </div>
        )}
        {cta && (
          <div className="mt-5">
            <Link href={cta.href} className="text-[14px] font-semibold no-underline" style={{ color: "#4B40C4" }}>
              {cta.label} <span aria-hidden>→</span>
            </Link>
          </div>
        )}
      </div>
      <div className={`min-w-0 ${flip ? "lg:order-1" : ""}`}>{children}</div>
    </section>
  );
}

/* ------------------------------ vignette card ------------------------------ */

export type ChipTone = "red" | "amber" | "green" | "indigo" | "neutral";

const CHIP_TONES: Record<ChipTone, { bg: string; fg: string }> = {
  red: { bg: "#FDECEC", fg: "#C0392B" },
  amber: { bg: "#FFF3E6", fg: "#B4661F" },
  green: { bg: "#E8F6EE", fg: "#1F7A49" },
  indigo: { bg: "rgba(75,64,196,.09)", fg: "#4B40C4" },
  neutral: { bg: "#EEF1F5", fg: "#54565E" },
};

export function ToneChip({ tone = "indigo", children }: { tone?: ChipTone; children: React.ReactNode }) {
  const t = CHIP_TONES[tone];
  return (
    <span
      className="whitespace-nowrap rounded-md px-2 py-0.5 text-[10px] font-bold"
      style={{ background: t.bg, color: t.fg }}
    >
      {children}
    </span>
  );
}

export function VignetteCard({
  title,
  badge,
  badgeTone = "green",
  children,
  footer,
}: {
  title: string;
  badge?: string;
  badgeTone?: ChipTone;
  children: React.ReactNode;
  footer?: string;
}) {
  return (
    <div
      className="rounded-[18px] border bg-white p-[18px]"
      style={{ borderColor: "#EAE9E5", boxShadow: "0 18px 40px -24px rgba(17,18,27,.22)" }}
    >
      <div className="mb-2.5 flex items-center gap-2">
        <span className="text-[12.5px] font-bold" style={{ color: "#15161B" }}>
          {title}
        </span>
        {badge && (
          <span className="ml-auto">
            <ToneChip tone={badgeTone}>{badge}</ToneChip>
          </span>
        )}
      </div>
      {children}
      {footer && (
        <div className="mt-2.5 text-[11.5px] leading-relaxed" style={{ color: "#9A9DA4" }}>
          {footer}
        </div>
      )}
    </div>
  );
}

export function VignetteRow({
  mono,
  text,
  chip,
  tone = "neutral",
}: {
  mono: string;
  text: string;
  chip?: string;
  tone?: ChipTone;
}) {
  return (
    <div className="flex items-center gap-2.5 border-t py-[9px]" style={{ borderColor: "#F4F4F1" }}>
      <span className="mono min-w-[58px] flex-none text-[10px] font-semibold" style={{ color: "#4B40C4" }}>
        {mono}
      </span>
      <span className="min-w-0 flex-1 text-[12.5px]" style={{ color: "#3A3D44" }}>
        {text}
      </span>
      {chip && <ToneChip tone={tone}>{chip}</ToneChip>}
    </div>
  );
}

/** Coverage-style progress bar, as on the landing's dashboard mock. */
export function VignetteBar({ label, pct, color }: { label: string; pct: number; color: string }) {
  return (
    <div className="mb-[9px]">
      <div className="mb-1 flex justify-between text-[10.5px]" style={{ color: "#54565E" }}>
        <span>{label}</span>
        <span>{pct}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full" style={{ background: "#F0F0EC" }}>
        <div className="anim-grow h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

/** Mono citation chip in the landing's Ask PolicyAI style. */
export function CitationChip({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="mono rounded-md border px-[7px] py-[3px] text-[10px]"
      style={{ borderColor: "#EAE9E5", color: "#4B40C4" }}
    >
      {children}
    </span>
  );
}

/* -------------------------------- CTA band -------------------------------- */

export function CtaBand({ title, body }: { title: string; body: string }) {
  return (
    <section
      className="flex flex-wrap items-center gap-10 rounded-3xl p-8 sm:p-12 md:p-14"
      style={{ background: "#15161B", color: "#F5F4F2" }}
    >
      <div className="min-w-[280px] flex-1 sm:min-w-[330px]">
        <h2 className="serif m-0 text-[30px] font-medium leading-[1.1] tracking-[-0.02em] md:text-[40px]">{title}</h2>
        <p className="mb-0 mt-3.5 max-w-[52ch] text-[15px] leading-relaxed md:text-[16px]" style={{ color: "#A7ABB4" }}>
          {body}
        </p>
      </div>
      <div className="flex flex-wrap gap-3">
        <Link
          href="/login"
          className="rounded-[14px] px-[26px] py-4 text-[16px] font-semibold text-white no-underline"
          style={{ background: "#4B40C4" }}
        >
          Start free trial
        </Link>
        <Link
          href="/contact?intent=sales"
          className="rounded-[14px] border px-[26px] py-4 text-[16px] font-semibold no-underline"
          style={{ borderColor: "#34363F", color: "#F5F4F2" }}
        >
          Book a walkthrough
        </Link>
      </div>
    </section>
  );
}
