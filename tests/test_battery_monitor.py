import unittest
from datetime import datetime

from src.agents.battery_monitor import BatteryMonitor


def build_snapshot(direction="bearish", strength=3):
    return {
        "timestamp": "2026-03-24T10:30:00",
        "price": {"current": 151440.0},
        "signal": {
            "direction": direction,
            "strength": strength,
        },
        "cost": {"change_pct": 12.3},
    }


class BatteryMonitorTests(unittest.TestCase):
    def setUp(self):
        self.monitor = BatteryMonitor(cooldown_hours=2)

    def test_skips_when_not_in_trading_hours(self):
        result = self.monitor.monitor_cycle(
            snapshot=build_snapshot(),
            memory={},
            now=datetime(2026, 3, 24, 22, 0, 0),
            trading_hours=False,
        )

        self.assertFalse(result["should_push"])
        self.assertEqual(result["schedule"], "next_open")
        self.assertEqual(result["reason"], "outside_trading_hours")

    def test_pushes_immediately_on_direction_change(self):
        memory = {
            "last_direction": "bearish",
            "last_strength": 2,
            "consecutive_count": 2,
            "consecutive_since": "2026-03-24T09:30:00",
            "signal_history_24h": [],
        }

        result = self.monitor.monitor_cycle(
            snapshot=build_snapshot(direction="bullish", strength=3),
            memory=memory,
            now=datetime(2026, 3, 24, 10, 30, 0),
            trading_hours=True,
        )

        self.assertTrue(result["should_push"])
        self.assertEqual(result["reason"], "direction_changed")
        self.assertEqual(result["memory"]["last_direction"], "bullish")
        self.assertEqual(result["memory"]["consecutive_count"], 1)
        self.assertIn("方向反转", result["report"])

    def test_consecutive_confirmation_respects_cooldown(self):
        memory = {
            "last_direction": "bullish",
            "last_strength": 3,
            "consecutive_count": 2,
            "consecutive_since": "2026-03-24T09:30:00",
            "last_push_time": "2026-03-24T09:45:00",
            "signal_history_24h": [],
        }

        result = self.monitor.monitor_cycle(
            snapshot=build_snapshot(direction="bullish", strength=3),
            memory=memory,
            now=datetime(2026, 3, 24, 10, 30, 0),
            trading_hours=True,
        )

        self.assertFalse(result["should_push"])
        self.assertEqual(result["reason"], "cooldown_active")
        self.assertEqual(result["memory"]["consecutive_count"], 3)

    def test_strong_signal_pushes_when_cooldown_has_expired(self):
        memory = {
            "last_direction": "bullish",
            "last_strength": 3,
            "consecutive_count": 5,
            "consecutive_since": "2026-03-23T09:30:00",
            "last_push_time": "2026-03-24T07:00:00",
            "signal_history_24h": [],
        }

        result = self.monitor.monitor_cycle(
            snapshot=build_snapshot(direction="bullish", strength=4),
            memory=memory,
            now=datetime(2026, 3, 24, 10, 30, 0),
            trading_hours=True,
        )

        self.assertTrue(result["should_push"])
        self.assertEqual(result["reason"], "strong_signal")
        self.assertEqual(result["memory"]["last_push_time"], "2026-03-24T10:30:00")

    def test_preserves_multi_day_consecutive_memory_and_trims_old_history(self):
        memory = {
            "last_direction": "bullish",
            "last_strength": 3,
            "consecutive_count": 2,
            "consecutive_since": "2026-03-21T10:30:00",
            "signal_history_24h": [
                {
                    "time": "2026-03-23T08:00:00",
                    "direction": "bullish",
                    "strength": 2,
                    "price": 150000.0,
                },
                {
                    "time": "2026-03-24T09:45:00",
                    "direction": "bullish",
                    "strength": 3,
                    "price": 151000.0,
                },
            ],
        }

        result = self.monitor.monitor_cycle(
            snapshot=build_snapshot(direction="bullish", strength=3),
            memory=memory,
            now=datetime(2026, 3, 24, 10, 30, 0),
            trading_hours=True,
        )

        self.assertEqual(result["memory"]["consecutive_count"], 3)
        self.assertEqual(result["memory"]["consecutive_since"], "2026-03-21T10:30:00")
        self.assertEqual(len(result["memory"]["signal_history_24h"]), 2)
        self.assertEqual(result["memory"]["signal_history_24h"][0]["time"], "2026-03-24T09:45:00")


if __name__ == "__main__":
    unittest.main()
