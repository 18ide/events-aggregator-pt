from __future__ import annotations


class DomainError(Exception):
    """Base class for all business-logic errors."""

    status_code = 400
    code = "domain_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class EventNotFoundError(DomainError):
    status_code = 404
    code = "event_not_found"


class EventNotPublishedError(DomainError):
    status_code = 400
    code = "event_not_published"


class RegistrationClosedError(DomainError):
    status_code = 400
    code = "registration_closed"


class SeatNotAvailableError(DomainError):
    status_code = 400
    code = "seat_not_available"


class TicketNotFoundError(DomainError):
    status_code = 404
    code = "ticket_not_found"


class ProviderUnavailableError(DomainError):
    status_code = 502
    code = "provider_unavailable"
