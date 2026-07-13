"""Public contact endpoint behind the marketing site's Book-a-demo /
Talk-to-sales form. Persists every submission and emails the ops inbox when
Resend is configured; never fails the visitor on a notification hiccup."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from policyai_extraction.notifications import is_configured, send_email
from policyai_graph.models_app import DemoRequest
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_api.deps import get_session

router = APIRouter(prefix="/contact", tags=["contact"])


class ContactRequest(BaseModel):
    intent: str = Field(default="demo", pattern="^(demo|sales)$")
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=160)
    company: str = Field(min_length=2, max_length=160)
    segment: str | None = Field(default=None, max_length=32)
    phone: str | None = Field(default=None, max_length=32)
    message: str | None = Field(default=None, max_length=2000)
    # Honeypot: real users never fill this; bots do. Filled -> silently accept.
    website: str | None = None


class ContactResponse(BaseModel):
    ok: bool


@router.post("", response_model=ContactResponse)
async def submit_contact(
    req: ContactRequest,
    session: AsyncSession = Depends(get_session),
) -> ContactResponse:
    if req.website:  # honeypot tripped; pretend success, store nothing
        return ContactResponse(ok=True)

    session.add(
        DemoRequest(
            intent=req.intent,
            name=req.name.strip(),
            email=str(req.email),
            company=req.company.strip(),
            segment=req.segment,
            phone=req.phone,
            message=(req.message or "").strip() or None,
        )
    )
    await session.commit()

    if is_configured():
        kind = "Demo request" if req.intent == "demo" else "Sales enquiry"
        await send_email(
            f"PolicyAI {kind}: {req.company}",
            f"<p><b>{req.name}</b> ({req.email}) at <b>{req.company}</b>"
            f"{f' · {req.segment}' if req.segment else ''}"
            f"{f' · {req.phone}' if req.phone else ''}</p>"
            f"<p>{req.message or '(no message)'}</p>",
        )
    return ContactResponse(ok=True)
