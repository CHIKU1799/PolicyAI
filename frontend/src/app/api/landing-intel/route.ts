import { NextResponse } from "next/server";

/**
 * Server-side proxy for the worker's public landing intel (/public/intel).
 * The band on the marketing landing fetches this instead of the worker
 * directly, so the page works same-origin (no CORS), the worker URL stays
 * out of the visitor's network tab, and one cached response serves every
 * visitor for five minutes. On any failure the client keeps its built-in
 * static snapshot, so the landing never looks broken.
 */

export const runtime = "nodejs";
// Deliberately a dynamic route: caching lives on the inner fetch (below),
// which only ever caches successful worker responses, so a failed first hit
// after a deploy must not pin an error for five minutes.
export const dynamic = "force-dynamic";

export async function GET() {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${base}/public/intel`, {
      next: { revalidate: 300 },
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) throw new Error(`worker responded ${res.status}`);
    const data = await res.json();
    return NextResponse.json(data, {
      headers: { "Cache-Control": "public, max-age=60, s-maxage=300" },
    });
  } catch {
    return NextResponse.json({ error: "intel unavailable" }, { status: 503 });
  }
}
