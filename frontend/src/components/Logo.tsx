"use client";

import { useId } from "react";

/**
 * The PolicyAI mark: the letter P drawn as a small knowledge graph, white
 * nodes and edges on the brand-gradient tile. One source of truth for the
 * sidebar, marketing nav, login, and (mirrored statically) the favicon at
 * src/app/icon.svg. Keep the two in sync when the mark changes.
 */
export function LogoMark({ size = 28, className }: { size?: number; className?: string }) {
  const id = useId();
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      className={className}
      role="img"
      aria-label="PolicyAI"
    >
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="64" y2="64">
          <stop offset="0" stopColor="#2E6BF7" />
          <stop offset="1" stopColor="#1746D6" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="15" fill={`url(#${id})`} />
      {/* edges: stem plus the angular bowl of the P */}
      <g stroke="#fff" strokeWidth="4" strokeLinecap="round" fill="none">
        <path d="M25 20 L25 46" />
        <path d="M25 20 L41 28 L25 36" />
      </g>
      {/* faint satellite edge: the graph continues beyond the letter */}
      <path d="M41 28 L47 44" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" opacity=".45" />
      {/* nodes */}
      <circle cx="25" cy="20" r="4.6" fill="#fff" />
      <circle cx="41" cy="28" r="5.4" fill="#fff" />
      <circle cx="25" cy="36" r="3.6" fill="#fff" />
      <circle cx="25" cy="46" r="4.6" fill="#fff" />
      <circle cx="47" cy="44" r="2.8" fill="#fff" opacity=".8" />
    </svg>
  );
}

/** Mark + wordmark, for places that show the full brand. */
export function LogoLockup({
  size = 28,
  dark = false,
  className,
}: {
  size?: number;
  /** dark=true renders the wordmark for dark backgrounds */
  dark?: boolean;
  className?: string;
}) {
  return (
    <span className={`inline-flex items-center gap-2 ${className ?? ""}`}>
      <LogoMark size={size} />
      <span
        className="font-extrabold tracking-tight"
        style={{ fontSize: Math.round(size * 0.64), color: dark ? "#fff" : "#15254E" }}
      >
        Policy
        <span style={{ color: dark ? "#7EA4FF" : "#1E5EF6" }}>AI</span>
      </span>
    </span>
  );
}
