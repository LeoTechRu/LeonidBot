import pytest

from core.services.google_sync import FakeGoogleCalendar, GoogleCalendarGone


def test_google_initial_and_incremental_sync():
    cal = FakeGoogleCalendar()
    cal.add_event("e1")
    events, token = cal.initial_sync()
    assert events == ["e1"]
    cal.add_event("e2")
    delta, _ = cal.incremental_sync(token)
    assert delta == ["e2"]


def test_google_sync_410_gone():
    cal = FakeGoogleCalendar()
    cal.add_event("e1")
    _, token = cal.initial_sync()
    with pytest.raises(GoogleCalendarGone):
        cal.incremental_sync("bad")
    # After handling 410 we perform fresh initial sync
    events, token = cal.initial_sync()
    assert "e1" in events
