from unittest.mock import AsyncMock

from app.services.paginator import EventsPaginator


async def test_paginator_yields_all_events() -> None:
    client = AsyncMock()
    client.fetch_events_page.return_value = {
        "next": "http://host/api/events/?cursor=abc",
        "results": [{"id": "1"}, {"id": "2"}],
    }
    client.fetch_events_by_url.side_effect = [
        {
            "next": "http://host/api/events/?cursor=def",
            "results": [{"id": "3"}],
        },
        {
            "next": None,
            "results": [{"id": "4"}],
        },
    ]

    paginator = EventsPaginator(client, changed_at="2000-01-01")
    ids = [event["id"] async for event in paginator]

    assert ids == ["1", "2", "3", "4"]
    client.fetch_events_page.assert_awaited_once_with("2000-01-01")
    assert client.fetch_events_by_url.await_count == 2


async def test_paginator_stops_on_first_page_when_no_next() -> None:
    client = AsyncMock()
    client.fetch_events_page.return_value = {
        "next": None,
        "results": [{"id": "only"}],
    }

    paginator = EventsPaginator(client, changed_at="2000-01-01")
    ids = [event["id"] async for event in paginator]

    assert ids == ["only"]
    client.fetch_events_by_url.assert_not_awaited()


async def test_paginator_respects_max_pages() -> None:
    client = AsyncMock()
    client.fetch_events_page.return_value = {
        "next": "http://host/api/events/?cursor=x",
        "results": [{"id": "1"}],
    }
    client.fetch_events_by_url.return_value = {
        "next": "http://host/api/events/?cursor=y",
        "results": [{"id": "2"}],
    }

    paginator = EventsPaginator(client, changed_at="2000-01-01", max_pages=2)
    ids = [event["id"] async for event in paginator]

    assert ids == ["1", "2"]
    assert client.fetch_events_by_url.await_count == 1


async def test_paginator_handles_empty_first_page() -> None:
    client = AsyncMock()
    client.fetch_events_page.return_value = {"next": None, "results": []}

    paginator = EventsPaginator(client, changed_at="2000-01-01")
    ids = [event["id"] async for event in paginator]

    assert ids == []
