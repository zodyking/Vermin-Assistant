import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from app.ha import compatible_players, presence_from_snapshot
from app.schedule import due, evaluate, in_hour_window, next_window_start
from app.store import normalize

ZONE = ZoneInfo("UTC")


class WindowTests(unittest.TestCase):
    def test_daytime_window(self):
        self.assertTrue(in_hour_window(9, 8, 17))
        self.assertFalse(in_hour_window(7, 8, 17))
        self.assertFalse(in_hour_window(17, 8, 17))

    def test_overnight_window(self):
        self.assertTrue(in_hour_window(23, 20, 7))
        self.assertTrue(in_hour_window(3, 20, 7))
        self.assertFalse(in_hour_window(12, 20, 7))
        self.assertFalse(in_hour_window(7, 20, 7))

    def test_equal_bounds_are_all_day(self):
        self.assertTrue(in_hour_window(0, 8, 8))
        self.assertTrue(in_hour_window(15, 8, 8))

    def test_next_start_rolls_to_tomorrow_after_the_window(self):
        now = datetime(2026, 11, 11, 21, 30, tzinfo=ZONE)
        start = next_window_start(now, 8, 17)
        self.assertEqual(start, datetime(2026, 11, 12, 8, 0, tzinfo=ZONE))

    def test_next_start_later_today(self):
        now = datetime(2026, 11, 11, 12, 30, tzinfo=ZONE)
        start = next_window_start(now, 20, 7)
        self.assertEqual(start, datetime(2026, 11, 11, 20, 0, tzinfo=ZONE))

    def test_next_start_is_none_while_open(self):
        now = datetime(2026, 11, 11, 22, 0, tzinfo=ZONE)
        self.assertIsNone(next_window_start(now, 20, 7))


class DecisionTests(unittest.TestCase):
    def settings(self, **overrides):
        base = {
            "enabled": True,
            "mode": "both",
            "start_hour": 20,
            "end_hour": 7,
            "players": ["media_player.kitchen"],
        }
        base.update(overrides)
        return base

    def test_off_and_no_speakers(self):
        self.assertFalse(evaluate(self.settings(enabled=False), {"someone_home": False}, 21)["active"])
        result = evaluate(self.settings(players=[]), {"someone_home": False}, 21)
        self.assertEqual(result["reason"], "Select a speaker")

    def test_both_requires_hours_and_away(self):
        away = {"someone_home": False, "unknown": False}
        home = {"someone_home": True, "unknown": False}
        self.assertTrue(evaluate(self.settings(), away, 22)["active"])
        self.assertFalse(evaluate(self.settings(), away, 12)["active"])
        self.assertFalse(evaluate(self.settings(), home, 22)["active"])

    def test_away_ignores_hours(self):
        away = {"someone_home": False, "unknown": False}
        self.assertTrue(evaluate(self.settings(mode="away"), away, 12)["active"])

    def test_unknown_presence_blocks_away_modes(self):
        unknown = {"someone_home": False, "unknown": True}
        self.assertFalse(evaluate(self.settings(mode="away"), unknown, 12)["active"])
        self.assertTrue(evaluate(self.settings(mode="hours"), unknown, 22)["active"])

    def test_repeat_gap(self):
        now = datetime(2026, 11, 11, 21, 0, tzinfo=ZONE)
        self.assertFalse(due(now, datetime(2026, 11, 11, 21, 0, 10, tzinfo=ZONE), "continuous", 36))
        self.assertTrue(due(now, datetime(2026, 11, 11, 21, 1, tzinfo=ZONE), "continuous", 36))
        self.assertFalse(due(now, datetime(2026, 11, 11, 21, 20, tzinfo=ZONE), "30", 36))


class PresenceTests(unittest.TestCase):
    def test_zone_with_people(self):
        presence = presence_from_snapshot({"zone_home": "0", "person_count": 2, "persons_home": 0})
        self.assertFalse(presence["someone_home"])
        self.assertEqual(presence["source"], "zone.home")

    def test_empty_house_is_unknown(self):
        presence = presence_from_snapshot(
            {"zone_home": "0", "person_count": 0, "tracker_count": 0, "persons_home": 0, "trackers_home": 0}
        )
        self.assertTrue(presence["unknown"])

    def test_trackers_are_the_fallback(self):
        presence = presence_from_snapshot(
            {"zone_home": "unknown", "person_count": 0, "tracker_count": 2, "trackers_home": 1, "persons_home": 0}
        )
        self.assertTrue(presence["someone_home"])
        self.assertEqual(presence["source"], "device_tracker")

    def test_compatible_players_keep_play_media_only(self):
        players, hidden = compatible_players(
            [
                {"entity_id": "media_player.kitchen", "name": "Kitchen", "state": "idle", "area": "Kitchen", "features": 512},
                {"entity_id": "media_player.tv", "name": "TV", "state": "off", "area": None, "features": 128},
            ]
        )
        self.assertEqual(hidden, 1)
        self.assertEqual(players[0]["entity_id"], "media_player.kitchen")
        self.assertEqual(players[0]["area"], "Kitchen")


class StoreTests(unittest.TestCase):
    def test_normalize_rejects_bad_values(self):
        settings = normalize(
            {
                "enabled": True,
                "mode": "nope",
                "start_hour": 99,
                "end_hour": "6",
                "repeat": "10",
                "volume": 4,
                "players": ["light.kitchen", "media_player.kitchen", "media_player.kitchen"],
            }
        )
        self.assertEqual(settings["mode"], "both")
        self.assertEqual(settings["start_hour"], 20)
        self.assertEqual(settings["end_hour"], 6)
        self.assertEqual(settings["repeat"], "continuous")
        self.assertEqual(settings["volume"], 1.0)
        self.assertEqual(settings["players"], ["media_player.kitchen"])
        self.assertTrue(settings["targets"]["mouse"]["enabled"])
        self.assertTrue(settings["targets"]["rat"]["enabled"])
        self.assertFalse(settings["targets"]["cockroach"]["enabled"])
        self.assertFalse(settings["targets"]["moth"]["enabled"])


if __name__ == "__main__":
    unittest.main()
