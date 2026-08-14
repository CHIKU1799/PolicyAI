"""Public, unauthenticated endpoints: landing-page intel and signup.

Intel serves only global regulatory data (raw_documents, monitoring_sources)
and never org-scoped rows; TTL-cached hard (one shared payload). Signup
creates the auth user pre-confirmed via the service-role admin API, because
Supabase's built-in SMTP (about 2 mails an hour) silently drops confirmation
emails and locks new users out. Both are rate limited per IP."""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from policyai_extraction.notifications import send_email_to
from policyai_graph.models import RawDocument
from policyai_graph.models_app import MonitoringSource
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_api.deps import get_session
from policyai_api.ratelimit import rate_limited
from policyai_api.ttl_cache import ttl_cache

router = APIRouter(prefix="/public", tags=["public"])

FEED_LIMIT = 9
REGULATOR_LIMIT = 6

# Portal titles often carry download-page debris: attachment size suffixes
# ("… .pdf 829 KB") and whitespace runs from scraped markup.
_TITLE_JUNK = re.compile(r"\s*\S+\.pdf\s+\d+(\.\d+)?\s*[KM]B\s*$", re.IGNORECASE)


def _clean_title(title: str) -> str:
    return _TITLE_JUNK.sub("", " ".join(title.split())).strip()


class IntelDoc(BaseModel):
    source: str
    title: str
    url: str
    published: str | None


class RegulatorCount(BaseModel):
    source: str
    count: int


class IntelStats(BaseModel):
    total_documents: int
    documents_30d: int
    regulators_live: int
    sources_enabled: int
    last_synced: str | None


class IntelResponse(BaseModel):
    stats: IntelStats
    latest: list[IntelDoc]
    by_regulator: list[RegulatorCount]


@ttl_cache(seconds=300, max_entries=4)
async def _intel_payload(_key: str, session: AsyncSession) -> IntelResponse:
    total = await session.scalar(select(func.count()).select_from(RawDocument)) or 0
    cutoff = datetime.now(UTC) - timedelta(days=30)
    recent = (
        await session.scalar(
            select(func.count()).select_from(RawDocument).where(RawDocument.fetched_at >= cutoff)
        )
        or 0
    )

    src_rows = (
        await session.execute(
            select(
                MonitoringSource.regulator_key,
                func.count().filter(MonitoringSource.enabled),
                func.max(MonitoringSource.last_scanned_at),
            ).group_by(MonitoringSource.regulator_key)
        )
    ).all()
    regulators_live = sum(1 for _, enabled, _ts in src_rows if enabled)
    sources_enabled = sum(enabled for _, enabled, _ts in src_rows)
    scanned = [ts for _, _e, ts in src_rows if ts is not None]
    last_synced = max(scanned).isoformat() if scanned else None

    latest_rows = (
        await session.execute(
            select(
                RawDocument.source,
                RawDocument.title,
                RawDocument.source_url,
                RawDocument.published_date,
            )
            # A public-facing feed: drop rows scrapers left with junk titles
            # ("NOTIFICATIONS") or future effective dates that would pin
            # themselves to the top of a recency sort.
            .where(
                RawDocument.published_date.is_not(None),
                RawDocument.published_date <= func.current_date(),
                func.length(RawDocument.title) >= 20,
            )
            .order_by(
                RawDocument.published_date.desc(),
                RawDocument.fetched_at.desc(),
            )
            .limit(FEED_LIMIT)
        )
    ).all()

    by_reg_rows = (
        await session.execute(
            select(RawDocument.source, func.count())
            .group_by(RawDocument.source)
            .order_by(func.count().desc())
            .limit(REGULATOR_LIMIT)
        )
    ).all()

    return IntelResponse(
        stats=IntelStats(
            total_documents=total,
            documents_30d=recent,
            regulators_live=regulators_live,
            sources_enabled=sources_enabled,
            last_synced=last_synced,
        ),
        latest=[
            IntelDoc(
                source=source,
                title=_clean_title(title),
                url=url,
                published=published.isoformat() if published else None,
            )
            for source, title, url, published in latest_rows
        ],
        by_regulator=[RegulatorCount(source=s, count=c) for s, c in by_reg_rows],
    )


@router.get(
    "/intel",
    response_model=IntelResponse,
    dependencies=[Depends(rate_limited("public_intel"))],
)
async def landing_intel(session: AsyncSession = Depends(get_session)) -> IntelResponse:
    return await _intel_payload("intel", session)


def _web_base() -> str:
    """Best guess at the web app URL for links in transactional emails."""
    origins = os.getenv("FRONTEND_ORIGINS", "")
    for origin in origins.split(","):
        origin = origin.strip().rstrip("/")
        if origin.startswith("https://"):
            return origin
    return "https://policyai-web-rgry0.sevalla.app"


async def _send_welcome(email: str, company: str) -> None:
    """Best-effort welcome mail; a no-op until RESEND_API_KEY is configured,
    and delivery-limited until a sender domain is verified in Resend."""
    base = _web_base()
    who = company or "your firm"
    await send_email_to(
        email,
        "Welcome to PolicyAI",
        (
            f"<p style='font-size:15px'>Your PolicyAI workspace for <b>{who}</b> is ready.</p>"
            f"<p style='font-size:14px'>Sign in at <a href='{base}/login'>{base}/login</a> "
            "to see your compliance dashboard, obligations and tasks.</p>"
            "<hr style='border:none;border-top:1px solid #e2e8f0'>"
            "<p style='font-size:12px;color:#94a3b8'>PolicyAI, continuous regulatory "
            "monitoring for India</p>"
        ),
    )


class SignupRequest(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=160)
    # Supabase (bcrypt) truncates at 72 bytes, so cap the input there too.
    password: str = Field(min_length=8, max_length=72)
    company: str | None = Field(default=None, max_length=120)


class SignupResponse(BaseModel):
    ok: bool


# Signup without the confirmation-email dance: the account is created already
# confirmed and the client signs in with the password right away. The 0012/0014
# DB triggers still fire on the auth.users insert, so invited emails join the
# inviter's org and everyone else gets a fresh org named from company_name.
# Trade-off (deliberate, until real SMTP is configured in Supabase): the email
# address is not proven to belong to the signer-upper.
@router.post(
    "/signup",
    response_model=SignupResponse,
    dependencies=[Depends(rate_limited("signup"))],
)
async def public_signup(req: SignupRequest, background: BackgroundTasks) -> SignupResponse:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise HTTPException(status_code=501, detail="signup not configured on this worker")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{url.rstrip('/')}/auth/v1/admin/users",
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
                json={
                    "email": req.email.strip().lower(),
                    "password": req.password,
                    "email_confirm": True,
                    "user_metadata": {"company_name": (req.company or "").strip()},
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="could not reach auth service") from exc
    if resp.status_code in (200, 201):
        background.add_task(_send_welcome, req.email.strip().lower(), (req.company or "").strip())
        return SignupResponse(ok=True)
    detail = ""
    try:
        detail = str(resp.json().get("msg") or resp.json().get("message") or "")
    except ValueError:
        pass
    if resp.status_code == 422 and "registered" in detail.lower():
        raise HTTPException(status_code=409, detail="this email is already registered")
    raise HTTPException(status_code=502, detail=detail or "signup failed")
