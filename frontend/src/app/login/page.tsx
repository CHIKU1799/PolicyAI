"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ScanLine } from "lucide-react";
import { getSupabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [company, setCompany] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const supabase = getSupabase();
    if (!supabase) {
      setMsg("Supabase isn't configured.");
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      if (mode === "signup") {
        // company_name lands in raw_user_meta_data; the DB trigger provisions a
        // fresh org named from it and makes this user its admin.
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { company_name: company.trim() } },
        });
        if (error) throw error;
        setMsg("Account created. If email confirmation is on, confirm then sign in.");
        setMode("signin");
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        router.push("/dashboard");
        router.refresh();
      }
    } catch (err) {
      setMsg((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#4b40c4] p-6">
      <div className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-xl">
        <div className="mb-6 flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#4b40c4] text-white">
            <ScanLine size={20} />
          </div>
          <div>
            <div className="text-base font-semibold text-[var(--text)]">PolicyAI</div>
            <div className="text-[11px] text-[var(--muted)]">Regulatory Intelligence</div>
          </div>
        </div>

        <h1 className="mb-1 text-lg font-semibold text-[var(--text)]">
          {mode === "signin" ? "Sign in" : "Create your account"}
        </h1>
        <p className="mb-5 text-sm text-[var(--muted)]">
          {mode === "signin"
            ? "Access your firm's compliance workspace."
            : "Start monitoring regulations for your firm."}
        </p>

        <form onSubmit={submit} className="flex flex-col gap-3">
          {mode === "signup" && (
            <input
              type="text"
              required
              placeholder="Company name (e.g. Acme Finance)"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              className="rounded-lg border border-[var(--border)] px-3 py-2.5 text-sm outline-none focus:border-[#4b40c4]"
            />
          )}
          <input
            type="email"
            required
            placeholder="you@firm.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-lg border border-[var(--border)] px-3 py-2.5 text-sm outline-none focus:border-[#4b40c4]"
          />
          <input
            type="password"
            required
            minLength={6}
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-lg border border-[var(--border)] px-3 py-2.5 text-sm outline-none focus:border-[#4b40c4]"
          />
          <button
            type="submit"
            disabled={busy}
            className="mt-1 rounded-lg bg-[#4b40c4] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#3a2fb0] disabled:opacity-60"
          >
            {busy ? "…" : mode === "signin" ? "Sign in" : "Create account"}
          </button>
        </form>

        {msg && <div className="mt-3 text-xs text-amber-700">{msg}</div>}

        <button
          onClick={() => {
            setMode(mode === "signin" ? "signup" : "signin");
            setMsg(null);
          }}
          className="mt-4 text-xs text-[#4b40c4] hover:underline"
        >
          {mode === "signin" ? "Need an account? Sign up" : "Have an account? Sign in"}
        </button>
      </div>
    </div>
  );
}
