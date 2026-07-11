"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getSupabase, WORKER_URL } from "@/lib/supabase";
import { PageHeader, Kpi, EmptyState } from "@/components/ui";

interface OrgRow {
  id: string;
  name: string;
  slug: string | null;
  created_at: string | null;
  members: number;
  documents: number;
  obligations: number;
  gaps: number;
  tasks: number;
}
interface Overview {
  orgs: number;
  users: number;
  documents: number;
  obligations: number;
  gaps: number;
  scans: number;
  alerts: number;
  regulations: number;
  org_list: OrgRow[];
}

const BAR_OBLIG = "#4b40c4";
const BAR_GAP = "#e0603a";

export default function AdminPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [state, setState] = useState<"loading" | "forbidden" | "error" | "ok">("loading");

  useEffect(() => {
    (async () => {
      const supabase = getSupabase();
      if (!supabase) return setState("error");
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) return setState("forbidden");
      try {
        const resp = await fetch(`${WORKER_URL}/admin/overview`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        if (resp.status === 403) return setState("forbidden");
        if (!resp.ok) return setState("error");
        setData((await resp.json()) as Overview);
        setState("ok");
      } catch {
        setState("error");
      }
    })();
  }, []);

  if (state === "forbidden")
    return (
      <>
        <PageHeader title="Operator Console" subtitle="Platform team access only" />
        <EmptyState
          title="Platform admin access required"
          body="This console is limited to PolicyAI platform administrators. Ask an operator to run `make seed-admin EMAIL=you@…`."
        />
      </>
    );
  if (state === "error")
    return (
      <>
        <PageHeader title="Operator Console" subtitle="Platform team access only" />
        <EmptyState title="Could not load admin data" body="The worker API was unreachable or misconfigured." />
      </>
    );
  if (state === "loading" || !data)
    return (
      <>
        <PageHeader title="Operator Console" subtitle="Platform team access only" />
        <div className="text-sm text-[var(--muted)]">Loading platform insights…</div>
      </>
    );

  const chartData = data.org_list.map((o) => ({
    name: o.name.length > 16 ? o.name.slice(0, 15) + "…" : o.name,
    obligations: o.obligations,
    gaps: o.gaps,
  }));

  const avgGaps = data.orgs ? Math.round(data.gaps / data.orgs) : 0;

  return (
    <>
      <PageHeader
        title="Operator Console"
        subtitle="Platform-wide analytics across every company. Visible to the PolicyAI team only."
      />

      <div className="mb-4 flex items-center gap-2 rounded-lg border border-[#E4E0F7] bg-[#F8F7FE] px-3 py-2 text-[12.5px] text-[var(--brand-ink)]">
        <span className="rounded bg-[var(--brand)] px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
          Team only
        </span>
        You are viewing cross-company data as a platform administrator. Individual companies
        never see this page or each other&apos;s data.
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi label="Companies" value={data.orgs} hint="firms onboarded" />
        <Kpi label="Users" value={data.users} hint="across all firms" />
        <Kpi label="Policy documents" value={data.documents} hint="uploaded by firms" />
        <Kpi
          label="Open gaps"
          value={data.gaps}
          hint={`~${avgGaps} per company`}
          tone={data.gaps > 0 ? "warn" : "default"}
        />
        <Kpi label="Obligations tracked" value={data.obligations} />
        <Kpi label="Regulations in corpus" value={data.regulations} hint="shared graph" />
        <Kpi label="Scans run" value={data.scans} />
        <Kpi label="Alerts fired" value={data.alerts} />
      </div>

      <div className="card mt-5 p-5">
        <div className="mb-3 text-sm font-semibold">Obligations vs gaps by company</div>
        {chartData.length === 0 ? (
          <div className="py-10 text-center text-sm text-[var(--muted)]">No companies yet.</div>
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(220, chartData.length * 46)}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ececec" horizontal={false} />
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
              <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 12 }} />
              <Tooltip cursor={{ fill: "rgba(75,64,196,0.06)" }} />
              <Legend />
              <Bar dataKey="obligations" name="Obligations" fill={BAR_OBLIG} radius={[0, 4, 4, 0]}>
                {chartData.map((_, i) => (
                  <Cell key={i} fill={BAR_OBLIG} />
                ))}
              </Bar>
              <Bar dataKey="gaps" name="Gaps" fill={BAR_GAP} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="card mt-5 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-2.5 font-medium">Company</th>
              <th className="px-4 py-2.5 font-medium">Members</th>
              <th className="px-4 py-2.5 font-medium">Documents</th>
              <th className="px-4 py-2.5 font-medium">Obligations</th>
              <th className="px-4 py-2.5 font-medium">Gaps</th>
              <th className="px-4 py-2.5 font-medium">Tasks</th>
              <th className="px-4 py-2.5 font-medium">Onboarded</th>
            </tr>
          </thead>
          <tbody>
            {data.org_list.map((o) => (
              <tr key={o.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-2.5">
                  <div className="font-medium text-slate-800">{o.name}</div>
                  {o.slug && <div className="text-[11px] text-[var(--muted)]">{o.slug}</div>}
                </td>
                <td className="px-4 py-2.5">{o.members}</td>
                <td className="px-4 py-2.5">{o.documents}</td>
                <td className="px-4 py-2.5">{o.obligations}</td>
                <td className="px-4 py-2.5">
                  {o.gaps > 0 ? (
                    <span className="font-semibold text-[#c2410c]">{o.gaps}</span>
                  ) : (
                    o.gaps
                  )}
                </td>
                <td className="px-4 py-2.5">{o.tasks}</td>
                <td className="px-4 py-2.5 text-[12px] text-[var(--muted)]">
                  {o.created_at ? new Date(o.created_at).toLocaleDateString() : "n/a"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
