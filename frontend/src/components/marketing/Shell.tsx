"use client";

/**
 * Shared chrome for the marketing pages (/platform, /solutions, /security,
 * /resources, /pricing, /blog/*) in the exact design language of the landing
 * page snapshot: Hanken Grotesk body, Newsreader serif display, #F5F4F2 paper,
 * #15254E navy ink, #1E5EF6 -> #1746D6 blue gradient CTAs.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { LogoMark } from "@/components/Logo";

export const NAV: {
  label: string;
  href: string;
  items?: { label: string; sub: string; href: string }[];
}[] = [
  {
    label: "Platform",
    href: "/platform",
    items: [
      { label: "Horizon scanning", sub: "RBI, SEBI, IRDAI & more, continuously", href: "/platform#monitor" },
      { label: "Structured obligations", sub: "Every update becomes trackable work", href: "/platform#structure" },
      { label: "Gap analysis", sub: "Your policies vs the rules, cited", href: "/platform#assess" },
      { label: "Controls testing", sub: "Effectiveness, trends and alerts", href: "/platform#test" },
      { label: "Policy governance", sub: "Versioned, approved, audit-ready", href: "/platform#govern" },
      { label: "Knowledge graph", sub: "How every rule connects", href: "/platform#graph" },
    ],
  },
  {
    label: "Solutions",
    href: "/solutions",
    items: [
      { label: "For NBFCs", sub: "Scale-based regulation, SBR compliance", href: "/solutions#nbfc" },
      { label: "For Microfinance", sub: "Pricing caps, fair practices, JLG rules", href: "/solutions#mfi" },
      { label: "For AIFs & PMS", sub: "SEBI circulars, disclosure calendars", href: "/solutions#aif" },
      { label: "For Payment Aggregators", sub: "PA/PG guidelines, escrow, KYC", href: "/solutions#pa" },
      { label: "For Insurers", sub: "IRDAI circulars and product norms", href: "/solutions#insurer" },
    ],
  },
  {
    label: "Security",
    href: "/security",
    items: [
      { label: "Security overview", sub: "How your data is protected", href: "/security" },
      { label: "Tenant isolation", sub: "Row-level security per firm", href: "/security#isolation" },
      { label: "Roadmap", sub: "SSO, SCIM, India region", href: "/security#roadmap" },
    ],
  },
  {
    label: "Resources",
    href: "/resources",
    items: [
      { label: "Blog", sub: "Copilot now drafts impact assessments", href: "/blog/copilot-impact-assessments" },
      { label: "Documentation", sub: "Architecture, deploys, mapping", href: "/resources#docs" },
      { label: "Changelog", sub: "What shipped recently", href: "/resources#changelog" },
      { label: "System status", sub: "Operator health checks", href: "/resources#status" },
    ],
  },
  { label: "Pricing", href: "/pricing" },
];

/** Pill-tab nav in the landing v2 design language. */
const TABS: { label: string; href: string }[] = [
  { label: "Home", href: "/" },
  { label: "Platform", href: "/platform" },
  { label: "Solutions", href: "/solutions" },
  { label: "Pricing", href: "/pricing" },
  { label: "Security", href: "/security" },
  { label: "Resources", href: "/resources" },
  { label: "Contact", href: "/contact" },
];

export function MarketingNav() {
  const pathname = usePathname() || "/";
  const [open, setOpen] = useState(false);
  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(href + "/");
  return (
    <nav
      className="sticky top-0 z-50 border-b"
      style={{
        background: "rgba(245,244,242,.86)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        borderColor: "#EAE9E5",
      }}
    >
      <div className="mx-auto flex h-[62px] max-w-[1304px] items-center gap-4 px-5 md:px-8 lg:gap-6">
        <Link href="/" className="flex flex-none items-center gap-[9px] no-underline">
          <LogoMark size={24} />
          <span className="text-[16px] font-extrabold tracking-tight" style={{ color: "#15161B" }}>
            PolicyAI
          </span>
        </Link>
        <div className="hidden flex-1 items-center gap-1 lg:flex">
          {TABS.map((t) => (
            <Link
              key={t.href}
              href={t.href}
              className="rounded-full px-[13px] py-[7px] text-[13.5px] font-semibold no-underline transition-colors hover:text-[#15161B]"
              style={
                isActive(t.href)
                  ? { background: "rgba(75,64,196,.1)", color: "#4B40C4" }
                  : { color: "#5B5E66" }
              }
            >
              {t.label}
            </Link>
          ))}
        </div>
        <div className="ml-auto flex flex-none items-center gap-3 lg:ml-0">
          <Link
            href="/login"
            className="hidden whitespace-nowrap text-[13.5px] font-semibold no-underline hover:text-[#15161B] sm:block"
            style={{ color: "#5B5E66" }}
          >
            Sign in
          </Link>
          <Link
            href="/login"
            className="whitespace-nowrap rounded-[11px] px-[18px] py-[9px] text-[13.5px] font-semibold text-white no-underline"
            style={{ background: "#4B40C4", boxShadow: "0 4px 14px rgba(75,64,196,.24)" }}
          >
            Start free
          </Link>
          <button
            type="button"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
            className="flex h-9 w-9 items-center justify-center rounded-[10px] border lg:hidden"
            style={{ borderColor: "#E2E1DC", background: "#fff", color: "#3A3D44" }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
              {open ? (
                <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              ) : (
                <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              )}
            </svg>
          </button>
        </div>
      </div>
      {open && (
        <div className="border-t px-5 py-3 lg:hidden" style={{ borderColor: "#EAE9E5" }}>
          <div className="flex flex-col gap-1">
            {TABS.map((t) => (
              <Link
                key={t.href}
                href={t.href}
                onClick={() => setOpen(false)}
                className="rounded-[10px] px-3 py-2 text-[14px] font-semibold no-underline"
                style={
                  isActive(t.href)
                    ? { background: "rgba(75,64,196,.1)", color: "#4B40C4" }
                    : { color: "#3A3D44" }
                }
              >
                {t.label}
              </Link>
            ))}
            <Link
              href="/login"
              onClick={() => setOpen(false)}
              className="rounded-[10px] px-3 py-2 text-[14px] font-semibold no-underline sm:hidden"
              style={{ color: "#3A3D44" }}
            >
              Sign in
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}

export function MarketingFooter() {
  return (
    <footer className="border-t px-5 py-12" style={{ background: "#FCFBFA", borderColor: "#E8E7E2" }}>
      <div className="mx-auto grid max-w-6xl gap-10 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr_1fr_1fr]">
        <div>
          <div className="text-[16px] font-extrabold" style={{ color: "#15254E" }}>
            Policy<span style={{ color: "#1E5EF6" }}>AI</span>
          </div>
          <p className="mt-2 max-w-[260px] text-[12.5px] leading-relaxed" style={{ color: "#71757E" }}>
            Regulatory intelligence for modern compliance teams. Monitor, structure, assess, and
            govern, in one platform.
          </p>
        </div>
        {NAV.filter((n) => n.items).map((n) => (
          <div key={n.label}>
            <div className="text-[11px] font-bold uppercase tracking-wider" style={{ color: "#9A9DA4" }}>
              {n.label}
            </div>
            <ul className="mt-3 space-y-2">
              {n.items!.map((it) => (
                <li key={it.href}>
                  <Link
                    href={it.href}
                    className="text-[12.5px] no-underline hover:underline"
                    style={{ color: "#54565E" }}
                  >
                    {it.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div
        className="mx-auto mt-10 flex max-w-6xl flex-wrap items-center gap-3 border-t pt-6 text-[11.5px]"
        style={{ borderColor: "#EDECE8", color: "#9A9DA4" }}
      >
        © 2026 PolicyAI, Inc. All rights reserved.
        <span className="ml-auto flex gap-2">
          {["Made for Indian BFSI", "RBI · SEBI · IRDAI", "Graph-native"].map((b) => (
            <span key={b} className="rounded-md border px-2 py-1" style={{ borderColor: "#E2E1DC" }}>
              {b}
            </span>
          ))}
        </span>
      </div>
    </footer>
  );
}

export default function MarketingShell({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{ background: "#F5F4F2", color: "#1A1C22", fontFamily: "var(--font-sans), sans-serif" }}
      className="min-h-screen"
    >
      <MarketingNav />
      {children}
      <MarketingFooter />
    </div>
  );
}
