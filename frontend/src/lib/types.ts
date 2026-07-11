export type Severity = "critical" | "high" | "medium" | "low" | "informational";
export type TaskStatus = "todo" | "in_progress" | "done" | "blocked";
export type Priority = "urgent" | "high" | "medium" | "low";

export interface Obligation {
  id: string;
  title: string;
  summary: string;
  what_changed: string | null;
  gap_analysis: string | null;
  severity: Severity;
  status: string;
  created_at: string;
  regulation_node_id: string | null;
  effective_date: string | null;
  valid_to: string | null;
  invalidated_at: string | null;
  obligation_type: string | null;
  frequency: string | null;
  regulatory_citation: string | null;
  penalty_summary: string | null;
  evidence_required: string | null;
  mapping_confidence: number | null;
  relevance_rationale: string | null;
}

export interface Task {
  id: string;
  obligation_id: string;
  title: string;
  description: string | null;
  owner: string | null;
  due_date: string | null;
  priority: Priority;
  status: TaskStatus;
  created_at: string;
}

export interface Alert {
  id: string;
  kind: string;
  message: string;
  read_at: string | null;
  created_at: string;
}

export interface CompanyDocument {
  id: string;
  filename: string;
  status: string;
  uploaded_at: string;
}

export interface ScanRun {
  id: string;
  status: string;
  docs_found: number;
  docs_new: number;
  started_at: string;
  finished_at: string | null;
}

export const SEVERITY_STYLES: Record<Severity, string> = {
  critical: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-sky-100 text-sky-700",
  informational: "bg-slate-100 text-slate-600",
};

export const PRIORITY_STYLES: Record<Priority, string> = {
  urgent: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-slate-100 text-slate-600",
};

export const TASK_COLUMNS: { key: TaskStatus; label: string }[] = [
  { key: "todo", label: "To do" },
  { key: "in_progress", label: "In progress" },
  { key: "blocked", label: "Blocked" },
  { key: "done", label: "Done" },
];

// --- GRC entities ---
export type Effectiveness = "effective" | "partial" | "ineffective" | "untested";
export type GapStatus = "open" | "remediating" | "closed" | "accepted";
export type PolicyStatus = "draft" | "in_review" | "approved" | "archived";

export interface Control {
  id: string;
  ref_code: string | null;
  title: string;
  description: string | null;
  control_type: string;
  frequency: string | null;
  owner: string | null;
  effectiveness: Effectiveness;
  last_tested_at: string | null;
}

export interface ControlTest {
  id: string;
  control_id: string;
  performed_at: string | null;
  performed_by: string | null;
  result: string | null;
  notes: string | null;
}

export interface Policy {
  id: string;
  title: string;
  summary: string | null;
  owner: string | null;
  status: PolicyStatus;
  current_version: number;
  updated_at: string;
}

export interface Gap {
  id: string;
  obligation_id: string;
  description: string;
  severity: Severity;
  status: GapStatus;
  remediation_plan: string | null;
  owner: string | null;
  due_date: string | null;
  created_at: string;
}

export const EFFECTIVENESS_STYLES: Record<Effectiveness, string> = {
  effective: "bg-emerald-100 text-emerald-700",
  partial: "bg-amber-100 text-amber-700",
  ineffective: "bg-red-100 text-red-700",
  untested: "bg-slate-100 text-slate-600",
};

export const GAP_STATUS_STYLES: Record<GapStatus, string> = {
  open: "bg-red-100 text-red-700",
  remediating: "bg-amber-100 text-amber-700",
  closed: "bg-emerald-100 text-emerald-700",
  accepted: "bg-slate-100 text-slate-600",
};

export const POLICY_STATUS_STYLES: Record<PolicyStatus, string> = {
  draft: "bg-slate-100 text-slate-600",
  in_review: "bg-amber-100 text-amber-700",
  approved: "bg-emerald-100 text-emerald-700",
  archived: "bg-slate-100 text-slate-500",
};

export const GAP_COLUMNS: { key: GapStatus; label: string }[] = [
  { key: "open", label: "Open" },
  { key: "remediating", label: "Remediating" },
  { key: "accepted", label: "Accepted" },
  { key: "closed", label: "Closed" },
];
