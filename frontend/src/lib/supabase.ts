"use client";

import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

let _client: SupabaseClient | null = null;

/**
 * Browser Supabase client. Returns null when env vars are absent so the UI can
 * render demo/empty states instead of crashing during local setup.
 */
export function getSupabase(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return null;
  if (!_client) _client = createBrowserClient(url, key);
  return _client;
}

export const KB_BUCKET =
  process.env.NEXT_PUBLIC_SUPABASE_KB_BUCKET ?? "company-documents";

export const WORKER_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * fetch() against the worker with the caller's Supabase access token attached,
 * so the worker scopes every request to the caller's own org. Falls back to an
 * anonymous call (demo org) when there is no session.
 */
export async function workerFetch(path: string, init: RequestInit = {}): Promise<Response> {
  // A deployed build that still points at localhost means NEXT_PUBLIC_API_URL
  // was missing at build time. Fail with the cause instead of a silent
  // "Failed to fetch" against the visitor's own machine.
  if (
    typeof window !== "undefined" &&
    !["localhost", "127.0.0.1"].includes(window.location.hostname) &&
    /localhost|127\.0\.0\.1/.test(WORKER_URL)
  ) {
    throw new Error(
      "worker URL not configured: set NEXT_PUBLIC_API_URL on the web app and rebuild",
    );
  }
  const headers = new Headers(init.headers);
  const supabase = getSupabase();
  if (supabase) {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (session) headers.set("Authorization", `Bearer ${session.access_token}`);
  }
  return fetch(`${WORKER_URL}${path}`, { ...init, headers });
}

// Cached per session, like useOrgRole: the org never changes mid-session.
let _orgId: string | null | undefined;

/**
 * The caller's org id (first membership), for stamping org_id on rows the
 * browser inserts directly (controls, control tests, obligation links). RLS
 * rejects inserts whose org_id is not one of the caller's orgs.
 */
export async function getOrgId(): Promise<string | null> {
  if (_orgId !== undefined) return _orgId;
  const supabase = getSupabase();
  if (!supabase) return (_orgId = null);
  const { data } = await supabase.auth.getUser();
  const uid = data.user?.id;
  if (!uid) return (_orgId = null);
  const { data: rows } = await supabase
    .from("memberships")
    .select("org_id, created_at")
    .eq("user_id", uid)
    .order("created_at", { ascending: true })
    .limit(1);
  _orgId = (rows?.[0]?.org_id as string | undefined) ?? null;
  return _orgId;
}
