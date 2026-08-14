"use client";

/**
 * Controls Testing: the full lifecycle in one page.
 *   1. Define a control (auto ref code C-001, C-002, ...) and link it to the
 *      obligations it satisfies (obligation_controls, browser-writable since
 *      supabase 0016).
 *   2. Record test results inline. Pass/partial update effectiveness here;
 *      a fail is handled by the 0013 DB trigger, which flips the control to
 *      ineffective and raises a control_failed alert on the dashboard.
 *   3. KPIs, the 12-week pass-rate trend and the coverage chips keep the rest
 *      of the UX (dashboard score, workflow pipeline, obligations) honest.
 */

import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Plus, FlaskConical, X } from "lucide-react";
import { getSupabase, getOrgId, workerFetch } from "@/lib/supabase";
import AskCopilotLink from "@/components/AskCopilotLink";
import ControlMappingGuide from "@/components/insights/ControlMappingGuide";
import { PageHeader, Kpi, Badge, DemoBanner, EmptyState } from "@/components/ui";
import { KpiSkeleton, TableSkeleton } from "@/components/Loading";
import { toast } from "@/components/Toast";
import { EFFECTIVENESS_STYLES, type Control, type ControlTest } from "@/lib/types";

const RESULT_STYLES: Record<string, string> = {
  pass: "bg-emerald-100 text-emerald-700",
  fail: "bg-red-100 text-red-700",
  partial: "bg-amber-100 text-amber-700",
};

const FREQUENCIES = ["daily", "weekly", "monthly", "quarterly", "half-yearly", "annual"];

interface ObligationLite {
  id: string;
  title: string;
  severity: string;
}

interface ControlLink {
  obligation_id: string;
  control_id: string;
}

const inputCls =
  "w-full rounded-md border border-[var(--border)] bg-white px-2.5 py-1.5 text-sm text-slate-700";

export default function ControlsPage() {
  const [configured, setConfigured] = useState(true);
  const [controls, setControls] = useState<Control[]>([]);
  const [tests, setTests] = useState<ControlTest[]>([]);
  const [obligations, setObligations] = useState<ObligationLite[]>([]);
  const [links, setLinks] = useState<ControlLink[]>([]);
  const [roster, setRoster] = useState<string[]>([]);
  const [userEmail, setUserEmail] = useState<string>("");
  const [loading, setLoading] = useState(true);

  // add-control form
  const [showAdd, setShowAdd] = useState(false);
  const [fTitle, setFTitle] = useState("");
  const [fRef, setFRef] = useState("");
  const [fDesc, setFDesc] = useState("");
  const [fType, setFType] = useState("preventive");
  const [fFreq, setFFreq] = useState("quarterly");
  const [fOwner, setFOwner] = useState("");
  const [fObls, setFObls] = useState<Set<string>>(new Set());
  const [oblSearch, setOblSearch] = useState("");
  const [saving, setSaving] = useState(false);

  // record-test form (one open row at a time)
  const [testFor, setTestFor] = useState<string | null>(null);
  const [tResult, setTResult] = useState("pass");
  const [tNotes, setTNotes] = useState("");
  const [tEvidence, setTEvidence] = useState("");
  const [savingTest, setSavingTest] = useState(false);

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) {
      setConfigured(false);
      return;
    }
    supabase
      .from("controls")
      .select("*")
      .order("ref_code", { ascending: true })
      .then(({ data }) => {
        setControls((data as Control[]) ?? []);
        setLoading(false);
      });
    supabase
      .from("control_tests")
      .select("*")
      .order("performed_at", { ascending: false })
      .then(({ data }) => setTests((data as ControlTest[]) ?? []));
    supabase
      .from("obligations")
      .select("id,title,severity")
      .order("created_at", { ascending: false })
      .then(({ data }) => setObligations((data as ObligationLite[]) ?? []));
    supabase
      .from("obligation_controls")
      .select("obligation_id,control_id")
      .then(({ data }) => setLinks((data as ControlLink[]) ?? []));
    supabase.auth.getUser().then(({ data }) => setUserEmail(data.user?.email ?? ""));
    workerFetch("/org/roster")
      .then((r) => (r.ok ? r.json() : []))
      .then((rows: { email: string | null }[]) =>
        setRoster(Array.isArray(rows) ? rows.map((r) => r.email).filter(Boolean) as string[] : []),
      )
      .catch(() => {});
  }, []);

  const count = (e: string) => controls.filter((c) => c.effectiveness === e).length;
  const latestTest = (controlId: string) => tests.find((t) => t.control_id === controlId);
  const oblById = useMemo(() => new Map(obligations.map((o) => [o.id, o])), [obligations]);
  const linkedObls = (controlId: string) =>
    links.filter((l) => l.control_id === controlId).map((l) => oblById.get(l.obligation_id)).filter(Boolean) as ObligationLite[];

  const ownerOptions = useMemo(() => {
    const set = new Set<string>(roster);
    controls.forEach((c) => c.owner && set.add(c.owner));
    return Array.from(set).sort();
  }, [roster, controls]);

  // Next free ref code in the C-00N series (C-004 after C-003 and so on).
  const nextRef = useMemo(() => {
    let max = 0;
    controls.forEach((c) => {
      const m = /^C-0*(\d+)$/i.exec(c.ref_code ?? "");
      if (m) max = Math.max(max, parseInt(m[1], 10));
    });
    return `C-${String(max + 1).padStart(3, "0")}`;
  }, [controls]);

  function openAdd() {
    setFRef(nextRef);
    setShowAdd(true);
  }

  async function addControl() {
    if (!fTitle.trim()) {
      toast("Give the control a title", "error");
      return;
    }
    const supabase = getSupabase();
    if (!supabase) return;
    setSaving(true);
    try {
      const orgId = await getOrgId();
      const { data, error } = await supabase
        .from("controls")
        .insert({
          org_id: orgId,
          ref_code: fRef.trim() || null,
          title: fTitle.trim(),
          description: fDesc.trim() || null,
          control_type: fType,
          frequency: fFreq,
          owner: fOwner.trim() || null,
          effectiveness: "untested",
        })
        .select()
        .single();
      if (error) throw error;
      const created = data as Control;
      if (fObls.size > 0) {
        const { error: linkErr } = await supabase.from("obligation_controls").insert(
          Array.from(fObls).map((oid) => ({
            org_id: orgId,
            obligation_id: oid,
            control_id: created.id,
          })),
        );
        if (linkErr) toast(`Control saved, but linking failed: ${linkErr.message}`, "error");
        else setLinks((cur) => [...cur, ...Array.from(fObls).map((oid) => ({ obligation_id: oid, control_id: created.id }))]);
      }
      setControls((cur) =>
        [...cur, created].sort((a, b) => (a.ref_code ?? "").localeCompare(b.ref_code ?? "")),
      );
      toast(`${created.ref_code ?? "Control"} created${fObls.size ? `, linked to ${fObls.size} obligation${fObls.size > 1 ? "s" : ""}` : ""}`);
      setShowAdd(false);
      setFTitle(""); setFDesc(""); setFOwner(""); setFObls(new Set()); setOblSearch("");
    } catch (err) {
      toast(`Couldn't create control: ${(err as Error).message}`, "error");
    } finally {
      setSaving(false);
    }
  }

  async function recordTest(control: Control) {
    const supabase = getSupabase();
    if (!supabase) return;
    setSavingTest(true);
    try {
      const orgId = await getOrgId();
      const now = new Date().toISOString();
      const { data, error } = await supabase
        .from("control_tests")
        .insert({
          org_id: orgId,
          control_id: control.id,
          performed_at: now,
          performed_by: userEmail || null,
          result: tResult,
          notes: tNotes.trim() || null,
          evidence: tEvidence.trim() || null,
        })
        .select()
        .single();
      if (error) throw error;
      setTests((cur) => [data as ControlTest, ...cur]);
      // Pass/partial are applied here; a fail is flipped to ineffective (and
      // alerted) by the DB trigger, so just mirror that locally.
      const eff = tResult === "pass" ? "effective" : tResult === "partial" ? "partial" : "ineffective";
      if (tResult !== "fail") {
        const { error: upErr } = await supabase
          .from("controls")
          .update({ effectiveness: eff, last_tested_at: now })
          .eq("id", control.id);
        if (upErr) throw upErr;
      }
      setControls((cur) =>
        cur.map((c) => (c.id === control.id ? { ...c, effectiveness: eff as Control["effectiveness"], last_tested_at: now } : c)),
      );
      toast(
        tResult === "fail"
          ? `Test recorded. ${control.ref_code ?? control.title} marked ineffective and an alert was raised.`
          : `Test recorded. ${control.ref_code ?? control.title} is ${eff}.`,
      );
      setTestFor(null);
      setTNotes(""); setTEvidence(""); setTResult("pass");
    } catch (err) {
      toast(`Couldn't record test: ${(err as Error).message}`, "error");
    } finally {
      setSavingTest(false);
    }
  }

  const filteredObls = obligations.filter(
    (o) => !oblSearch.trim() || o.title.toLowerCase().includes(oblSearch.trim().toLowerCase()),
  );

  // Pass-rate per ISO week over the last 12 weeks, from the test history.
  const trend = useMemo(() => {
    const now = Date.now();
    const week = 7 * 24 * 3600 * 1000;
    const buckets: { label: string; pass: number; total: number }[] = [];
    for (let i = 11; i >= 0; i--) {
      const start = new Date(now - (i + 1) * week);
      buckets.push({
        label: start.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
        pass: 0,
        total: 0,
      });
    }
    for (const t of tests) {
      if (!t.performed_at || !t.result) continue;
      const age = now - new Date(t.performed_at).getTime();
      const idx = 11 - Math.floor(age / week);
      if (idx < 0 || idx > 11) continue;
      buckets[idx].total += 1;
      if (t.result === "pass") buckets[idx].pass += 1;
    }
    return buckets.map((b) => ({
      label: b.label,
      tests: b.total,
      passRate: b.total ? Math.round((100 * b.pass) / b.total) : null,
    }));
  }, [tests]);
  const testedWeeks = trend.filter((b) => b.tests > 0).length;

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <PageHeader
          title="Controls Testing & Monitoring"
          subtitle="Define controls, link them to obligations, test them on schedule"
        />
        <button
          onClick={openAdd}
          className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--brand)] px-3.5 py-2 text-sm font-semibold text-white shadow-sm hover:opacity-90"
        >
          <Plus size={15} /> Add control
        </button>
      </div>
      {!configured && <DemoBanner />}

      {showAdd && (
        <div className="card mb-4 border-[#E4E0F7] p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-semibold text-slate-800">New control</div>
            <button onClick={() => setShowAdd(false)} className="text-slate-400 hover:text-slate-600" aria-label="Close">
              <X size={16} />
            </button>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="md:col-span-2">
              <label className="mb-1 block text-xs font-medium text-slate-600">Title</label>
              <input
                className={inputCls}
                placeholder="e.g. Quarterly KYC file audit"
                value={fTitle}
                onChange={(e) => setFTitle(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Ref code</label>
              <input className={inputCls} value={fRef} onChange={(e) => setFRef(e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Owner</label>
              <input
                className={inputCls}
                list="control-owner-options"
                placeholder="Who runs this control"
                value={fOwner}
                onChange={(e) => setFOwner(e.target.value)}
              />
              <datalist id="control-owner-options">
                {ownerOptions.map((o) => (
                  <option key={o} value={o} />
                ))}
              </datalist>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Type</label>
              <select className={inputCls} value={fType} onChange={(e) => setFType(e.target.value)}>
                <option value="preventive">Preventive (stops issues before they happen)</option>
                <option value="detective">Detective (finds issues after the fact)</option>
                <option value="corrective">Corrective (fixes issues found)</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Test frequency</label>
              <select className={inputCls} value={fFreq} onChange={(e) => setFFreq(e.target.value)}>
                {FREQUENCIES.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="mb-1 block text-xs font-medium text-slate-600">Description</label>
              <textarea
                className={inputCls}
                rows={2}
                placeholder="What the check does and what evidence it produces"
                value={fDesc}
                onChange={(e) => setFDesc(e.target.value)}
              />
            </div>
            <div className="md:col-span-2">
              <label className="mb-1 block text-xs font-medium text-slate-600">
                Obligations this control satisfies ({fObls.size} selected)
              </label>
              <input
                className={`${inputCls} mb-2`}
                placeholder="Search obligations"
                value={oblSearch}
                onChange={(e) => setOblSearch(e.target.value)}
              />
              <div className="max-h-44 overflow-y-auto rounded-md border border-[var(--border)]">
                {filteredObls.slice(0, 60).map((o) => (
                  <label
                    key={o.id}
                    className="flex cursor-pointer items-center gap-2 border-b border-[var(--border)] px-2.5 py-1.5 text-[13px] last:border-b-0 hover:bg-slate-50"
                  >
                    <input
                      type="checkbox"
                      checked={fObls.has(o.id)}
                      onChange={(e) => {
                        const next = new Set(fObls);
                        if (e.target.checked) next.add(o.id);
                        else next.delete(o.id);
                        setFObls(next);
                      }}
                    />
                    <span className="flex-1 text-slate-700">{o.title}</span>
                    <span className="text-[10px] uppercase text-[var(--muted)]">{o.severity}</span>
                  </label>
                ))}
                {filteredObls.length === 0 && (
                  <div className="px-3 py-4 text-center text-xs text-[var(--muted)]">No obligations match.</div>
                )}
              </div>
            </div>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <button onClick={() => setShowAdd(false)} className="rounded-lg border border-[var(--border)] px-3.5 py-2 text-sm text-slate-600">
              Cancel
            </button>
            <button
              onClick={addControl}
              disabled={saving}
              className="rounded-lg bg-[var(--brand)] px-3.5 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {saving ? "Saving..." : "Create control"}
            </button>
          </div>
        </div>
      )}

      <div className="card mb-4 border-[#E4E0F7] bg-gradient-to-b from-[#F8F7FE] to-white p-4">
        <div className="text-sm font-semibold text-[var(--brand-ink)]">What is a control?</div>
        <p className="mt-1 max-w-3xl text-[13px] leading-relaxed text-slate-600">
          A control is a check or process your team runs to make sure a regulatory obligation is
          actually being met, for example a maker-checker review before payouts, or a quarterly KYC
          file audit. Each control is tested on a schedule; the test result (pass, partial or fail)
          drives its effectiveness rating below and your overall compliance score.
        </p>
        <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-[12px] text-slate-500">
          <span><b className="text-slate-700">1. Define</b> a control and link its obligations</span>
          <span><b className="text-slate-700">2. Test</b> it at its set frequency</span>
          <span><b className="text-slate-700">3. Record</b> the result; a fail raises an alert automatically</span>
        </div>
      </div>

      <ControlMappingGuide />

      {loading ? (
        <>
          <KpiSkeleton />
          <div className="mt-6">
            <TableSkeleton />
          </div>
        </>
      ) : (
        <>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi label="Effective" value={count("effective")} tone="ok" hint="Latest test passed; working as intended" />
        <Kpi label="Partial" value={count("partial")} tone="warn" hint="Works, but with gaps to close" />
        <Kpi label="Ineffective" value={count("ineffective")} tone="danger" hint="Latest test failed; needs remediation" />
        <Kpi label="Untested" value={count("untested")} hint="No test recorded yet; run a first test" />
      </div>

      {testedWeeks >= 2 && (
        <div className="card mt-4 p-4">
          <div className="mb-1 text-sm font-semibold text-slate-700">
            Test pass rate, last 12 weeks
          </div>
          <div className="h-36">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
                <CartesianGrid stroke="#EEF0F4" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 11, fill: "#71757E" }}
                  tickLine={false}
                  axisLine={{ stroke: "#E2E5EB" }}
                />
                <YAxis
                  domain={[0, 100]}
                  ticks={[0, 50, 100]}
                  tick={{ fontSize: 11, fill: "#71757E" }}
                  tickLine={false}
                  axisLine={false}
                  unit="%"
                />
                <Tooltip
                  formatter={(v: number, _n, item) => [
                    `${v}% pass (${item?.payload?.tests} test${item?.payload?.tests === 1 ? "" : "s"})`,
                    "",
                  ]}
                  separator=""
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #E2E5EB" }}
                />
                <Line
                  type="monotone"
                  dataKey="passRate"
                  stroke="#4B40C4"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "#4B40C4", strokeWidth: 0 }}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {controls.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            title="No controls yet"
            body="Click 'Add control' above to define your first check (e.g. C-001 Quarterly KYC file audit), link it to the obligations it satisfies, then record test results to track whether it works."
          />
        </div>
      ) : (
        <div className="card mt-6 overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="border-b border-[var(--border)] bg-slate-50 text-left text-xs uppercase tracking-wide text-[var(--muted)]">
              <tr>
                <th className="px-4 py-3">Control</th>
                <th className="px-4 py-3" title="Preventive stops issues before they happen; detective finds them after">Type</th>
                <th className="px-4 py-3" title="Person responsible for running and testing this control">Owner</th>
                <th className="px-4 py-3" title="How often this control should be tested">Test frequency</th>
                <th className="px-4 py-3" title="Rating from the most recent test result">Effectiveness</th>
                <th className="px-4 py-3">Latest test</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {controls.map((c) => {
                const t = latestTest(c.id);
                const obls = linkedObls(c.id);
                return (
                  <ControlRow
                    key={c.id}
                    control={c}
                    test={t}
                    obligations={obls}
                    testOpen={testFor === c.id}
                    onToggleTest={() => setTestFor(testFor === c.id ? null : c.id)}
                    tResult={tResult}
                    setTResult={setTResult}
                    tNotes={tNotes}
                    setTNotes={setTNotes}
                    tEvidence={tEvidence}
                    setTEvidence={setTEvidence}
                    savingTest={savingTest}
                    onSaveTest={() => recordTest(c)}
                  />
                );
              })}
            </tbody>
          </table>
        </div>
      )}
        </>
      )}
    </div>
  );
}

function ControlRow(props: {
  control: Control;
  test: ControlTest | undefined;
  obligations: ObligationLite[];
  testOpen: boolean;
  onToggleTest: () => void;
  tResult: string;
  setTResult: (v: string) => void;
  tNotes: string;
  setTNotes: (v: string) => void;
  tEvidence: string;
  setTEvidence: (v: string) => void;
  savingTest: boolean;
  onSaveTest: () => void;
}) {
  const { control: c, test: t, obligations: obls } = props;
  return (
    <>
      <tr className="group hover:bg-slate-50/60">
        <td className="px-4 py-3">
          <div className="flex items-center gap-1.5">
            <span className="font-medium text-slate-800">
              {c.ref_code ? `${c.ref_code} · ` : ""}
              {c.title}
            </span>
            <AskCopilotLink
              question={`Suggest a test plan for control '${c.title}'`}
              className="opacity-0 transition-opacity group-hover:opacity-100"
            />
          </div>
          {c.description && (
            <div className="line-clamp-1 text-xs text-[var(--muted)]">{c.description}</div>
          )}
          {obls.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {obls.slice(0, 3).map((o) => (
                <a
                  key={o.id}
                  href="/obligations"
                  title={o.title}
                  className="max-w-[220px] truncate rounded-md border border-[#E4E0F7] bg-[#F8F7FE] px-1.5 py-0.5 text-[10.5px] text-[var(--brand)] no-underline"
                >
                  {o.title}
                </a>
              ))}
              {obls.length > 3 && (
                <span className="text-[10.5px] text-[var(--muted)]">+{obls.length - 3} more</span>
              )}
            </div>
          )}
        </td>
        <td className="px-4 py-3 capitalize text-[var(--muted)]">{c.control_type}</td>
        <td className="px-4 py-3 text-[var(--muted)]">{c.owner ?? "Unassigned"}</td>
        <td className="px-4 py-3 text-[var(--muted)]">{c.frequency ?? "Not set"}</td>
        <td className="px-4 py-3">
          <Badge className={EFFECTIVENESS_STYLES[c.effectiveness]}>{c.effectiveness}</Badge>
        </td>
        <td className="px-4 py-3">
          {t && t.result ? (
            <div className="flex items-center gap-2">
              <Badge className={RESULT_STYLES[t.result] ?? "bg-slate-100"}>{t.result}</Badge>
              <span className="text-[11px] text-[var(--muted)]">
                {t.performed_at ? new Date(t.performed_at).toLocaleDateString() : ""}
              </span>
            </div>
          ) : (
            <span className="text-xs text-[var(--muted)]">Not tested yet</span>
          )}
        </td>
        <td className="px-4 py-3">
          <button
            onClick={props.onToggleTest}
            className="inline-flex items-center gap-1 rounded-md border border-[var(--border)] px-2 py-1 text-xs font-medium text-slate-600 hover:border-[var(--brand)] hover:text-[var(--brand)]"
          >
            <FlaskConical size={12} /> {props.testOpen ? "Close" : "Record test"}
          </button>
        </td>
      </tr>
      {props.testOpen && (
        <tr className="bg-[#FCFCFE]">
          <td colSpan={7} className="px-4 py-3">
            <div className="flex flex-wrap items-end gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Result</label>
                <select
                  className="rounded-md border border-[var(--border)] bg-white px-2.5 py-1.5 text-sm"
                  value={props.tResult}
                  onChange={(e) => props.setTResult(e.target.value)}
                >
                  <option value="pass">Pass</option>
                  <option value="partial">Partial</option>
                  <option value="fail">Fail</option>
                </select>
              </div>
              <div className="min-w-[220px] flex-1">
                <label className="mb-1 block text-xs font-medium text-slate-600">Notes</label>
                <input
                  className={inputCls}
                  placeholder="What was checked, sample size, findings"
                  value={props.tNotes}
                  onChange={(e) => props.setTNotes(e.target.value)}
                />
              </div>
              <div className="min-w-[220px] flex-1">
                <label className="mb-1 block text-xs font-medium text-slate-600">Evidence</label>
                <input
                  className={inputCls}
                  placeholder="Link or reference to the evidence"
                  value={props.tEvidence}
                  onChange={(e) => props.setTEvidence(e.target.value)}
                />
              </div>
              <button
                onClick={props.onSaveTest}
                disabled={props.savingTest}
                className="rounded-lg bg-[var(--brand)] px-3.5 py-2 text-sm font-semibold text-white disabled:opacity-60"
              >
                {props.savingTest ? "Saving..." : "Save test"}
              </button>
            </div>
            {props.tResult === "fail" && (
              <div className="mt-2 text-[11.5px] text-red-600">
                Saving a fail marks this control ineffective and raises an alert on the dashboard automatically.
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}
