"""Upper hearing limits for the pests this add-on can target.

The chirp slams into that limit, or into the highest tone the output can
actually make when the animal hears higher than the speaker.

Mouse: house mouse, about 2.3–92 kHz (Heffner hearing-range compilation).
Rat: about 0.2–76 kHz (same compilation, Rattus).
Cockroach: American cockroach cerci, insensitive above about 3 kHz
(Shaw, 1989, Journal of Economic Entomology).
Cricket: field cricket hears from about 2 kHz to at least 100 kHz
(Hoy, Pollack, and Moiseff, 1982, via Imaizumi and Pollack, 1999).
Mosquito: yellow-fever mosquito Johnston's organ, sensitive up to 2 kHz
(Cator, Arthur, Harrington, and Hoy, 2009, Science).
Moth: Indian meal moth tympana respond through the ultrasonic clicks
that reach about 80 kHz (Mankin).
"""

from __future__ import annotations

IDS = ("mouse", "rat", "cockroach", "cricket", "mosquito", "moth")

SPECS = {
    "mouse": {"upper": 92000.0},
    "rat": {"upper": 76000.0},
    "cockroach": {"upper": 3000.0},
    "cricket": {"upper": 100000.0},
    "mosquito": {"upper": 2000.0},
    "moth": {"upper": 80000.0},
}


def default_targets() -> dict:
    return {
        "mouse": {"enabled": True, "level": 80},
        "rat": {"enabled": True, "level": 100},
        "cockroach": {"enabled": False, "level": 70},
        "cricket": {"enabled": False, "level": 70},
        "mosquito": {"enabled": False, "level": 70},
        "moth": {"enabled": False, "level": 70},
    }


def clean_targets(raw: object) -> dict:
    targets = default_targets()
    if not isinstance(raw, dict):
        return targets
    for name in IDS:
        item = raw.get(name)
        if not isinstance(item, dict):
            continue
        targets[name]["enabled"] = bool(item.get("enabled", targets[name]["enabled"]))
        try:
            level = int(round(float(item.get("level", targets[name]["level"]))))
        except (TypeError, ValueError):
            level = targets[name]["level"]
        targets[name]["level"] = max(0, min(100, level))
    return targets


def playback_band(upper: float, rate: int) -> tuple[float, float]:
    high = min(upper, rate * 0.45)
    low = max(80.0, high * 0.28)
    return low, high


def active_targets(settings: dict | None, rate: int = 48000) -> list[dict]:
    raw = settings.get("targets") if isinstance(settings, dict) else None
    cleaned = clean_targets(raw)
    chosen = []
    for name in IDS:
        if cleaned[name]["enabled"] and cleaned[name]["level"] > 0:
            low, high = playback_band(SPECS[name]["upper"], rate)
            chosen.append(
                {
                    "id": name,
                    "level": cleaned[name]["level"],
                    "upper": SPECS[name]["upper"],
                    "low": low,
                    "high": high,
                    "center": high,
                }
            )
    return chosen


def signature(settings: dict | None) -> str:
    chosen = active_targets(settings)
    if not chosen:
        return "none"
    return "|".join(f"{item['id']}:{item['level']}" for item in chosen)
