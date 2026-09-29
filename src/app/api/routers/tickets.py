from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.tickets import (
    TicketCancelResponse,
    TicketCreateRequest,
    TicketCreateResponse,
)
from app.core.config import settings
from app.db.session import get_session
from app.services.events_provider import EventsProviderClient
from app.services.tickets import CancelTicketUseCase, CreateTicketUseCase

router = APIRouter(tags=["tickets"])


def _client() -> EventsProviderClient:
    return EventsProviderClient(
        base_url=settings.events_provider_url,
        api_key=settings.events_provider_api_key,
    )


@router.post(
    "/tickets",
    response_model=TicketCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ticket(
    payload: TicketCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> TicketCreateResponse:
    usecase = CreateTicketUseCase(_client(), session)
    ticket_id = await usecase.do(
        event_id=payload.event_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        seat=payload.seat,
    )
    return TicketCreateResponse(ticket_id=ticket_id)


@router.delete("/tickets/{ticket_id}", response_model=TicketCancelResponse)
async def cancel_ticket(
    ticket_id: str,
    session: AsyncSession = Depends(get_session),
) -> TicketCancelResponse:
    usecase = CancelTicketUseCase(_client(), session)
    await usecase.do(ticket_id)
    return TicketCancelResponse(success=True)
