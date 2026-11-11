"""HTTP checks for the panel API. Uses a short generated tone and sample speakers."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="vermin-assistant-"))
os.environ["VERMIN_ASSISTANT_DEV"] = "1"
os.environ["VERMIN_ASSISTANT_DATA"] = str(_TMP)
os.environ["VERMIN_ASSISTANT_MEDIA"] = str(_TMP / "media")

from app.audio import render, write_wav  # noqa: E402

_SOUND = _TMP / "deterrent.wav"
write_wav(_SOUND, render(seconds=2))
os.environ["VERMIN_ASSISTANT_SOUND"] = str(_SOUND)

from aiohttp.test_utils import AioHTTPTestCase  # noqa: E402

from app.server import create_app  # noqa: E402


class ApiTests(AioHTTPTestCase):
    async def get_application(self):
        return create_app()

    async def test_schedule_play_and_stop(self):
        status = await self.client.get("/api/status")
        self.assertEqual(status.status, 200)
        body = await status.json()
        self.assertTrue(body["dev"])
        self.assertEqual(len(body["players"]), 3)
        self.assertFalse(body["settings"]["enabled"])

        saved = {
            **body["settings"],
            "enabled": True,
            "mode": "both",
            "start_hour": 0,
            "end_hour": 0,
            "players": ["media_player.kitchen"],
            "volume": 0.4,
        }
        updated = await self.client.put("/api/settings", json=saved)
        self.assertEqual(updated.status, 200)
        updated_body = await updated.json()
        self.assertTrue(updated_body["settings"]["enabled"])
        self.assertTrue(updated_body["patrol"]["active"])
        self.assertIn("media_player.kitchen", updated_body["settings"]["players"])

        played = await self.client.post("/api/play", json=saved)
        self.assertEqual(played.status, 200)
        played_body = await played.json()
        self.assertTrue(played_body["patrol"]["playing"])
        self.assertTrue(played_body["patrol"]["last_results"][0]["ok"])

        stopped = await self.client.post("/api/stop")
        self.assertEqual(stopped.status, 200)
        stopped_body = await stopped.json()
        self.assertFalse(stopped_body["patrol"]["playing"])

        tone = await self.client.get("/audio/deterrent.wav")
        self.assertEqual(tone.status, 200)
        payload = await tone.read()
        self.assertTrue(payload.startswith(b"RIFF"))


if __name__ == "__main__":
    unittest.main()
