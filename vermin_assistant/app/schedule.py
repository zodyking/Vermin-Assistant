"""Pure schedule decisions for Vermin Assistant. No I/O."""

from __future__ import annotations

from datetime import datetime, timedelta

MODES = ("hours", "away", "both")
REPEATS = ("continuous", "15", "30", "60")

REPEAT_MINUTES = {"15": 15, "30": 30, "60": 60}


def in_hour_window(hour: int, start: int, end: int) -> bool:
    """True when `hour` is inside [start, end). Equal bounds mean all day.

    Overnight windows wrap, so 20 → 7 includes 23 and 3, and excludes 12.
    """
    if not 0 <= hour <= 23 or not 0 <= start <= 23 or not 0 <= end <= 23:
        return False
    if start == end:
        return True
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def evaluate(settings: dict, presence: dict, hour: int) -> dict:
    """Return whether the deterrent should be allowed to play right now."""
    if not settings.get("enabled"):
        return {"active": False, "reason": "Off"}
    if not settings.get("players"):
        return {"active": False, "reason": "Select a speaker"}

    mode = settings.get("mode", "both")
    hours_ok = in_hour_window(hour, int(settings["start_hour"]), int(settings["end_hour"]))
    unknown = bool(presence.get("unknown"))
    someone_home = bool(presence.get("someone_home"))

    if mode == "hours":
        if not hours_ok:
            return {"active": False, "reason": "Waiting"}
        return {"active": True, "reason": "On"}

    if mode == "away":
        if unknown:
            return {"active": False, "reason": "Waiting to see who's home"}
        if someone_home:
            return {"active": False, "reason": "Someone is home"}
        return {"active": True, "reason": "On"}

    if not hours_ok:
        return {"active": False, "reason": "Waiting"}
    if unknown:
        return {"active": False, "reason": "Waiting to see who's home"}
    if someone_home:
        return {"active": False, "reason": "Someone is home"}
    return {"active": True, "reason": "On"}


def next_window_start(now: datetime, start: int, end: int) -> datetime | None:
    """Next time an hour window opens. None when the window is open or all day."""
    if in_hour_window(now.hour, start, end):
        return None
    candidate = now.replace(hour=start, minute=0, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def repeat_seconds(repeat: str, clip_seconds: float) -> float:
    if repeat == "continuous":
        return max(clip_seconds, 5) + 2
    minutes = REPEAT_MINUTES.get(repeat, 30)
    return minutes * 60


def due(last_played: datetime | None, now: datetime, repeat: str, clip_seconds: float) -> bool:
    if last_played is None:
        return True
    elapsed = (now - last_played).total_seconds()
    return elapsed >= repeat_seconds(repeat, clip_seconds)


def format_clock(when: datetime) -> str:
    hour = when.hour % 12 or 12
    suffix = "AM" if when.hour < 12 else "PM"
    return f"{hour}:{when.minute:02d} {suffix}"


def next_play_at(
    last_played: datetime | None, now: datetime, repeat: str, clip_seconds: float
) -> datetime | None:
    if last_played is None:
        return now
    nxt = last_played + timedelta(seconds=repeat_seconds(repeat, clip_seconds))
    if nxt <= now:
        return now
    return nxt
