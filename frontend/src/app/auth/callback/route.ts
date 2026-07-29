import { createServerClient, type CookieOptions } from "@supabase/ssr";
import type { EmailOtpType } from "@supabase/supabase-js";
import { cookies } from "next/headers";
import { NextResponse, type NextRequest } from "next/server";

export const dynamic = "force-dynamic";

/**
 * Lands every Supabase Auth email link (confirm signup, magic link, recovery,
 * invite). Handles both link styles:
 *   - PKCE `?code=` from the default {{ .ConfirmationURL }} template
 *   - `?token_hash=&type=` from a token-hash template
 * On success the session is written to cookies and the user goes straight to
 * the app. A failed PKCE exchange (link opened in a different browser than the
 * signup) still means the email WAS confirmed server-side, so we send the user
 * to /login with a "confirmed, sign in" notice instead of an error.
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const tokenHash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const next = searchParams.get("next") ?? "/dashboard";
  const errorDescription = searchParams.get("error_description");

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) {
    return NextResponse.redirect(`${origin}/login?error=Supabase is not configured`);
  }

  // Supabase redirected here with an error (expired/used link, etc.).
  if (errorDescription) {
    return NextResponse.redirect(
      `${origin}/login?error=${encodeURIComponent(errorDescription)}`,
    );
  }

  const cookieStore = cookies();
  const supabase = createServerClient(url, key, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
        cookiesToSet.forEach(({ name, value, options }) =>
          cookieStore.set(name, value, options),
        );
      },
    },
  });

  if (code) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) return NextResponse.redirect(`${origin}${next}`);
    // The verify endpoint already confirmed the email before redirecting with
    // a code; only the browser-bound PKCE exchange failed. Sign-in now works.
    return NextResponse.redirect(
      `${origin}/login?notice=${encodeURIComponent(
        "Email confirmed. Please sign in.",
      )}`,
    );
  }

  if (tokenHash && type) {
    const { error } = await supabase.auth.verifyOtp({ type, token_hash: tokenHash });
    if (!error) return NextResponse.redirect(`${origin}${next}`);
    return NextResponse.redirect(
      `${origin}/login?error=${encodeURIComponent(
        "Confirmation link is invalid or has expired. Sign in or resend the email.",
      )}`,
    );
  }

  return NextResponse.redirect(`${origin}/login`);
}
