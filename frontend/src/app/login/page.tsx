"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ScanLine } from "lucide-react";
import { getSupabase } from "@/lib/supabase";
import { ButtonSpinner } from "@/components/Loading";

/** The features cycled by the animated showcase panel. */
const FEATURES = [
  {
    tag: "01 · MONITOR",
    title: "Horizon scanning",
    body: "RBI, SEBI, IRDAI and more, monitored continuously with severity-scored alerts.",
    stat: ["1,000+", "regulations in the graph"],
  },
  {
    tag: "02 · STRUCTURE",
    title: "Structured obligations",
    body: "Every circular becomes discrete, trackable obligations mapped to your policies and owners.",
    stat: ["11,000+", "requirements extracted"],
  },
  {
    tag: "03 · ASSESS",
    title: "Gap analysis",
    body: "Your own policies diffed against the rules, with the exact passage as citable evidence.",
    stat: ["4-state", "coverage per requirement"],
  },
  {
    tag: "04 · TEST",
    title: "Controls testing",
    body: "Pass-rate trends and alerts the moment a control fails, not at the next audit.",
    stat: ["Real-time", "failure alerts"],
  },
  {
    tag: "COPILOT",
    title: "An analyst that reads every rule",
    body: "Grounded answers with citations, and impact assessments drafted for your review.",
    stat: ["30 sec", "to a drafted impact assessment"],
  },
];

function Showcase() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((x) => (x + 1) % FEATURES.length), 4200);
    return () => clearInterval(t);
  }, []);
  const f = FEATURES[i];
  return (
    <div
      className="pa-show relative hidden min-h-full flex-col justify-between overflow-hidden p-10 lg:flex"
      style={{
        background:
          "radial-gradient(ellipse 90% 70% at 20% 110%, rgba(46,107,247,.4), transparent 60%), linear-gradient(155deg, #23204A, #101A38 65%)",
      }}
    >
      {/* ambient orbit rings + dust */}
      <div className="pa-ring2" style={{ width: 560, height: 560, right: -180, top: -180 }} aria-hidden />
      <div className="pa-ring2" style={{ width: 380, height: 380, right: -90, top: -90, opacity: 0.5 }} aria-hidden />
      <div className="pa-dust2" aria-hidden />

      <Link href="/" className="relative z-10 flex items-center gap-2 no-underline">
        <span
          className="flex h-8 w-8 items-center justify-center rounded-lg text-white"
          style={{ background: "linear-gradient(135deg,#2E6BF7,#1746D6)" }}
        >
          <ScanLine size={17} />
        </span>
        <span className="text-[17px] font-extrabold tracking-tight text-white">
          Policy<span style={{ color: "#7EA4FF" }}>AI</span>
        </span>
      </Link>

      <div className="relative z-10">
        <h2
          className="max-w-md text-[34px] font-medium leading-[1.15] text-white"
          style={{ fontFamily: "var(--font-serif), serif" }}
        >
          The compliance platform that turns regulatory change into{" "}
          <em style={{ color: "#7EA4FF" }}>action.</em>
        </h2>

        {/* cycling feature card */}
        <div key={i} className="pa-feature mt-8 max-w-sm rounded-2xl border p-5"
          style={{ background: "rgba(23,28,58,.72)", borderColor: "rgba(126,164,255,.28)", backdropFilter: "blur(6px)" }}>
          <div className="text-[10px] font-bold uppercase tracking-[.12em]" style={{ color: "#7EA4FF" }}>
            {f.tag}
          </div>
          <div className="mt-1.5 text-[18px] font-semibold text-white">{f.title}</div>
          <p className="mt-1.5 text-[13px] leading-relaxed" style={{ color: "#9FA6C8" }}>
            {f.body}
          </p>
          <div className="mt-4 flex items-baseline gap-2 border-t pt-3" style={{ borderColor: "rgba(126,164,255,.18)" }}>
            <span className="text-[24px] font-medium text-white" style={{ fontFamily: "var(--font-serif), serif" }}>
              {f.stat[0]}
            </span>
            <span className="text-[11.5px]" style={{ color: "#9FA6C8" }}>
              {f.stat[1]}
            </span>
          </div>
        </div>

        {/* progress dots */}
        <div className="mt-5 flex gap-2">
          {FEATURES.map((_, j) => (
            <button
              key={j}
              onClick={() => setI(j)}
              aria-label={`Show feature ${j + 1}`}
              className="h-1.5 rounded-full transition-all"
              style={{
                width: j === i ? 22 : 8,
                background: j === i ? "#7EA4FF" : "rgba(126,164,255,.3)",
              }}
            />
          ))}
        </div>
      </div>

      <div className="relative z-10 text-[11.5px]" style={{ color: "#8B93B8" }}>
        Secure by design · Org-isolated data · Made for Indian BFSI
      </div>

      <style jsx global>{`
        .pa-ring2 {
          position: absolute;
          border: 1px solid rgba(126, 164, 255, 0.18);
          border-radius: 50%;
          animation: pa-spin2 40s linear infinite;
        }
        .pa-ring2::after {
          content: "";
          position: absolute;
          top: -4px;
          left: 50%;
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #2e6bf7;
          box-shadow: 0 0 14px 3px rgba(46, 107, 247, 0.65);
        }
        .pa-dust2 {
          position: absolute;
          inset: 0;
          background-image: radial-gradient(1px 1px at 15% 25%, rgba(255, 255, 255, 0.45), transparent),
            radial-gradient(1.5px 1.5px at 75% 45%, rgba(126, 164, 255, 0.45), transparent),
            radial-gradient(1px 1px at 40% 80%, rgba(255, 255, 255, 0.3), transparent),
            radial-gradient(1.5px 1.5px at 88% 15%, rgba(126, 164, 255, 0.35), transparent);
          animation: pa-drift2 16s ease-in-out infinite alternate;
        }
        .pa-feature {
          animation: pa-rise 0.55s cubic-bezier(0.22, 1, 0.36, 1);
        }
        @keyframes pa-rise {
          from {
            opacity: 0;
            transform: translateY(14px) scale(0.985);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        @keyframes pa-spin2 {
          to {
            transform: rotate(360deg);
          }
        }
        @keyframes pa-drift2 {
          to {
            transform: translateY(-12px);
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .pa-ring2,
          .pa-dust2,
          .pa-feature {
            animation: none;
          }
        }
      `}</style>
    </div>
  );
}

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
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]" style={{ background: "#F5F4F2" }}>
      <Showcase />

      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          {/* mobile-only brand */}
          <Link href="/" className="mb-8 flex items-center gap-2 no-underline lg:hidden">
            <span
              className="flex h-9 w-9 items-center justify-center rounded-lg text-white"
              style={{ background: "linear-gradient(135deg,#2E6BF7,#1746D6)" }}
            >
              <ScanLine size={20} />
            </span>
            <span className="text-[18px] font-extrabold tracking-tight" style={{ color: "#15254E" }}>
              Policy<span style={{ color: "#1E5EF6" }}>AI</span>
            </span>
          </Link>

          <h1
            className="text-[30px] font-medium leading-snug"
            style={{ fontFamily: "var(--font-serif), serif", color: "#15254E" }}
          >
            {mode === "signin" ? "Welcome back" : "Create your workspace"}
          </h1>
          <p className="mb-6 mt-1.5 text-sm" style={{ color: "#71757E" }}>
            {mode === "signin"
              ? "Access your firm's compliance workspace."
              : "Your firm gets its own isolated workspace, provisioned instantly."}
          </p>

          <form onSubmit={submit} className="flex flex-col gap-3">
            {mode === "signup" && (
              <input
                type="text"
                required
                placeholder="Company name (e.g. Acme Finance)"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                className="rounded-xl border bg-white px-3.5 py-3 text-sm outline-none transition-shadow focus:border-[#1E5EF6] focus:shadow-[0_0_0_3px_rgba(46,107,247,.15)]"
                style={{ borderColor: "#E2E1DC" }}
              />
            )}
            <input
              type="email"
              required
              placeholder="you@firm.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-xl border bg-white px-3.5 py-3 text-sm outline-none transition-shadow focus:border-[#1E5EF6] focus:shadow-[0_0_0_3px_rgba(46,107,247,.15)]"
              style={{ borderColor: "#E2E1DC" }}
            />
            <input
              type="password"
              required
              minLength={6}
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-xl border bg-white px-3.5 py-3 text-sm outline-none transition-shadow focus:border-[#1E5EF6] focus:shadow-[0_0_0_3px_rgba(46,107,247,.15)]"
              style={{ borderColor: "#E2E1DC" }}
            />
            <button
              type="submit"
              disabled={busy}
              className="mt-1 flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold text-white transition-transform active:scale-[.99] disabled:opacity-60"
              style={{
                background: "linear-gradient(135deg,#2E6BF7,#1746D6)",
                boxShadow: "0 2px 10px rgba(23,70,214,.35)",
              }}
            >
              {busy && <ButtonSpinner />}
              {busy
                ? mode === "signin"
                  ? "Signing in…"
                  : "Provisioning your workspace…"
                : mode === "signin"
                  ? "Sign in"
                  : "Create account"}
            </button>
          </form>

          {msg && (
            <div
              className="mt-3 rounded-lg border px-3 py-2 text-xs"
              style={{ borderColor: "#F0E3C8", background: "#FBF6EA", color: "#8A6116" }}
            >
              {msg}
            </div>
          )}

          <button
            onClick={() => {
              setMode(mode === "signin" ? "signup" : "signin");
              setMsg(null);
            }}
            className="mt-5 text-xs font-medium hover:underline"
            style={{ color: "#1746D6" }}
          >
            {mode === "signin" ? "Need an account? Sign up" : "Have an account? Sign in"}
          </button>

          <p className="mt-8 text-[11px]" style={{ color: "#9A9DA4" }}>
            By continuing you agree to the early-access terms. Questions?{" "}
            <Link href="/contact?intent=sales" className="underline" style={{ color: "#71757E" }}>
              Talk to us
            </Link>
            .
          </p>
        </div>
      </div>
    </div>
  );
}
