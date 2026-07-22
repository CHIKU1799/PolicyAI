"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import clsx from "clsx";
import {
  LayoutDashboard,
  ShieldAlert,
  ListChecks,
  BookOpen,
  Share2,
  TriangleAlert,
  ShieldCheck,
  FileText,
  Sparkles,
  ChevronsUpDown,
  LogOut,
  ShieldHalf,
  Gauge,
} from "lucide-react";
import { getSupabase } from "@/lib/supabase";

const MONITOR = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, hint: "Live compliance posture at a glance" },
  { href: "/obligations", label: "Obligations", icon: ShieldAlert, hint: "What the regulations require you to do" },
  { href: "/graph", label: "Knowledge Graph", icon: Share2, hint: "Explore how regulations, topics and deadlines connect" },
];
const MANAGE = [
  { href: "/gaps", label: "Gap Analysis", icon: TriangleAlert, hint: "Obligations you are not fully covering yet" },
  { href: "/controls", label: "Controls Testing", icon: ShieldCheck, hint: "The checks that prove each obligation is met, and their test results" },
  { href: "/policies", label: "Policies", icon: FileText, hint: "Your internal policy documents and versions" },
  { href: "/tasks", label: "Tasks", icon: ListChecks, hint: "Action items generated from obligations" },
  { href: "/knowledge-base", label: "Knowledge Base", icon: BookOpen, hint: "Your company documents and registrations" },
];

function Brand() {
  return (
    <div className="flex h-14 flex-none items-center gap-2.5 px-4">
      <div className="brand-grad flex h-7 w-7 items-center justify-center rounded-lg text-white shadow-[0_2px_6px_rgba(67,56,184,.35)]">
        <ShieldHalf size={16} />
      </div>
      <span className="text-[16px] font-extrabold tracking-tight">
        Policy<span className="text-[var(--brand)]">AI</span>
      </span>
      <span className="ml-auto rounded-[5px] border border-[var(--border)] px-1.5 py-0.5 text-[9px] font-bold tracking-wider text-[var(--muted-2)]">
        ENT
      </span>
    </div>
  );
}

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [score, setScore] = useState<number | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) return;
    supabase.auth.getUser().then(({ data }) => setEmail(data.user?.email ?? null));
    // Show the Platform section only to platform admins (RLS lets them read their
    // own platform_admins row).
    supabase
      .from("platform_admins")
      .select("user_id")
      .maybeSingle()
      .then(({ data }) => setIsAdmin(!!data));
    supabase
      .from("controls")
      .select("effectiveness")
      .then(({ data }) => {
        const rows = (data as { effectiveness: string }[]) ?? [];
        if (rows.length)
          setScore(Math.round((rows.filter((r) => r.effectiveness === "effective").length / rows.length) * 100));
      });
  }, []);

  async function logout() {
    await getSupabase()?.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  const NavItem = ({ href, label, icon: Icon, hint }: { href: string; label: string; icon: typeof LayoutDashboard; hint?: string }) => (
    <Link href={href} title={hint} className={clsx("nav-link", pathname.startsWith(href) && "nav-link-active")}>
      <span className="flex w-[18px] justify-center">
        <Icon size={16} />
      </span>
      {label}
    </Link>
  );

  const initials = (email ?? "U").split("@")[0].slice(0, 2).toUpperCase();

  return (
    <aside className="flex h-full w-[258px] flex-none flex-col border-r border-[var(--border)] bg-[var(--surface)] shadow-xl lg:shadow-none">
      <Brand />

      {/* workspace switcher */}
      <button className="mx-3 mb-1.5 flex items-center gap-2.5 rounded-xl border border-[var(--border)] bg-white px-2.5 py-2 text-left shadow-[0_1px_2px_rgba(17,18,27,.04)]">
        <div className="flex h-[30px] w-[30px] flex-none items-center justify-center rounded-lg bg-gradient-to-br from-[#3A3D44] to-[#1A1C22] text-[13px] font-extrabold text-white">
          D
        </div>
        <div className="min-w-0 flex-1 leading-tight">
          <div className="truncate text-[13px] font-bold text-[#1A1C22]">Demo Microfinance Co.</div>
          <div className="truncate text-[11px] text-[var(--muted-2)]">Compliance workspace</div>
        </div>
        <ChevronsUpDown size={14} className="flex-none text-[var(--muted-3)]" />
      </button>

      <nav className="flex-1 overflow-y-auto px-3 py-2">
        <Link
          href="/ask"
          className="mb-2.5 flex items-center gap-2.5 rounded-xl border border-[#E4E0F7] bg-gradient-to-b from-[#F8F7FE] to-[#F3F1FC] px-2.5 py-2.5"
        >
          <span className="brand-grad flex h-6 w-6 flex-none items-center justify-center rounded-[7px]">
            <Sparkles size={13} className="text-white" />
          </span>
          <span className="flex-1 text-[13.5px] font-bold text-[var(--brand-ink)]">PolicyAI Copilot</span>
          <span className="rounded-[5px] border border-[#E4E0F7] bg-white px-1.5 py-px text-[10px] font-bold text-[#8B7DE0]">
            ⌘J
          </span>
        </Link>

        <SectionLabel>Monitor</SectionLabel>
        <div className="flex flex-col gap-0.5">
          {MONITOR.map((i) => (
            <NavItem key={i.href} {...i} />
          ))}
        </div>

        <SectionLabel className="pt-4">Manage</SectionLabel>
        <div className="flex flex-col gap-0.5">
          {MANAGE.map((i) => (
            <NavItem key={i.href} {...i} />
          ))}
        </div>

        {isAdmin && (
          <>
            <SectionLabel className="pt-4">Platform</SectionLabel>
            <div className="flex flex-col gap-0.5">
              <NavItem href="/admin" label="Admin Console" icon={Gauge} />
            </div>
          </>
        )}
      </nav>

      {/* compliance score */}
      <div className="mx-3 mb-2 flex-none rounded-xl border border-[var(--border)] bg-white px-3 py-3">
        <div className="mb-2 flex items-center justify-between">
          <span
            className="text-[11.5px] font-semibold text-[var(--muted)]"
            title="Share of your controls whose latest test shows they are effective"
          >
            Compliance score
          </span>
          <span className="text-[13px] font-extrabold text-[var(--success)]">
            {score ?? "--"}
            <span className="text-[10px] font-semibold text-[var(--muted-2)]">/100</span>
          </span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-[var(--border-soft)]">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#1F9D5B] to-[#46BD7C] transition-all"
            style={{ width: `${score ?? 0}%` }}
          />
        </div>
      </div>

      {/* user */}
      <div className="flex flex-none items-center gap-2.5 border-t border-[var(--border-soft)] px-3 py-2.5">
        <div className="flex h-8 w-8 flex-none items-center justify-center rounded-full bg-[#E9E7F8] text-[12px] font-bold text-[var(--brand)]">
          {initials}
        </div>
        <div className="min-w-0 flex-1 leading-tight">
          <div className="truncate text-[12.5px] font-semibold">{email?.split("@")[0] ?? "User"}</div>
          <div className="truncate text-[11px] text-[var(--muted-2)]">{email ?? "Compliance"}</div>
        </div>
        <button onClick={logout} title="Sign out" className="text-[var(--muted-2)] hover:text-[var(--text-2)]">
          <LogOut size={15} />
        </button>
      </div>
    </aside>
  );
}

function SectionLabel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={clsx("px-2.5 pb-1.5 pt-1.5 text-[10.5px] font-bold uppercase tracking-[.09em] text-[#AEAEB4]", className)}>
      {children}
    </div>
  );
}
