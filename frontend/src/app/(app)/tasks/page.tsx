"use client";

import { useEffect, useState } from "react";
import { getSupabase } from "@/lib/supabase";
import { TableSkeleton } from "@/components/Loading";
import { PageHeader, Badge, DemoBanner } from "@/components/ui";
import { toast } from "@/components/Toast";
import {
  PRIORITY_STYLES,
  TASK_COLUMNS,
  type Task,
  type TaskStatus,
} from "@/lib/types";

export default function TasksPage() {
  const [configured, setConfigured] = useState(true);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) {
      setConfigured(false);
      return;
    }
    supabase
      .from("tasks")
      .select("*")
      .order("created_at", { ascending: false })
      .then(({ data }) => {
        setTasks((data as Task[]) ?? []);
        setLoading(false);
      });
  }, []);

  async function move(task: Task, status: TaskStatus) {
    const prev = task.status;
    setTasks((cur) => cur.map((t) => (t.id === task.id ? { ...t, status } : t)));
    const supabase = getSupabase();
    if (!supabase) return;
    const { error } = await supabase.from("tasks").update({ status }).eq("id", task.id);
    if (error) {
      setTasks((cur) => cur.map((t) => (t.id === task.id ? { ...t, status: prev } : t)));
      toast(`Couldn't move task: ${error.message}`, "error");
    } else {
      toast(`Task moved to ${status.replace(/_/g, " ")}`);
    }
  }

  return (
    <div>
      <PageHeader
        title="Tasks"
        subtitle="Actionable work generated from obligations, with suggested owners and deadlines"
      />
      {!configured && <DemoBanner />}

      {loading ? (
        <TableSkeleton rows={8} />
      ) : (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {TASK_COLUMNS.map((col) => {
          const items = tasks.filter((t) => t.status === col.key);
          return (
            <div key={col.key} className="flex flex-col">
              <div className="mb-2 flex items-center justify-between px-1">
                <span className="text-sm font-semibold text-slate-700">{col.label}</span>
                <span className="rounded-full bg-slate-200 px-2 text-xs text-slate-600">
                  {items.length}
                </span>
              </div>
              <div className="flex flex-col gap-2">
                {items.map((t) => (
                  <div key={t.id} className="card p-3">
                    <div className="text-sm font-medium text-slate-800">{t.title}</div>
                    {t.description && (
                      <div className="mt-1 line-clamp-2 text-xs text-[var(--muted)]">
                        {t.description}
                      </div>
                    )}
                    <div className="mt-2 flex items-center justify-between">
                      <Badge className={PRIORITY_STYLES[t.priority]}>{t.priority}</Badge>
                      {t.due_date && (
                        <span className="text-[11px] text-[var(--muted)]">
                          due {new Date(t.due_date).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    {t.owner && (
                      <div className="mt-1 text-[11px] text-[var(--muted)]">Owner: {t.owner}</div>
                    )}
                    <select
                      value={t.status}
                      onChange={(e) => move(t, e.target.value as TaskStatus)}
                      className="mt-2 w-full rounded-md border border-[var(--border)] bg-white px-2 py-1 text-xs text-slate-600"
                    >
                      {TASK_COLUMNS.map((c) => (
                        <option key={c.key} value={c.key}>
                          {c.label}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
                {items.length === 0 && (
                  <div className="rounded-lg border border-dashed border-[var(--border)] py-6 text-center text-xs text-[var(--muted)]">
                    Nothing here
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
      )}
    </div>
  );
}
