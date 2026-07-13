"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Styled GitHub-flavored markdown for Copilot answers: tight headings,
 *  scannable lists, and compact bordered tables that scroll on overflow. */
export default function Markdown({ children }: { children: string }) {
  return (
    <div className="pa-md text-sm leading-relaxed text-slate-800">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (p) => <h3 className="mb-1.5 mt-3 text-[15px] font-semibold first:mt-0" {...p} />,
          h2: (p) => <h3 className="mb-1.5 mt-3 text-[15px] font-semibold first:mt-0" {...p} />,
          h3: (p) => (
            <h3
              className="mb-1.5 mt-3 text-[13px] font-semibold uppercase tracking-wide text-[var(--muted)] first:mt-0"
              {...p}
            />
          ),
          p: (p) => <p className="mb-2 last:mb-0" {...p} />,
          ul: (p) => <ul className="mb-2 list-disc space-y-1 pl-5 last:mb-0" {...p} />,
          ol: (p) => <ol className="mb-2 list-decimal space-y-1 pl-5 last:mb-0" {...p} />,
          strong: (p) => <strong className="font-semibold text-[#23204A]" {...p} />,
          a: (p) => (
            <a className="text-blue-600 hover:underline" target="_blank" rel="noreferrer" {...p} />
          ),
          code: (p) => (
            <code
              className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[12px] text-[#4b40c4]"
              {...p}
            />
          ),
          blockquote: (p) => (
            <blockquote
              className="mb-2 border-l-2 border-[#4b40c4] bg-indigo-50/50 px-3 py-1.5 text-slate-700"
              {...p}
            />
          ),
          table: (p) => (
            <div className="mb-2 overflow-x-auto rounded-lg border border-[var(--border)]">
              <table className="w-full border-collapse text-[13px]" {...p} />
            </div>
          ),
          thead: (p) => (
            <thead
              className="bg-slate-50 text-left text-[11px] uppercase tracking-wide text-[var(--muted)]"
              {...p}
            />
          ),
          th: (p) => <th className="border-b border-[var(--border)] px-3 py-2 font-semibold" {...p} />,
          td: (p) => (
            <td className="border-b border-[var(--border)] px-3 py-2 align-top last:border-b-0" {...p} />
          ),
          hr: () => <hr className="my-3 border-[var(--border)]" />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
