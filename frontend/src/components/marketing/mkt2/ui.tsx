import Link from "next/link";

/**
 * Shared primitives for the rebuilt marketing pages (pricing, security,
 * resources, contact) in the landing page's design language: serif display
 * headlines, mono uppercase kickers, #4B40C4 accent, rounded cards on
 * #F5F4F2 paper, dark #15161B bands.
 */

export const INK = "#15161B";
export const BODY = "#5B5E66";
export const MUTED = "#71757E";
export const FAINT = "#9A9DA4";
export const LINE = "#EAE9E5";
export const ACCENT = "#4B40C4";
export const GREEN = "#1F9D5B";

export function Kicker({ children }: { children: React.ReactNode }) {
  return (
    <span className="mono text-[11px] font-semibold tracking-[.18em]" style={{ color: MUTED }}>
      {children}
    </span>
  );
}

export function PageHero({
  kicker,
  title,
  lede,
}: {
  kicker: string;
  title: React.ReactNode;
  lede?: React.ReactNode;
}) {
  return (
    <section className="anim-rise flex flex-col items-center gap-5 text-center">
      <Kicker>{kicker}</Kicker>
      <h1 className="serif m-0 max-w-[20ch] text-balance text-[36px] font-medium leading-[1.07] tracking-[-0.02em] sm:text-[46px] md:text-[56px] md:leading-[1.05]">
        {title}
      </h1>
      {lede ? (
        <p
          className="m-0 max-w-[62ch] text-pretty text-[15.5px] leading-relaxed md:text-[17px]"
          style={{ color: BODY }}
        >
          {lede}
        </p>
      ) : null}
    </section>
  );
}

export function CheckItem({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-2 text-[13px] leading-relaxed" style={{ color: "#3A3D44" }}>
      <span aria-hidden className="mt-px flex-none" style={{ color: GREEN }}>
        ✓
      </span>
      <span>{children}</span>
    </li>
  );
}

/** Dark closing band, matching the landing page CTA section. */
export function CtaBand({
  title,
  body,
  primary,
  secondary,
}: {
  title: string;
  body: string;
  primary: { label: string; href: string };
  secondary: { label: string; href: string };
}) {
  return (
    <section
      className="flex flex-wrap items-center gap-10 rounded-3xl p-8 sm:p-12 md:p-14"
      style={{ background: "#15161B", color: "#F5F4F2" }}
    >
      <div className="min-w-[260px] flex-1 sm:min-w-[330px]">
        <h2 className="serif m-0 text-[28px] font-medium leading-[1.1] tracking-[-0.02em] md:text-[38px]">
          {title}
        </h2>
        <p
          className="mb-0 mt-3.5 max-w-[52ch] text-[15px] leading-relaxed md:text-[16px]"
          style={{ color: "#A7ABB4" }}
        >
          {body}
        </p>
      </div>
      <div className="flex flex-wrap gap-3">
        <Link
          href={primary.href}
          className="rounded-[14px] px-[26px] py-4 text-[16px] font-semibold text-white no-underline"
          style={{ background: ACCENT }}
        >
          {primary.label}
        </Link>
        <Link
          href={secondary.href}
          className="rounded-[14px] border px-[26px] py-4 text-[16px] font-semibold no-underline"
          style={{ borderColor: "#34363F", color: "#F5F4F2" }}
        >
          {secondary.label}
        </Link>
      </div>
    </section>
  );
}

/** Slim row of factual reassurances, used under pricing tiers and CTAs. */
export function TrustStrip({ items }: { items: string[] }) {
  return (
    <div
      className="flex flex-wrap items-center justify-center gap-x-3 gap-y-2 text-[12.5px]"
      style={{ color: FAINT }}
    >
      {items.map((t, i) => (
        <span key={t} className="flex items-center gap-3">
          {i > 0 && (
            <span aria-hidden className="hidden sm:inline">
              ·
            </span>
          )}
          {t}
        </span>
      ))}
    </div>
  );
}

/** Native-details accordion; no client JS needed. */
export function Faq({ items }: { items: { q: string; a: React.ReactNode }[] }) {
  return (
    <div className="flex flex-col gap-2.5">
      {items.map((it) => (
        <details
          key={it.q}
          className="group rounded-2xl border bg-white px-5"
          style={{ borderColor: LINE }}
        >
          <summary className="flex cursor-pointer list-none items-center gap-4 py-4 [&::-webkit-details-marker]:hidden">
            <span className="flex-1 text-[15px] font-semibold" style={{ color: INK }}>
              {it.q}
            </span>
            <span
              aria-hidden
              className="flex h-7 w-7 flex-none items-center justify-center rounded-full border text-[15px] transition-transform group-open:rotate-45"
              style={{ borderColor: LINE, color: ACCENT }}
            >
              +
            </span>
          </summary>
          <div
            className="pb-5 pr-2 text-pretty text-[13.5px] leading-relaxed"
            style={{ color: BODY }}
          >
            {it.a}
          </div>
        </details>
      ))}
    </div>
  );
}
