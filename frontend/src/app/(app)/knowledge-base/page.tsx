"use client";

import { useEffect, useState } from "react";
import { UploadCloud, FileText, Sparkles } from "lucide-react";
import { getSupabase, KB_BUCKET, workerFetch } from "@/lib/supabase";
import { PageHeader, Badge, DemoBanner } from "@/components/ui";
import type { CompanyDocument } from "@/lib/types";

const STATUS_STYLE: Record<string, string> = {
  processed: "bg-emerald-100 text-emerald-700",
  pending: "bg-slate-100 text-slate-600",
  needs_ocr: "bg-amber-100 text-amber-700",
  failed: "bg-red-100 text-red-700",
};

export default function KnowledgeBasePage() {
  const [configured, setConfigured] = useState(true);
  const [docs, setDocs] = useState<CompanyDocument[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function refresh() {
    const supabase = getSupabase();
    if (!supabase) {
      setConfigured(false);
      return;
    }
    const { data } = await supabase
      .from("company_documents")
      .select("*")
      .order("uploaded_at", { ascending: false });
    setDocs((data as CompanyDocument[]) ?? []);
  }

  useEffect(() => {
    refresh();
  }, []);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    const supabase = getSupabase();
    if (!file || !supabase) return;
    setBusy(true);
    setMsg(null);
    try {
      const path = `${Date.now()}-${file.name}`;
      const { error } = await supabase.storage.from(KB_BUCKET).upload(path, file);
      if (error) throw error;
      const resp = await workerFetch("/documents/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ storage_path: path, filename: file.name, mime: file.type }),
      });
      const body = await resp.json();
      setMsg(`Processed "${file.name}" — status: ${body.status} (${body.chars} chars).`);
      await refresh();
    } catch (err) {
      setMsg(`Upload failed: ${(err as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  async function deriveProfile() {
    setBusy(true);
    setMsg(null);
    try {
      const resp = await workerFetch("/profile/derive", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const body = await resp.json();
      setMsg(
        `Profile derived — entity classes: ${(body.entity_classes ?? []).join(", ") || "none"}.`,
      );
    } catch (err) {
      setMsg(`Profile derivation failed: ${(err as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Knowledge Base"
        subtitle="Upload your company's policies and registrations. We derive your regulatory profile and map new obligations against it."
      />
      {!configured && <DemoBanner />}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <label className="card flex cursor-pointer flex-col items-center justify-center gap-2 border-dashed px-6 py-10 text-center hover:border-blue-400">
          <UploadCloud className="text-blue-500" size={28} />
          <span className="text-sm font-medium text-slate-700">
            {busy ? "Working…" : "Upload a policy document"}
          </span>
          <span className="text-xs text-[var(--muted)]">PDF or DOCX</span>
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            className="hidden"
            disabled={busy || !configured}
            onChange={onUpload}
          />
        </label>

        <button
          onClick={deriveProfile}
          disabled={busy || !configured}
          className="card flex flex-col items-center justify-center gap-2 px-6 py-10 text-center hover:border-blue-400 disabled:opacity-60"
        >
          <Sparkles className="text-blue-500" size={28} />
          <span className="text-sm font-medium text-slate-700">Derive company profile</span>
          <span className="text-xs text-[var(--muted)]">From all uploaded documents</span>
        </button>

        <div className="card flex flex-col justify-center px-6 py-6">
          <div className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Documents
          </div>
          <div className="mt-1 text-3xl font-semibold">{docs.length}</div>
          <div className="mt-1 text-xs text-[var(--muted)]">
            in your knowledge base
          </div>
        </div>
      </div>

      {msg && (
        <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2.5 text-sm text-blue-800">
          {msg}
        </div>
      )}

      <div className="card mt-6 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-[var(--border)] bg-slate-50 text-left text-xs uppercase tracking-wide text-[var(--muted)]">
            <tr>
              <th className="px-4 py-3">Document</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Uploaded</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {docs.map((d) => (
              <tr key={d.id}>
                <td className="flex items-center gap-2 px-4 py-3">
                  <FileText size={16} className="text-[var(--muted)]" />
                  <span className="text-slate-800">{d.filename}</span>
                </td>
                <td className="px-4 py-3">
                  <Badge className={STATUS_STYLE[d.status] ?? "bg-slate-100 text-slate-600"}>
                    {d.status.replace(/_/g, " ")}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-[var(--muted)]">
                  {new Date(d.uploaded_at).toLocaleString()}
                </td>
              </tr>
            ))}
            {docs.length === 0 && (
              <tr>
                <td colSpan={3} className="px-4 py-10 text-center text-sm text-[var(--muted)]">
                  No documents yet. Upload a policy to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
