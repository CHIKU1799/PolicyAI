"use client";

/** Shared process animations: shimmer skeletons for data loads and a pulse
 *  loader for long-running actions, consistent across the app. */

export function Shimmer({ className = "" }: { className?: string }) {
  return (
    <div className={`pa-shimmer rounded-lg ${className}`}>
      <style jsx global>{`
        .pa-shimmer {
          position: relative;
          overflow: hidden;
          background: #eceef2;
        }
        .pa-shimmer::after {
          content: "";
          position: absolute;
          inset: 0;
          transform: translateX(-100%);
          background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.75), transparent);
          animation: pa-shimmer 1.4s ease infinite;
        }
        @keyframes pa-shimmer {
          100% {
            transform: translateX(100%);
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .pa-shimmer::after {
            animation: none;
          }
        }
      `}</style>
    </div>
  );
}

/** Full-card table/list placeholder while a page's data loads. */
export function TableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="card overflow-hidden">
      <div className="border-b border-[var(--border)] bg-slate-50 px-4 py-3">
        <Shimmer className="h-3 w-44" />
      </div>
      <div className="divide-y divide-[var(--border)]">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-4 py-3.5">
            <Shimmer className="h-3.5 w-1/3" />
            <Shimmer className="h-3.5 w-16" />
            <Shimmer className="h-3.5 w-24" />
            <Shimmer className="ml-auto h-3.5 w-20" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function KpiSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card p-4">
          <Shimmer className="h-3 w-24" />
          <Shimmer className="mt-3 h-7 w-16" />
          <Shimmer className="mt-2 h-2.5 w-28" />
        </div>
      ))}
    </div>
  );
}

/** Overlay pulse loader for in-progress work inside a container. */
export function ProcessOverlay({ label }: { label: string }) {
  return (
    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-white/70 backdrop-blur-[2px]">
      <span className="pa-orbits relative inline-block h-10 w-10">
        <span className="pa-orbit-dot" />
        <span className="pa-orbit-dot" style={{ animationDelay: "-0.5s" }} />
        <span className="pa-orbit-dot" style={{ animationDelay: "-1s" }} />
      </span>
      <span className="text-xs font-medium text-[var(--muted)]">{label}</span>
      <style jsx global>{`
        .pa-orbit-dot {
          position: absolute;
          left: 50%;
          top: 50%;
          width: 9px;
          height: 9px;
          margin: -4.5px;
          border-radius: 50%;
          background: #4b40c4;
          animation: pa-orbit 1.5s linear infinite;
        }
        @keyframes pa-orbit {
          from {
            transform: rotate(0deg) translateX(16px);
            opacity: 1;
          }
          to {
            transform: rotate(360deg) translateX(16px);
            opacity: 0.35;
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .pa-orbit-dot {
            animation-duration: 3s;
          }
        }
      `}</style>
    </div>
  );
}

/** Inline button spinner. */
export function ButtonSpinner() {
  return (
    <span
      aria-hidden
      className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white align-[-2px]"
    />
  );
}
