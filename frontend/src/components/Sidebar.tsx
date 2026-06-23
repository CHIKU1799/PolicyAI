"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  LayoutDashboard,
  ShieldAlert,
  ListChecks,
  BookOpen,
  Share2,
  ScanLine,
  MessageSquare,
} from "lucide-react";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/ask", label: "Ask PolicyAI", icon: MessageSquare },
  { href: "/obligations", label: "Obligations", icon: ShieldAlert },
  { href: "/tasks", label: "Tasks", icon: ListChecks },
  { href: "/knowledge-base", label: "Knowledge Base", icon: BookOpen },
  { href: "/graph", label: "Knowledge Graph", icon: Share2 },
];

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex w-60 flex-col bg-[#0b1f4d] px-4 py-5 text-white">
      <div className="mb-7 flex items-center gap-2 px-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500">
          <ScanLine size={18} />
        </div>
        <div>
          <div className="text-sm font-semibold leading-tight">PolicyAI</div>
          <div className="text-[11px] text-slate-400">Regulatory Intelligence</div>
        </div>
      </div>
      <nav className="flex flex-col gap-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={clsx("nav-link", active && "nav-link-active")}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto rounded-lg bg-white/5 p-3 text-[11px] text-slate-400">
        Monitoring RBI · SEBI · IRDAI · MCA
      </div>
    </aside>
  );
}
