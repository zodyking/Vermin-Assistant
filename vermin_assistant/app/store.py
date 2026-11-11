"""Persistent panel settings."""

from __future__ import annotations

import json
from pathlib import Path

from .schedule import MODES, REPEATS
from .targets import clean_targets, default_targets

DEFAULT_SETTINGS = {
    "enabled": False,
    "mode": "both",
    "start_hour": 20,
    "end_hour": 7,
    "repeat": "continuous",
    "volume": 0.35,
    "players": [],
    "targets": default_targets(),
}


def clamp_hour(value: object, fallback: int) -> int:
    try:
        hour = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback
    if 0 <= hour <= 23:
        return hour
    return fallback


def normalize(raw: object) -> dict:
    settings = dict(DEFAULT_SETTINGS)
    settings["players"] = []
    settings["targets"] = default_targets()
    if not isinstance(raw, dict):
        return settings

    settings["enabled"] = bool(raw.get("enabled", False))
    mode = raw.get("mode", "both")
    settings["mode"] = mode if mode in MODES else "both"
    settings["start_hour"] = clamp_hour(raw.get("start_hour"), 20)
    settings["end_hour"] = clamp_hour(raw.get("end_hour"), 7)
    repeat = str(raw.get("repeat", "continuous"))
    settings["repeat"] = repeat if repeat in REPEATS else "continuous"
    try:
        volume = float(raw.get("volume", 0.35))
    except (TypeError, ValueError):
        volume = 0.35
    settings["volume"] = round(min(1.0, max(0.0, volume)), 2)
    players = raw.get("players") or []
    cleaned: list[str] = []
    if isinstance(players, list):
        for player in players:
            if isinstance(player, str) and player.startswith("media_player.") and player not in cleaned:
                cleaned.append(player)
    settings["players"] = cleaned
    settings["targets"] = clean_targets(raw.get("targets"))
    return settings


def load(path: Path) -> dict:
    if not path.exists():
        return normalize(DEFAULT_SETTINGS)
    try:
        return normalize(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return normalize(DEFAULT_SETTINGS)


def save(path: Path, settings: dict) -> dict:
    normalized = normalize(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    return normalized
