"use client";

import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";

/**
 * Subtle inline entry point into the Ask Copilot: navigates to /ask with the
 * question prefilled via ?q=, which the ask page auto-submits once on mount.
 * Designed to sit inside clickable rows/cards, so it stops event propagation.
 */
export default function AskCopilotLink({
  question,
  className = "",
}: {
  question: string;
  className?: string;
}) {
  const router = useRouter();
  return (
    <button
      type="button"
      title={question}
      aria-label={`Ask Copilot: ${question}`}
      onClick={(e) => {
        e.stopPropagation();
        router.push(`/ask?q=${encodeURIComponent(question)}`);
      }}
      className={`inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-transparent px-1.5 py-0.5 text-[11px] font-medium text-[var(--muted)] transition-colors hover:border-[#4b40c4]/30 hover:bg-[#4b40c4]/5 hover:text-[#4b40c4] ${className}`}
    >
      <Sparkles size={12} />
      <span>Ask Copilot</span>
    </button>
  );
}
