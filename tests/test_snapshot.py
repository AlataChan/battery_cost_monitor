import copy
import os
import unittest
from unittest.mock import patch

from src.services.snapshot import AnalysisSnapshot


class FakeAdapter:
    def __init__(self):
        self.fetch_calls = 0
        self.should_fail = False

    def fetch_all(self, symbol):
        self.fetch_calls += 1
        if self.should_fail:
            raise RuntimeError(f"failed to load market data for {symbol}")

        return {
            "futures_data": object(),
            "daily_data": object(),
            "current_price": 151440.0,
        }

    def extract_signal(self, futures_data, daily_data, symbol):
        _ = futures_data, daily_data, symbol
        return {
            "direction": "bearish",
            "strength": 3,
            "confidence": 65,
            "description": "多重指标看跌确认，布林带下轨附近",
            "indicators": {
                "ema_trend": "bearish",
                "macd": "bearish_crossover",
                "kdj_status": "oversold",
                "bollinger_position": 0.15,
                "volume_ratio": 1.3,
            },
        }


class FakeCalculator:
    def __init__(self):
        self.config = {
            "baseline_total_cost": 3308.0,
            "materials": {
                "LC": {
                    "name": "碳酸锂",
                    "baseline_price": 82700.0,
                    "standard_usage": 40,
                }
            },
        }

    def _calculate_material_cost(self, symbol, config, current_price):
        _ = symbol, config
        return {
            "name": "碳酸锂",
            "usage": 40,
            "current_cost": 6057.6,
        }


class FakePredictor:
    def _generate_prediction(self, symbol, futures_data, daily_data):
        _ = symbol, futures_data, daily_data
        return {
            "current_price": 151440.0,
            "confidence": 40.0,
            "technical_analysis": {
                "overall_signal": "bearish",
            },
            "trend_prediction": {
                "trend_direction": "down",
            },
            "price_prediction": {
                "confidence_lower": 148000.0,
                "confidence_upper": 154000.0,
            },
        }

    def _get_ai_analysis(self, symbol, technical_prediction):
        _ = symbol, technical_prediction
        return {
            "ai_analysis": "短期震荡偏弱",
            "market_sentiment": "看跌",
            "risk_assessment": {
                "risk_level": "中",
                "risk_factors": ["布林带下轨支撑", "成交量放大", "KDJ超卖"],
            },
        }

    def _combine_predictions(self, technical_prediction, ai_analysis):
        combined = copy.deepcopy(technical_prediction)
        combined["ai_mentor_analysis"] = ai_analysis
        combined["confidence"] = 55.0
        return combined


class AnalysisSnapshotTests(unittest.TestCase):
    def build_snapshot(self):
        with patch.dict(os.environ, {"SNAPSHOT_CACHE_TTL": "300"}, clear=False):
            snapshot = AnalysisSnapshot()

        snapshot._adapter = FakeAdapter()
        snapshot._calculator = FakeCalculator()
        snapshot._predictor = FakePredictor()
        return snapshot

    def test_get_snapshot_returns_structured_payload_and_hits_cache(self):
        snapshot = self.build_snapshot()

        first = snapshot.get_snapshot()
        second = snapshot.get_snapshot()

        self.assertEqual(snapshot._adapter.fetch_calls, 1)
        self.assertEqual(first["snapshot_cached_at"], second["snapshot_cached_at"])
        self.assertFalse(second["stale"])
        self.assertEqual(first["data_source"], "akshare_futures_LC0")
        self.assertEqual(first["price"]["current"], 151440.0)
        self.assertEqual(first["signal"]["direction"], "bearish")
        self.assertEqual(first["cost"]["total_per_pack"], 6057.6)
        self.assertEqual(first["prediction"]["price_range_7d"], [148000.0, 154000.0])
        self.assertEqual(first["ai_analysis"]["risk_level"], "medium")

    def test_force_refresh_returns_stale_cache_when_rebuild_fails(self):
        snapshot = self.build_snapshot()

        first = snapshot.get_snapshot()
        snapshot._adapter.should_fail = True

        stale = snapshot.get_snapshot(force_refresh=True)

        self.assertTrue(stale["stale"])
        self.assertEqual(stale["snapshot_cached_at"], first["snapshot_cached_at"])
        self.assertIn("failed to load market data", stale["error_message"])


if __name__ == "__main__":
    unittest.main()
