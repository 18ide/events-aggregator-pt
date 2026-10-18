from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TicketCreateRequest(BaseModel):
    event_id: UUID
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    seat: str = Field(min_length=1, max_length=32)
    idempotency_key: str | None = Field(
        default=None,
        max_length=255,
        description=(
            "Optional idempotency key. If the same key was used before with the "
            "same request data (event_id, seat, email), the original ticket is "
            "returned with HTTP 201. If the key was used with different data, "
            "HTTP 409 Conflict is returned. If omitted, every request is "
            "processed as new."
        ),
    )


class TicketCreateResponse(BaseModel):
    ticket_id: str


class TicketCancelResponse(BaseModel):
    success: bool
