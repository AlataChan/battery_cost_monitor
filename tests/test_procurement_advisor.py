import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.agents.procurement_advisor import ProcurementAdvisor


def build_snapshot(direction="bullish", bollinger_position=0.2, confidence=72):
    return {
        "timestamp": "2026-03-24T10:30:00",
        "price": {"current": 151440.0},
        "signal": {
            "direction": direction,
            "strength": 3,
            "confidence": confidence,
            "indicators": {
                "bollinger_position": bollinger_position,
            },
        },
        "cost": {"total_per_pack": 6057.6},
        "prediction": {"direction": "neutral_to_bullish"},
    }


class ProcurementAdvisorTests(unittest.TestCase):
    def setUp(self):
        self.advisor = ProcurementAdvisor()

    def test_classifies_urgency_from_runway_days(self):
        self.assertEqual(self.advisor.classify_urgency(20), "high")
        self.assertEqual(self.advisor.classify_urgency(45), "medium")
        self.assertEqual(self.advisor.classify_urgency(75), "low")

    def test_recommends_buy_for_medium_urgency_good_timing(self):
        context = {
            "monthly_demand_tons": 200.0,
            "inventory_tons": 300.0,
            "budget_remaining": 30000000.0,
            "last_purchase_price": 153000.0,
            "avg_3m_price": 160000.0,
        }

        decision = self.advisor.generate_advice(
            snapshot=build_snapshot(),
            context=context,
            now=datetime(2026, 3, 24, 10, 30, 0),
        )

        self.assertEqual(decision["action"], "buy")
        self.assertTrue(decision["requires_confirmation"])
        self.assertEqual(decision["quantity_tons"], 100.0)
        self.assertEqual(decision["reasoning"]["matrix_cell"], "中紧迫 × 好时机 → 适量采购")
        self.assertGreaterEqual(decision["confidence"], 50)

    def test_low_confidence_returns_observe_only(self):
        context = {
            "monthly_demand_tons": 200.0,
            "inventory_tons": 500.0,
            "budget_remaining": 30000000.0,
        }

        decision = self.advisor.generate_advice(
            snapshot=build_snapshot(direction="neutral", bollinger_position=0.5, confidence=35),
            context=context,
            now=datetime(2026, 3, 24, 10, 30, 0),
        )

        self.assertEqual(decision["action"], "observe")
        self.assertEqual(decision["quantity_tons"], 0.0)
        self.assertLess(decision["confidence"], 50)
        self.assertIn("观察", decision["summary"])

    def test_appends_jsonl_decision_log(self):
        context = {
            "monthly_demand_tons": 200.0,
            "inventory_tons": 300.0,
            "budget_remaining": 30000000.0,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "decisions.jsonl"
            decision = self.advisor.generate_advice(
                snapshot=build_snapshot(),
                context=context,
                now=datetime(2026, 3, 24, 10, 30, 0),
                decision_log_path=log_path,
            )

            lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            logged = json.loads(lines[0])
            self.assertEqual(logged["decision_id"], decision["decision_id"])
            self.assertEqual(logged["business_snapshot"]["urgency"], "medium")

    def test_all_nine_decision_matrix_cells_return_reasonable_outputs(self):
        cases = [
            ("high", "good", {"inventory_tons": 100.0}, build_snapshot(direction="bullish", bollinger_position=0.2), "buy"),
            ("high", "neutral", {"inventory_tons": 100.0}, build_snapshot(direction="neutral", bollinger_position=0.5), "buy"),
            ("high", "bad", {"inventory_tons": 100.0}, build_snapshot(direction="bearish", bollinger_position=0.8), "buy"),
            ("medium", "good", {"inventory_tons": 300.0}, build_snapshot(direction="bullish", bollinger_position=0.2), "buy"),
            ("medium", "neutral", {"inventory_tons": 300.0}, build_snapshot(direction="neutral", bollinger_position=0.5), "observe"),
            ("medium", "bad", {"inventory_tons": 300.0}, build_snapshot(direction="bearish", bollinger_position=0.8), "observe"),
            ("low", "good", {"inventory_tons": 500.0}, build_snapshot(direction="bullish", bollinger_position=0.2), "buy"),
            ("low", "neutral", {"inventory_tons": 500.0}, build_snapshot(direction="neutral", bollinger_position=0.5), "observe"),
            ("low", "bad", {"inventory_tons": 500.0}, build_snapshot(direction="bearish", bollinger_position=0.8), "observe"),
        ]

        for expected_urgency, expected_timing, context_patch, snapshot, expected_action in cases:
            with self.subTest(urgency=expected_urgency, timing=expected_timing):
                context = {
                    "monthly_demand_tons": 200.0,
                    "budget_remaining": 30000000.0,
                    **context_patch,
                }
                decision = self.advisor.generate_advice(
                    snapshot=snapshot,
                    context=context,
                    now=datetime(2026, 3, 24, 10, 30, 0),
                )

                self.assertEqual(decision["action"], expected_action)
                self.assertTrue(decision["requires_confirmation"])
                self.assertIn("valid_until", decision)
                self.assertIn(expected_urgency, decision["reasoning"]["urgency"])
                self.assertIn(expected_timing, decision["reasoning"]["timing"])


if __name__ == "__main__":
    unittest.main()
