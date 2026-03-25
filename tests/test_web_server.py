import copy
import unittest
from datetime import datetime

import web_server


class FakeSnapshotService:
    def __init__(self):
        self.latest_calls = []
        self._snapshot = {
            "timestamp": "2026-03-24T10:30:00",
            "data_source": "akshare_futures_LC0",
            "price": {"current": 151440.0, "unit": "元/吨"},
            "signal": {"direction": "bearish", "strength": 3},
            "cost": {"total_per_pack": 6057.6},
            "prediction": {"direction": "neutral_to_bearish"},
            "ai_analysis": {"risk_level": "medium"},
            "snapshot_cached_at": "2026-03-24T10:28:00",
            "snapshot_ttl_seconds": 300,
            "stale": False,
        }

    def get_snapshot(self, force_refresh=False):
        self.latest_calls.append(force_refresh)
        snapshot = copy.deepcopy(self._snapshot)
        if force_refresh:
            snapshot["snapshot_cached_at"] = "2026-03-24T10:31:00"
        return snapshot

    def get_cache_status(self):
        return {
            "cached": True,
            "cached_at": "2026-03-24T10:28:00",
            "age_seconds": 12,
            "ttl_seconds": 300,
        }


class WebServerApiTests(unittest.TestCase):
    def setUp(self):
        self.original_snapshot = web_server.analysis_snapshot
        self.original_api_key = web_server.API_CONFIG["api_key"]
        self.original_last_analysis_time = web_server.last_analysis_time

        self.fake_snapshot = FakeSnapshotService()
        web_server.analysis_snapshot = self.fake_snapshot
        web_server.API_CONFIG["api_key"] = "test-key"
        web_server.last_analysis_time = None

        self.app = web_server.create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def tearDown(self):
        web_server.analysis_snapshot = self.original_snapshot
        web_server.API_CONFIG["api_key"] = self.original_api_key
        web_server.last_analysis_time = self.original_last_analysis_time

    def test_latest_requires_api_key(self):
        response = self.client.get("/api/latest")

        self.assertEqual(response.status_code, 401)
        payload = response.get_json()
        self.assertTrue(payload["error"])
        self.assertEqual(payload["code"], "AUTH_FAILED")

    def test_latest_returns_snapshot_with_valid_api_key(self):
        response = self.client.get("/api/latest", headers={"X-API-Key": "test-key"})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["price"]["current"], 151440.0)
        self.assertEqual(payload["snapshot_cached_at"], "2026-03-24T10:28:00")
        self.assertIsInstance(web_server.last_analysis_time, datetime)

    def test_refresh_forces_snapshot_rebuild(self):
        response = self.client.post("/api/refresh", headers={"X-API-Key": "test-key"})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["snapshot"]["snapshot_cached_at"], "2026-03-24T10:31:00")
        self.assertEqual(self.fake_snapshot.latest_calls, [True])

    def test_status_is_public_and_returns_cache_metadata(self):
        response = self.client.get("/api/status")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "running")
        self.assertTrue(payload["snapshot_cached"])
        self.assertEqual(payload["snapshot_age_seconds"], 12)


if __name__ == "__main__":
    unittest.main()
