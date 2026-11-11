"""Ingress service for the Vermin Assistant panel and playback scheduler."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import threading
from datetime import datetime, timedelta
from json import JSONDecodeError
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import aiohttp
from aiohttp import web

from . import audio
from .ha import HomeAssistant, HomeAssistantError, compatible_players, presence_from_snapshot
from .schedule import due, evaluate, format_clock, next_play_at, next_window_start
from .store import load, save
from .targets import active_targets, signature

LOG = logging.getLogger("vermin_assistant")

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(os.environ.get("VERMIN_ASSISTANT_STATIC", ROOT / "static"))
DATA_DIR = Path(os.environ.get("VERMIN_ASSISTANT_DATA", "/data"))
SETTINGS_PATH = DATA_DIR / "settings.json"
MEDIA_DIR = Path(os.environ.get("VERMIN_ASSISTANT_MEDIA", "/media/vermin_assistant"))
DEV = os.environ.get("VERMIN_ASSISTANT_DEV") == "1"
SUPERVISOR_PEER = "172.30.32.2"
CLIP_SECONDS = float(audio.SECONDS)

MOCK_PLAYERS = [
    {
        "entity_id": "media_player.brandons_bedroom",
        "name": "Brandon's Bedroom",
        "area": "Brandon's Bedroom",
        "state": "idle",
        "supports_volume": True,
    },
    {
        "entity_id": "media_player.nigels_bedroom",
        "name": "Nigel's Bedroom",
        "area": "Nigel's Bedroom",
        "state": "idle",
        "supports_volume": True,
    },
    {
        "entity_id": "media_player.kitchen",
        "name": "Kitchen",
        "area": "Kitchen",
        "state": "off",
        "supports_volume": True,
    },
]


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


class Patrol:
    def __init__(self) -> None:
        self.settings = load(SETTINGS_PATH)
        self.timezone_name = "UTC"
        self.players: list[dict] = []
        self.hidden_incompatible = 0
        self.presence = {
            "someone_home": False,
            "people_home": None,
            "unknown": True,
            "source": "unknown",
        }
        self.connected = False
        self.audio_published = False
        self.audio_path: Path | None = None
        self.last_played: datetime | None = None
        self.last_error: str | None = None
        self.last_results: list[dict] = []
        self.playing_until: datetime | None = None
        self.clip_seconds = CLIP_SECONDS
        self._failure_until: datetime | None = None
        self._dev_someone_home = False
        self._dev_presence_known = True

    def now(self) -> datetime:
        return datetime.now(_zone(self.timezone_name))

    def publish_audio(self) -> None:
        source = audio.ensure_file(self.settings)
        self.audio_path = source
        self.clip_seconds = audio.duration_seconds(source)
        try:
            MEDIA_DIR.mkdir(parents=True, exist_ok=True)
            target = MEDIA_DIR / audio.FILE_NAME
            source_time = source.stat().st_mtime
            if (
                not target.exists()
                or target.stat().st_size != source.stat().st_size
                or target.stat().st_mtime + 0.01 < source_time
            ):
                shutil.copyfile(source, target)
            self.audio_published = True
        except OSError as error:
            self.audio_published = False
            LOG.warning("Could not copy the deterrent into the media folder: %s", error)

    async def refresh(self, hass: HomeAssistant) -> None:
        self.connected = hass.connected or DEV
        if DEV and not hass.connected:
            self.timezone_name = os.environ.get("VERMIN_ASSISTANT_TZ", "America/New_York")
            self.players = [dict(player) for player in MOCK_PLAYERS]
            self.hidden_incompatible = 1
            self.presence = {
                "someone_home": self._dev_someone_home,
                "people_home": 1 if self._dev_someone_home else 0,
                "unknown": not self._dev_presence_known,
                "source": "dev",
            }
            return
        if not hass.connected:
            self.players = []
            self.presence = {
                "someone_home": False,
                "people_home": None,
                "unknown": True,
                "source": "unknown",
            }
            return
        self.timezone_name = await hass.timezone_name()
        snapshot = await hass.snapshot()
        players, hidden = compatible_players(snapshot.get("players") or [])
        self.players = players
        self.hidden_incompatible = hidden
        self.presence = presence_from_snapshot(snapshot)

    def decision(self) -> dict:
        now = self.now()
        result = evaluate(self.settings, self.presence, now.hour)
        start = next_window_start(now, int(self.settings["start_hour"]), int(self.settings["end_hour"]))
        if not result["active"] and start is not None and self.settings.get("enabled") and self.settings.get("players"):
            if self.settings["mode"] in {"hours", "both"} and result["reason"] == "Waiting":
                result = {
                    "active": False,
                    "reason": f"Starts at {format_clock(start)}",
                }
        if result["active"] and not active_targets(self.settings):
            result = {"active": False, "reason": "Select an animal"}
        return result

    def status(self) -> dict:
        now = self.now()
        decision = self.decision()
        playing = self.playing_until is not None and now < self.playing_until
        upcoming = None
        if decision["active"]:
            upcoming_at = next_play_at(self.last_played, now, "continuous", self.clip_seconds)
            if upcoming_at is not None and not playing:
                upcoming = upcoming_at.isoformat()
        return {
            "settings": self.settings,
            "players": self.players,
            "hidden_incompatible": self.hidden_incompatible,
            "presence": self.presence,
            "patrol": {
                "active": decision["active"],
                "reason": decision["reason"],
                "playing": playing,
                "last_played": self.last_played.isoformat() if self.last_played else None,
                "next_play": upcoming,
                "last_error": self.last_error,
                "last_results": self.last_results,
            },
            "audio": {
                "title": "Mouse and rat deterrent",
                "seconds": int(round(self.clip_seconds)),
                "published": self.audio_published,
            },
            "homeassistant": self.connected,
            "dev": DEV,
            "timezone": self.timezone_name,
            "now": now.isoformat(),
        }

    async def play(self, hass: HomeAssistant, *, manual: bool) -> dict:
        selected = set(self.settings["players"])
        speakers = [player for player in self.players if player["entity_id"] in selected]
        if not speakers:
            raise HomeAssistantError("Select a speaker")
        if not active_targets(self.settings):
            raise HomeAssistantError("Select an animal")
        if not DEV and not self.audio_published:
            raise HomeAssistantError("The sound isn't ready yet")

        results: list[dict] = []
        for player in speakers:
            entity_id = player["entity_id"]
            try:
                if DEV and not hass.connected:
                    results.append({"entity_id": entity_id, "ok": True})
                    continue
                if player.get("supports_volume"):
                    await hass.call_service(
                        "media_player",
                        "volume_set",
                        {"entity_id": entity_id, "volume_level": self.settings["volume"]},
                    )
                await hass.call_service(
                    "media_player",
                    "play_media",
                    {
                        "entity_id": entity_id,
                        "media_content_id": "media-source://media_source/local/vermin_assistant/deterrent.wav",
                        "media_content_type": "music",
                        "announce": False,
                        "extra": {"title": "Vermin Assistant", "metadata": {"title": "Vermin Assistant"}},
                    },
                )
                results.append({"entity_id": entity_id, "ok": True})
            except HomeAssistantError as error:
                results.append({"entity_id": entity_id, "ok": False, "error": str(error)})

        self.last_results = results
        if any(item["ok"] for item in results):
            self.last_played = self.now()
            self.playing_until = self.last_played + timedelta(seconds=self.clip_seconds)
            self.last_error = None
            self._failure_until = None
        else:
            self.last_error = next((item["error"] for item in results if item.get("error")), "Playback failed")
            if not manual:
                self._failure_until = self.now() + timedelta(minutes=2)
        LOG.info("play manual=%s results=%s", manual, results)
        return self.status()

    async def stop(self, hass: HomeAssistant) -> dict:
        selected = set(self.settings["players"])
        for player in self.players:
            if player["entity_id"] not in selected:
                continue
            if DEV and not hass.connected:
                continue
            try:
                await hass.call_service(
                    "media_player",
                    "media_stop",
                    {"entity_id": player["entity_id"]},
                )
            except HomeAssistantError as error:
                LOG.warning("stop %s failed: %s", player["entity_id"], error)
        self.playing_until = None
        return self.status()

    async def tick(self, hass: HomeAssistant) -> None:
        try:
            await self.refresh(hass)
        except (HomeAssistantError, aiohttp.ClientError, asyncio.TimeoutError) as error:
            LOG.warning("refresh failed: %s", error)
            return
        decision = self.decision()
        if not decision["active"]:
            return
        now = self.now()
        if self._failure_until is not None and now < self._failure_until:
            return
        if not due(self.last_played, now, "continuous", self.clip_seconds):
            return
        try:
            await self.play(hass, manual=False)
        except HomeAssistantError as error:
            self.last_error = str(error)
            self._failure_until = now + timedelta(minutes=2)
            LOG.warning("scheduled play skipped: %s", error)


def _ingress_allowed(request: web.Request) -> bool:
    if DEV:
        return True
    peer = request.remote or ""
    return peer == SUPERVISOR_PEER


@web.middleware
async def ingress_guard(request: web.Request, handler):
    if not _ingress_allowed(request):
        raise web.HTTPForbidden(text="Forbidden")
    return await handler(request)


patrol_key: web.AppKey[Patrol] = web.AppKey("patrol")
session_key: web.AppKey[aiohttp.ClientSession] = web.AppKey("session")
scheduler_key: web.AppKey[asyncio.Task[None]] = web.AppKey("scheduler")


def create_app(patrol: Patrol | None = None) -> web.Application:
    patrol = patrol or Patrol()
    app = web.Application(middlewares=[ingress_guard])
    app[patrol_key] = patrol

    async def client_session(app_: web.Application):
        timeout = aiohttp.ClientTimeout(total=30)
        app_[session_key] = aiohttp.ClientSession(timeout=timeout)
        yield
        await app_[session_key].close()

    app.cleanup_ctx.append(client_session)

    def hass() -> HomeAssistant:
        return HomeAssistant(app[session_key])

    async def scheduler(_app: web.Application):
        await asyncio.sleep(2)
        while True:
            await patrol.tick(hass())
            await asyncio.sleep(15)

    async def on_start(_app: web.Application):
        await asyncio.to_thread(patrol.publish_audio)
        app[scheduler_key] = asyncio.create_task(scheduler(app))

    async def on_stop(_app: web.Application):
        task = app.get(scheduler_key)
        if task:
            task.cancel()

    app.on_startup.append(on_start)
    app.on_cleanup.append(on_stop)

    async def status(_request: web.Request) -> web.Response:
        try:
            await patrol.refresh(hass())
        except (HomeAssistantError, aiohttp.ClientError, asyncio.TimeoutError) as error:
            LOG.warning("status refresh failed: %s", error)
        return web.json_response(patrol.status())

    async def update_settings(request: web.Request) -> web.Response:
        try:
            payload = await request.json()
        except JSONDecodeError:
            raise web.HTTPBadRequest(text="Expected JSON") from None
        if not isinstance(payload, dict):
            raise web.HTTPBadRequest(text="Expected a settings object")
        previous = signature(patrol.settings)
        patrol.settings = save(SETTINGS_PATH, payload)
        patrol._failure_until = None
        if signature(patrol.settings) != previous:
            threading.Thread(target=patrol.publish_audio, daemon=True).start()
        return web.json_response(patrol.status())

    async def play_now(request: web.Request) -> web.Response:
        try:
            body = await play_body(request)
        except web.HTTPBadRequest:
            raise
        if body:
            patrol.settings = save(SETTINGS_PATH, {**patrol.settings, **body})
        try:
            await patrol.refresh(hass())
            result = await patrol.play(hass(), manual=True)
        except HomeAssistantError as error:
            raise web.HTTPBadRequest(text=str(error)) from error
        return web.json_response(result)

    async def stop_now(_request: web.Request) -> web.Response:
        try:
            await patrol.refresh(hass())
            result = await patrol.stop(hass())
        except HomeAssistantError as error:
            raise web.HTTPBadRequest(text=str(error)) from error
        return web.json_response(result)

    async def dev_presence(request: web.Request) -> web.Response:
        if not DEV:
            raise web.HTTPNotFound()
        payload = await request.json()
        patrol._dev_someone_home = bool(payload.get("someone_home"))
        patrol._dev_presence_known = bool(payload.get("known", True))
        return web.json_response(patrol.status())

    async def index(request: web.Request) -> web.Response:
        page = STATIC_DIR / "index.html"
        if not page.exists():
            return web.Response(status=404, text="Panel has not been built")
        html = page.read_text(encoding="utf-8")
        ingress = request.headers.get("X-Ingress-Path", "").strip()
        if ingress:
            base = ingress.rstrip("/") + "/"
            html = html.replace("<!--ingress-base-->", f'<base href="{base}">', 1)
        else:
            html = html.replace("<!--ingress-base-->", "", 1)
        return web.Response(text=html, content_type="text/html")

    async def deterrent(_request: web.Request) -> web.Response:
        path = patrol.audio_path or audio.ensure_file()
        return web.FileResponse(path)

    async def preview(_request: web.Request) -> web.Response:
        path = audio.preview_path()
        if not path.exists():
            audio.ensure_file()
            path = audio.preview_path()
        return web.FileResponse(path)

    app.router.add_get("/api/status", status)
    app.router.add_put("/api/settings", update_settings)
    app.router.add_post("/api/play", play_now)
    app.router.add_post("/api/stop", stop_now)
    app.router.add_post("/api/dev/presence", dev_presence)
    app.router.add_get("/audio/deterrent.wav", deterrent)
    app.router.add_get("/audio/preview.wav", preview)
    app.router.add_get("/", index)
    if STATIC_DIR.exists():
        app.router.add_static("/assets", STATIC_DIR / "assets", show_index=False)
    return app


async def play_body(request: web.Request) -> dict:
    if request.content_type != "application/json":
        return {}
    try:
        payload = await request.json()
    except JSONDecodeError:
        return {}
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise web.HTTPBadRequest(text="Expected a settings object")
    return payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    port = int(os.environ.get("PORT", "8099"))
    web.run_app(create_app(), host="0.0.0.0", port=port, print=None)


if __name__ == "__main__":
    main()
