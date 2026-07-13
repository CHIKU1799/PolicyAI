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
