"use client";

/**
 * Shared chrome for the marketing pages (/platform, /solutions, /security,
 * /resources, /pricing, /blog/*) in the exact design language of the landing
 * page snapshot: Hanken Grotesk body, Newsreader serif display, #F5F4F2 paper,
 * #15254E navy ink, #1E5EF6 -> #1746D6 blue gradient CTAs.
 */

import Link from "next/link";
import { useState } from "react";

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

function Caret() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M6 9l6 6 6-6" stroke="#B6B9BF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function MarketingNav() {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className="sticky top-0 z-50">
      <div
        style={{ background: "#0C1A38", color: "#E4E2F4" }}
        className="px-4 py-1.5 text-center text-[12px]"
      >
        <span
          className="mr-2 rounded px-2 py-0.5 text-[10px] font-bold tracking-wide"
          style={{ background: "rgba(255,255,255,.12)" }}
        >
          NEW
        </span>
        PolicyAI Copilot now drafts impact assessments automatically{" "}
        <Link href="/blog/copilot-impact-assessments" className="font-semibold text-white hover:underline">
          Read more →
        </Link>
      </div>
      <header
        className="border-b px-5"
        style={{ background: "rgba(255,255,255,.92)", backdropFilter: "blur(10px)", borderColor: "#E8E7E2" }}
      >
        <div className="mx-auto flex h-[58px] max-w-6xl items-center">
          <Link href="/" className="flex items-center gap-2 no-underline">
            <span
              className="flex h-7 w-7 items-center justify-center rounded-lg text-[13px] font-extrabold text-white"
              style={{ background: "linear-gradient(135deg,#2E6BF7,#1746D6)" }}
            >
              P
            </span>
            <span className="text-[18px] font-extrabold tracking-tight" style={{ color: "#15254E" }}>
              Policy<span style={{ color: "#1E5EF6" }}>AI</span>
            </span>
          </Link>
          <nav className="ml-6 hidden items-center gap-0.5 md:flex">
            {NAV.map((n) => (
              <div
                key={n.label}
                className="relative"
                onMouseEnter={() => setOpen(n.label)}
                onMouseLeave={() => setOpen(null)}
              >
                <Link
                  href={n.href}
                  className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-[13.5px] font-medium no-underline hover:bg-[#F1F0EC]"
                  style={{ color: "#54565E" }}
                >
                  {n.label}
                  {n.items && <Caret />}
                </Link>
                {n.items && open === n.label && (
                  <div
                    className="absolute left-0 top-full w-72 rounded-xl border bg-white p-2 shadow-xl"
                    style={{ borderColor: "#E8E7E2", boxShadow: "0 16px 40px -12px rgba(21,37,78,.18)" }}
                  >
                    {n.items.map((it) => (
                      <Link
                        key={it.href}
                        href={it.href}
                        className="block rounded-lg px-3 py-2 no-underline hover:bg-[#F5F4F2]"
                      >
                        <div className="text-[13px] font-medium" style={{ color: "#1A1C22" }}>
                          {it.label}
                        </div>
                        <div className="text-[11px]" style={{ color: "#71757E" }}>
                          {it.sub}
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2.5">
            <Link
              href="/login"
              className="px-3 py-2 text-[13.5px] font-semibold no-underline"
              style={{ color: "#3A3D44" }}
            >
              Sign in
            </Link>
            <Link
              href="/contact"
              className="rounded-[10px] px-4 py-2 text-[13.5px] font-semibold text-white no-underline"
              style={{
                background: "linear-gradient(135deg,#2E6BF7,#1746D6)",
                boxShadow: "0 2px 8px rgba(23,70,214,.3)",
              }}
            >
              Book a demo
            </Link>
          </div>
        </div>
      </header>
    </div>
  );
}

export function MarketingFooter() {
  return (
    <footer className="border-t px-5 py-12" style={{ background: "#FCFBFA", borderColor: "#E8E7E2" }}>
      <div className="mx-auto grid max-w-6xl gap-10 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
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
