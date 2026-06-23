"""Optional email alerts via Resend.

Strictly opt-in: a no-op unless ``RESEND_API_KEY`` and ``ALERT_EMAIL_TO`` are set,
so it never breaks the worker. Scoped by default to high-value, low-volume alerts
(new obligations + scan failures) via ``ALERT_EMAIL_KINDS`` — a 150-document
backfill shouldn't send 150 emails, so NEW_REGULATION is excluded by default.

Env vars:
  RESEND_API_KEY      — from resend.com
  ALERT_EMAIL_TO      — comma-separated recipients
  ALERT_EMAIL_FROM    — verified sender (default: PolicyAI <onboarding@resend.dev>,
                        which Resend only delivers to your own account email)
  ALERT_EMAIL_KINDS   — comma-separated alert kinds that trigger email
                        (default: new_obligation,scan_failed)
"""

from __future__ import annotations

import os

import httpx

_DEFAULT_KINDS = "new_obligation,scan_failed"
_TIMEOUT = httpx.Timeout(20.0)


def is_configured() -> bool:
    return bool(os.getenv("RESEND_API_KEY") and os.getenv("ALERT_EMAIL_TO"))


def _email_kinds() -> set[str]:
    raw = os.getenv("ALERT_EMAIL_KINDS") or _DEFAULT_KINDS
    return {k.strip() for k in raw.split(",") if k.strip()}


def should_email(kind: str) -> bool:
    return is_configured() and kind in _email_kinds()


async def send_email(subject: str, html: str) -> bool:
    key = os.getenv("RESEND_API_KEY")
    to = os.getenv("ALERT_EMAIL_TO")
    sender = os.getenv("ALERT_EMAIL_FROM", "PolicyAI <onboarding@resend.dev>")
    if not key or not to:
        return False
    recipients = [t.strip() for t in to.split(",") if t.strip()]
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {key}"},
                json={"from": sender, "to": recipients, "subject": subject, "html": html},
            )
            resp.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001 - notifications must never break the caller
        print(f"[notifications] email failed: {exc}")
        return False


async def notify_alert(kind: str, message: str, *, detail: str | None = None) -> bool:
    """Email an alert if its kind is enabled. Returns False (no-op) otherwise."""
    if not should_email(kind):
        return False
    html = f"<p style='font-size:15px'>{message}</p>"
    if detail:
        html += f"<p style='color:#475569;font-size:13px'>{detail}</p>"
    html += (
        "<hr style='border:none;border-top:1px solid #e2e8f0'>"
        "<p style='font-size:12px;color:#94a3b8'>PolicyAI — continuous regulatory monitoring "
        "for India</p>"
    )
    subject = f"[PolicyAI] {message[:120]}"
    return await send_email(subject, html)
