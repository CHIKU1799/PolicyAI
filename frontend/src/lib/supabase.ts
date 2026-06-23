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
