from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PlaceShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    city: str
    address: str


class PlaceDetail(PlaceShort):
    seats_pattern: str


class EventShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    place: PlaceShort
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int


class EventDetail(EventShort):
    place: PlaceDetail


class SeatsResponse(BaseModel):
    event_id: UUID
    available_seats: list[str]
