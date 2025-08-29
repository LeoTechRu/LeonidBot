from datetime import datetime
from zoneinfo import ZoneInfo
from dateutil.rrule import rrulestr


def test_rrule_handles_dst_transition():
    tz = ZoneInfo("Europe/Berlin")
    start = datetime(2024, 3, 30, 12, 0, tzinfo=tz)
    rule = "FREQ=DAILY;COUNT=3"
    r = rrulestr(rule, dtstart=start)
    occ = list(r)
    assert occ[0].utcoffset().total_seconds() == 3600
    assert occ[1].utcoffset().total_seconds() == 7200
    assert occ[1] - occ[0] == occ[2] - occ[1]
