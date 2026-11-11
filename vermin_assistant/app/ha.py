"""Home Assistant supervisor client."""

from __future__ import annotations

import json
import os
from typing import Any

import aiohttp

PLAY_MEDIA = 512
VOLUME_SET = 4

SNAPSHOT_TEMPLATE = r"""
{% set ns = namespace(rows=[]) %}
{% for s in states.media_player %}
{% set ns.rows = ns.rows + [{
  "entity_id": s.entity_id,
  "name": s.attributes.friendly_name | default(s.name, true),
  "state": s.state,
  "area": area_name(s.entity_id),
  "features": s.attributes.supported_features | default(0)
}] %}
{% endfor %}
{{ {
  "players": ns.rows,
  "zone_home": states("zone.home"),
  "person_count": states.person | list | count,
  "persons_home": states.person | selectattr("state", "eq", "home") | list | count,
  "tracker_count": states.device_tracker | list | count,
  "trackers_home": states.device_tracker | selectattr("state", "eq", "home") | list | count
} | tojson }}
"""


class HomeAssistantError(Exception):
    pass


def supports(features: Any, flag: int, name: str) -> bool:
    if isinstance(features, bool):
        return False
    if isinstance(features, int):
        return bool(features & flag)
    if isinstance(features, str):
        try:
            return bool(int(features) & flag)
        except ValueError:
            return name in features
    if isinstance(features, list):
        return flag in features or name in features
    return False


def presence_from_snapshot(snapshot: dict) -> dict:
    """Prefer zone.home, then person entities, then device trackers.

    A home zone stuck at 0 because no people exist is treated as unknown,
    so away mode does not run in a house that has no presence tracking.
    """
    zone_raw = str(snapshot.get("zone_home", "unknown"))
    person_count = int(snapshot.get("person_count") or 0)
    persons_home = int(snapshot.get("persons_home") or 0)
    tracker_count = int(snapshot.get("tracker_count") or 0)
    trackers_home = int(snapshot.get("trackers_home") or 0)

    zone_count: int | None
    try:
        zone_count = int(float(zone_raw))
    except ValueError:
        zone_count = None

    if zone_count is not None and (person_count > 0 or zone_count > 0):
        return {
            "someone_home": zone_count > 0,
            "people_home": zone_count,
            "unknown": False,
            "source": "zone.home",
        }
    if person_count > 0:
        return {
            "someone_home": persons_home > 0,
            "people_home": persons_home,
            "unknown": False,
            "source": "person",
        }
    if tracker_count > 0:
        return {
            "someone_home": trackers_home > 0,
            "people_home": trackers_home,
            "unknown": False,
            "source": "device_tracker",
        }
    return {"someone_home": False, "people_home": None, "unknown": True, "source": "unknown"}


def compatible_players(rows: list[dict]) -> tuple[list[dict], int]:
    players: list[dict] = []
    hidden = 0
    for row in rows:
        entity_id = str(row.get("entity_id") or "")
        if not entity_id.startswith("media_player."):
            continue
        features = row.get("features", 0)
        if not supports(features, PLAY_MEDIA, "PLAY_MEDIA"):
            hidden += 1
            continue
        area = row.get("area") or ""
        if area in (None, "None"):
            area = ""
        players.append(
            {
                "entity_id": entity_id,
                "name": str(row.get("name") or entity_id),
                "area": str(area),
                "state": str(row.get("state") or "unknown"),
                "supports_volume": supports(features, VOLUME_SET, "VOLUME_SET"),
            }
        )
    players.sort(key=lambda item: (item["area"].lower(), item["name"].lower(), item["entity_id"]))
    return players, hidden


class HomeAssistant:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.token = os.environ.get("SUPERVISOR_TOKEN", "")
        self.base = os.environ.get("HA_API_BASE", "http://supervisor/core/api").rstrip("/")

    @property
    def connected(self) -> bool:
        return bool(self.token)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, payload: dict | None = None) -> tuple[int, str]:
        if not self.connected:
            raise HomeAssistantError("Home Assistant is not connected")
        async with self.session.request(
            method,
            f"{self.base}{path}",
            headers=self._headers(),
            json=payload,
            timeout=aiohttp.ClientTimeout(total=20),
        ) as response:
            body = await response.text()
            return response.status, body

    async def timezone_name(self) -> str:
        status, body = await self._request("GET", "/config")
        if status >= 400:
            raise HomeAssistantError(body or "Could not read Home Assistant config")
        data = json.loads(body)
        return str(data.get("time_zone") or "UTC")

    async def snapshot(self) -> dict:
        status, body = await self._request("POST", "/template", {"template": SNAPSHOT_TEMPLATE})
        if status >= 400:
            raise HomeAssistantError(body or "Could not read media players")
        try:
            data = json.loads(body)
        except json.JSONDecodeError as error:
            raise HomeAssistantError("Home Assistant returned an unreadable player list") from error
        if not isinstance(data, dict):
            raise HomeAssistantError("Home Assistant returned an unreadable player list")
        return data

    async def call_service(self, domain: str, service: str, data: dict) -> None:
        status, body = await self._request("POST", f"/services/{domain}/{service}", data)
        if status >= 400:
            message = body.strip() or f"{domain}.{service} failed"
            raise HomeAssistantError(message[:300])
