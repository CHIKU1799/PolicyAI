"use client";

import { Fragment, useEffect, useState } from "react";
import { ChevronDown, ChevronRight, FileText, CheckCircle2 } from "lucide-react";
import { getSupabase } from "@/lib/supabase";
import { PageHeader, Badge, DemoBanner, EmptyState, ExportButton } from "@/components/ui";
import { downloadCSV } from "@/lib/export";
import { POLICY_STATUS_STYLES, type Policy } from "@/lib/types";
import { TableSkeleton } from "@/components/Loading";

interface PolicyVersion {
  id: string;
  policy_id: string;
  version_no: number;
  change_note: string | null;
  status: string;
  approved_by: string | null;
  approved_at: string | null;
}

export default function PoliciesPage() {
  const [configured, setConfigured] = useState(true);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [versions, setVersions] = useState<PolicyVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) {
      setConfigured(false);
      return;
    }
    supabase
      .from("policies")
      .select("*")
      .order("updated_at", { ascending: false })
      .then(({ data }) => {
        setPolicies((data as Policy[]) ?? []);
        setLoading(false);
      });
    supabase
      .from("policy_versions")
      .select("*")
      .order("version_no", { ascending: false })
      .then(({ data }) => setVersions((data as PolicyVersion[]) ?? []));
  }, []);

  return (
    <div>
      <PageHeader
        title="Policy Library"
        subtitle="Central library with versioning, review/approval, and audit-ready traceability"
      />
      {!configured && <DemoBanner />}

      {policies.length > 0 && (
        <div className="mb-4 flex justify-end">
          <ExportButton
            label="Export audit trail"
            onClick={() => {
              const byId = new Map(policies.map((p) => [p.id, p]));
              downloadCSV(
                "policy-audit-trail.csv",
                versions
                  .slice()
                  .sort(
                    (a, b) =>
                      (byId.get(a.policy_id)?.title ?? "").localeCompare(
                        byId.get(b.policy_id)?.title ?? "",
                      ) || a.version_no - b.version_no,
                  )
                  .map((v) => ({
                    policy: byId.get(v.policy_id)?.title ?? v.policy_id,
                    owner: byId.get(v.policy_id)?.owner ?? "",
                    version: v.version_no,
                    status: v.status,
                    change_note: v.change_note ?? "",
                    approved_by: v.approved_by ?? "",
                    approved_at: v.approved_at ?? "",
                  })),
              );
            }}
          />
        </div>
      )}

      {loading ? (
        <TableSkeleton />
      ) : policies.length === 0 ? (
        <EmptyState
          title="No policies yet"
          body="Add your governing policies here. Each gets versioned with a review and approval trail."
        />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="border-b border-[var(--border)] bg-slate-50 text-left text-xs uppercase tracking-wide text-[var(--muted)]">
              <tr>
                <th className="w-8 px-4 py-3"></th>
                <th className="px-4 py-3">Policy</th>
                <th className="px-4 py-3">Owner</th>
                <th className="px-4 py-3">Version</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {policies.map((p) => {
                const pv = versions.filter((v) => v.policy_id === p.id);
                return (
                  <Fragment key={p.id}>
                    <tr
                      className="cursor-pointer hover:bg-slate-50"
                      onClick={() => setOpen(open === p.id ? null : p.id)}
                    >
                      <td className="px-4 py-3 text-[var(--muted)]">
                        {open === p.id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2 font-medium text-slate-800">
                          <FileText size={15} className="text-[var(--brand)]" />
                          {p.title}
                        </div>
                        {p.summary && (
                          <div className="line-clamp-1 text-xs text-[var(--muted)]">
                            {p.summary}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-[var(--muted)]">{p.owner ?? "—"}</td>
                      <td className="px-4 py-3 text-[var(--muted)]">v{p.current_version}</td>
                      <td className="px-4 py-3">
                        <Badge className={POLICY_STATUS_STYLES[p.status]}>
                          {p.status.replace("_", " ")}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-[var(--muted)]">
                        {new Date(p.updated_at).toLocaleDateString()}
                      </td>
                    </tr>
                    {open === p.id && (
                      <tr className="bg-slate-50/60">
                        <td></td>
                        <td colSpan={5} className="px-4 py-4">
                          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                            Version history
                          </div>
                          <ul className="space-y-2">
                            {pv.map((v) => (
                              <li key={v.id} className="flex items-start gap-3 text-sm">
                                <span className="rounded bg-slate-200 px-1.5 text-xs font-medium text-slate-700">
                                  v{v.version_no}
                                </span>
                                <div>
                                  <div className="text-slate-700">
                                    {v.change_note ?? "(no note)"}
                                  </div>
                                  {v.approved_by && (
                                    <div className="mt-0.5 flex items-center gap-1 text-[11px] text-emerald-600">
                                      <CheckCircle2 size={12} /> Approved by {v.approved_by}
                                      {v.approved_at &&
                                        ` · ${new Date(v.approved_at).toLocaleDateString()}`}
                                    </div>
                                  )}
                                </div>
                              </li>
                            ))}
                            {pv.length === 0 && (
                              <li className="text-xs text-[var(--muted)]">No versions recorded.</li>
                            )}
                          </ul>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
