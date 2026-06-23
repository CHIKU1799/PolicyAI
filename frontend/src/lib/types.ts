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
