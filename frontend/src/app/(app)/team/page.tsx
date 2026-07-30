"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Mail, ShieldAlert, UserPlus, Users, X } from "lucide-react";
import { workerFetch } from "@/lib/supabase";
import { PageHeader, Badge } from "@/components/ui";
import { useOrgRole } from "@/lib/useOrgRole";
import { TableSkeleton } from "@/components/Loading";

interface Member {
  user_id: string;
  email: string | null;
  role: string;
  joined_at: string | null;
}

interface Invite {
  id: string;
  email: string;
  role: string;
  created_at: string | null;
}

const ROLE_STYLE: Record<string, string> = {
  admin: "bg-[#EAF0FE] text-[#2E6BF7]",
  member: "bg-slate-100 text-slate-600",
};

async function readError(resp: Response): Promise<string> {
  try {
    const body = await resp.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // fall through to the generic message
  }
  return resp.status === 403
    ? "You need org admin rights for this action."
    : `Request failed (${resp.status}).`;
}

export default function TeamPage() {
  const { role: myRole, loading: roleLoading } = useOrgRole();
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"member" | "admin">("member");
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [mResp, iResp] = await Promise.all([
        workerFetch("/org/members"),
        workerFetch("/org/invites"),
      ]);
      if (!mResp.ok) throw new Error(await readError(mResp));
      if (!iResp.ok) throw new Error(await readError(iResp));
      setMembers((await mResp.json()) as Member[]);
      setInvites((await iResp.json()) as Invite[]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!roleLoading && myRole === "admin") load();
  }, [roleLoading, myRole, load]);

  async function toggleRole(m: Member) {
    const next = m.role === "admin" ? "member" : "admin";
    setBusy(m.user_id);
    setError(null);
    try {
      const resp = await workerFetch(`/org/members/${m.user_id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: next }),
      });
      if (!resp.ok) throw new Error(await readError(resp));
      setMembers((prev) =>
        prev.map((x) => (x.user_id === m.user_id ? { ...x, role: next } : x)),
      );
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function sendInvite(e: React.FormEvent) {
    e.preventDefault();
    const email = inviteEmail.trim();
    if (!email) return;
    setBusy("invite");
    setError(null);
    setNotice(null);
    try {
      const resp = await workerFetch("/org/invites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, role: inviteRole }),
      });
      if (!resp.ok) throw new Error(await readError(resp));
      const body = (await resp.json()) as { result: string; email: string };
      setNotice(
        body.result === "member_added"
          ? `${body.email} already had an account and was added to your team.`
          : `Invite recorded for ${body.email}. They join your org when they sign up with this email.`,
      );
      setInviteEmail("");
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function cancelInvite(inv: Invite) {
    setBusy(inv.id);
    setError(null);
    try {
      const resp = await workerFetch(`/org/invites/${inv.id}`, { method: "DELETE" });
      if (!resp.ok) throw new Error(await readError(resp));
      setInvites((prev) => prev.filter((x) => x.id !== inv.id));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }

  if (roleLoading) return null;

  if (myRole !== "admin") {
    return (
      <div className="card flex flex-col items-center justify-center px-6 py-16 text-center">
        <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[#EAF0FE]">
          <ShieldAlert size={22} className="text-[#2E6BF7]" />
        </div>
        <div className="mt-3 text-sm font-semibold text-[var(--text)]">Admins only</div>
        <p className="mt-1 max-w-md text-sm text-[var(--muted)]">
          Team management is available to your organization&apos;s admins.
        </p>
        <Link href="/dashboard" className="mt-4 text-sm font-medium text-[#2E6BF7] hover:underline">
          Back to dashboard
        </Link>
      </div>
    );
  }

  const adminCount = members.filter((m) => m.role === "admin").length;

  return (
    <div>
      <PageHeader title="Team" subtitle="Invite teammates and manage their roles" />

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">
          {error}
        </div>
      )}
      {notice && (
        <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-700">
          {notice}
        </div>
      )}

      {/* invite form */}
      <form
        onSubmit={sendInvite}
        className="card mb-6 flex flex-col gap-3 p-4 sm:flex-row sm:items-center"
      >
        <div className="flex items-center gap-2 text-sm font-semibold text-[var(--text)]">
          <UserPlus size={16} className="text-[#2E6BF7]" />
          Invite a teammate
        </div>
        <input
          type="email"
          required
          value={inviteEmail}
          onChange={(e) => setInviteEmail(e.target.value)}
          placeholder="colleague@yourfirm.in"
          className="h-9 flex-1 rounded-lg border border-[var(--border)] bg-white px-3 text-sm outline-none focus:border-[#2E6BF7]"
        />
        <select
          value={inviteRole}
          onChange={(e) => setInviteRole(e.target.value as "member" | "admin")}
          className="h-9 rounded-lg border border-[var(--border)] bg-white px-2 text-sm outline-none focus:border-[#2E6BF7]"
        >
          <option value="member">Member</option>
          <option value="admin">Admin</option>
        </select>
        <button
          type="submit"
          disabled={busy === "invite"}
          className="h-9 rounded-lg bg-[#2E6BF7] px-4 text-sm font-semibold text-white hover:bg-[#2558cc] disabled:opacity-60"
        >
          {busy === "invite" ? "Sending…" : "Send invite"}
        </button>
      </form>

      {/* members table */}
      {loading ? (
        <TableSkeleton />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead className="border-b border-[var(--border)] bg-slate-50 text-left text-xs uppercase tracking-wide text-[var(--muted)]">
              <tr>
                <th className="px-4 py-3">Member</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Joined</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {members.map((m) => {
                const lastAdmin = m.role === "admin" && adminCount <= 1;
                return (
                  <tr key={m.user_id}>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 font-medium text-slate-800">
                        <Users size={15} className="text-[#2E6BF7]" />
                        {m.email ?? m.user_id}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={ROLE_STYLE[m.role] ?? "bg-slate-100 text-slate-600"}>
                        {m.role.replace(/_/g, " ")}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-[var(--muted)]">
                      {m.joined_at ? new Date(m.joined_at).toLocaleDateString() : "-"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => toggleRole(m)}
                        disabled={busy === m.user_id || lastAdmin}
                        title={
                          lastAdmin
                            ? "The last admin cannot be demoted. Promote someone else first."
                            : undefined
                        }
                        className="rounded-lg border border-[var(--border)] bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:border-[#2E6BF7] hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {m.role === "admin" ? "Make member" : "Make admin"}
                      </button>
                    </td>
                  </tr>
                );
              })}
              {members.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-10 text-center text-sm text-[var(--muted)]">
                    No members found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* pending invites */}
      <div className="mt-6">
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Pending invites
        </div>
        {invites.length === 0 ? (
          <div className="card px-4 py-6 text-center text-sm text-[var(--muted)]">
            No pending invites. Invited teammates appear here until they sign up.
          </div>
        ) : (
          <div className="card overflow-x-auto">
            <table className="w-full min-w-[480px] text-sm">
              <thead className="border-b border-[var(--border)] bg-slate-50 text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                <tr>
                  <th className="px-4 py-3">Email</th>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3">Invited</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {invites.map((inv) => (
                  <tr key={inv.id}>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 text-slate-800">
                        <Mail size={15} className="text-[var(--muted)]" />
                        {inv.email}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={ROLE_STYLE[inv.role] ?? "bg-slate-100 text-slate-600"}>
                        {inv.role}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-[var(--muted)]">
                      {inv.created_at ? new Date(inv.created_at).toLocaleDateString() : "-"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => cancelInvite(inv)}
                        disabled={busy === inv.id}
                        className="inline-flex items-center gap-1 rounded-lg border border-[var(--border)] bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:border-red-300 hover:text-red-600 disabled:opacity-50"
                      >
                        <X size={13} />
                        Cancel
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
