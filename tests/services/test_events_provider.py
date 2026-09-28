import pytest
import respx
from app.services.events_provider import EventsProviderClient, EventsProviderError
from httpx import Response

BASE_URL = "http://events-provider.test"
API_KEY = "test-key"


@pytest.fixture
def client() -> EventsProviderClient:
    return EventsProviderClient(base_url=BASE_URL, api_key=API_KEY)


@respx.mock
async def test_fetch_events_page_sends_api_key_and_changed_at(client: EventsProviderClient) -> None:
    route = respx.get(f"{BASE_URL}/api/events/").mock(
        return_value=Response(
            200,
            json={"next": None, "previous": None, "results": [{"id": "1"}]},
        )
    )

    async with client:
        page = await client.fetch_events_page("2000-01-01")

    assert page["results"] == [{"id": "1"}]
    assert route.called
    request = route.calls.last.request
    assert request.headers["x-api-key"] == API_KEY
    assert request.url.params["changed_at"] == "2000-01-01"
    assert "cursor" not in request.url.params


@respx.mock
async def test_fetch_events_page_with_cursor(client: EventsProviderClient) -> None:
    route = respx.get(f"{BASE_URL}/api/events/").mock(
        return_value=Response(200, json={"next": None, "results": []})
    )

    async with client:
        await client.fetch_events_page("2000-01-01", cursor="abc123")

    assert route.calls.last.request.url.params["cursor"] == "abc123"


@respx.mock
async def test_fetch_events_by_url_uses_full_url(client: EventsProviderClient) -> None:
    next_url = f"{BASE_URL}/api/events/?changed_at=2000-01-01&cursor=xyz"
    respx.get(next_url).mock(
        return_value=Response(200, json={"next": None, "results": [{"id": "2"}]})
    )

    async with client:
        page = await client.fetch_events_by_url(next_url)

    assert page["results"] == [{"id": "2"}]


@respx.mock
async def test_fetch_seats(client: EventsProviderClient) -> None:
    event_id = "11111111-1111-1111-1111-111111111111"
    respx.get(f"{BASE_URL}/api/events/{event_id}/seats/").mock(
        return_value=Response(200, json={"seats": ["A1", "A2", "B5"]})
    )

    async with client:
        seats = await client.fetch_seats(event_id)

    assert seats == ["A1", "A2", "B5"]


@respx.mock
async def test_register_returns_ticket_id(client: EventsProviderClient) -> None:
    event_id = "11111111-1111-1111-1111-111111111111"
    route = respx.post(f"{BASE_URL}/api/events/{event_id}/register/").mock(
        return_value=Response(201, json={"ticket_id": "ticket-abc"})
    )

    async with client:
        ticket_id = await client.register(
            event_id,
            first_name="Иван",
            last_name="Иванов",
            email="ivan@example.com",
            seat="A15",
        )

    assert ticket_id == "ticket-abc"
    sent = route.calls.last.request
    assert sent.headers["x-api-key"] == API_KEY
    import json as _json

    body = _json.loads(sent.content)
    assert body == {
        "first_name": "Иван",
        "last_name": "Иванов",
        "email": "ivan@example.com",
        "seat": "A15",
    }


@respx.mock
async def test_unregister_calls_delete(client: EventsProviderClient) -> None:
    event_id = "11111111-1111-1111-1111-111111111111"
    route = respx.delete(f"{BASE_URL}/api/events/{event_id}/unregister/").mock(
        return_value=Response(200, json={"success": True})
    )

    async with client:
        await client.unregister(event_id, "ticket-abc")

    assert route.called


@respx.mock
async def test_error_response_raises_events_provider_error(client: EventsProviderClient) -> None:
    event_id = "11111111-1111-1111-1111-111111111111"
    respx.get(f"{BASE_URL}/api/events/{event_id}/seats/").mock(
        return_value=Response(404, json={"detail": "Event not found"})
    )

    async with client:
        with pytest.raises(EventsProviderError) as exc_info:
            await client.fetch_seats(event_id)

    assert exc_info.value.status_code == 404
    assert "Event not found" in exc_info.value.message


async def test_client_not_started_raises() -> None:
    client = EventsProviderClient(base_url=BASE_URL, api_key=API_KEY)
    with pytest.raises(RuntimeError, match="not started"):
        await client.fetch_seats("some-id")
