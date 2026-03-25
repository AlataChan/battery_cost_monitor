from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .common import append_jsonl, load_json_file, save_json_file


DECISION_MATRIX = {
    ("high", "good"): {"action": "buy", "ratio": 0.8, "confidence": 80, "summary": "建议立即采购"},
    ("high", "neutral"): {"action": "buy", "ratio": 0.6, "confidence": 65, "summary": "建议立即采购"},
    ("high", "bad"): {"action": "buy", "ratio": 0.2, "confidence": 60, "summary": "建议先采购最低保障量"},
    ("medium", "good"): {"action": "buy", "ratio": 0.5, "confidence": 72, "summary": "建议适量采购"},
    ("medium", "neutral"): {"action": "observe", "ratio": 0.0, "confidence": 45, "summary": "建议继续观察"},
    ("medium", "bad"): {"action": "observe", "ratio": 0.0, "confidence": 40, "summary": "建议继续观察"},
    ("low", "good"): {"action": "buy", "ratio": 0.3, "confidence": 58, "summary": "建议战略建仓"},
    ("low", "neutral"): {"action": "observe", "ratio": 0.0, "confidence": 35, "summary": "建议继续观察"},
    ("low", "bad"): {"action": "observe", "ratio": 0.0, "confidence": 30, "summary": "建议继续观察"},
}


class ProcurementAdvisor:
    def classify_urgency(self, runway_days: float) -> str:
        if runway_days < 30:
            return "high"
        if runway_days <= 60:
            return "medium"
        return "low"

    def classify_timing(self, snapshot: dict[str, Any]) -> str:
        signal = snapshot.get("signal", {})
        prediction = snapshot.get("prediction", {})
        direction = signal.get("direction", "neutral")
        predicted_direction = prediction.get("direction", "neutral")
        bollinger_position = float(signal.get("indicators", {}).get("bollinger_position", 0.5) or 0.5)

        bullish = direction in {"bullish", "neutral_to_bullish"} or predicted_direction in {"bullish", "neutral_to_bullish"}
        bearish = direction in {"bearish", "neutral_to_bearish"} or predicted_direction in {"bearish", "neutral_to_bearish"}

        if bullish and bollinger_position <= 0.35:
            return "good"
        if bearish and bollinger_position >= 0.65:
            return "bad"
        return "neutral"

    def generate_advice(
        self,
        snapshot: dict[str, Any],
        context: dict[str, Any],
        now: datetime | None = None,
        decision_log_path: str | Path | None = None,
    ) -> dict[str, Any]:
        current_time = now or datetime.now()
        monthly_demand = float(context.get("monthly_demand_tons", 0.0) or 0.0)
        inventory = float(context.get("inventory_tons", 0.0) or 0.0)
        budget_remaining = float(context.get("budget_remaining", 0.0) or 0.0)
        runway_days = self.calculate_runway_days(monthly_demand, inventory)
        urgency = self.classify_urgency(runway_days)
        timing = self.classify_timing(snapshot)
        matrix = DECISION_MATRIX[(urgency, timing)]
        confidence = float(matrix["confidence"])

        quantity_tons = round(monthly_demand * float(matrix["ratio"]), 2)
        action = matrix["action"]
        summary = matrix["summary"]
        if confidence < 50 or action == "observe":
            action = "observe"
            quantity_tons = 0.0
            summary = "建议继续观察，暂不执行采购"

        decision = {
            "decision_id": self._build_decision_id(current_time),
            "timestamp": current_time.isoformat(timespec="seconds"),
            "action": action,
            "requires_confirmation": True,
            "summary": summary if action == "observe" else f"{summary} {quantity_tons} 吨碳酸锂",
            "quantity_tons": quantity_tons,
            "reasoning": {
                "urgency": f"{urgency} (库存{runway_days:.0f}天)",
                "timing": f"{timing} (基于技术方向与布林带位置)",
                "matrix_cell": self._matrix_cell_label(urgency, timing),
            },
            "price_context": self._build_price_context(snapshot, context),
            "cost_impact": self._build_cost_impact(snapshot, quantity_tons, budget_remaining),
            "risk_note": self._build_risk_note(action, timing),
            "confidence": confidence,
            "valid_until": self._build_valid_until(current_time),
        }

        if decision_log_path is not None:
            self.log_decision(decision_log_path, decision, snapshot, context, runway_days, urgency)

        return decision

    def load_context(self, path: str | Path) -> dict[str, Any]:
        return load_json_file(path, {})

    def save_context(self, path: str | Path, context: dict[str, Any]) -> None:
        save_json_file(path, context)

    def log_decision(
        self,
        path: str | Path,
        decision: dict[str, Any],
        snapshot: dict[str, Any],
        context: dict[str, Any],
        runway_days: float,
        urgency: str,
    ) -> None:
        payload = {
            "decision_id": decision["decision_id"],
            "timestamp": decision["timestamp"],
            "advice_summary": decision["summary"],
            "market_snapshot": {
                "price": snapshot.get("price", {}).get("current"),
                "signal_direction": snapshot.get("signal", {}).get("direction"),
                "signal_strength": snapshot.get("signal", {}).get("strength"),
            },
            "business_snapshot": {
                "inventory_tons": float(context.get("inventory_tons", 0.0) or 0.0),
                "runway_days": round(runway_days, 2),
                "urgency": urgency,
            },
            "user_action": None,
            "outcome_7d": None,
        }
        append_jsonl(path, payload)

    def calculate_runway_days(self, monthly_demand_tons: float, inventory_tons: float) -> float:
        if monthly_demand_tons <= 0:
            return 9999.0
        daily_demand = monthly_demand_tons / 30.0
        if daily_demand <= 0:
            return 9999.0
        return inventory_tons / daily_demand

    def _build_decision_id(self, current_time: datetime) -> str:
        return f"DEC-{current_time.strftime('%Y%m%d-%H%M%S')}"

    def _matrix_cell_label(self, urgency: str, timing: str) -> str:
        urgency_label = {"high": "高紧迫", "medium": "中紧迫", "low": "低紧迫"}[urgency]
        timing_label = {"good": "好时机", "neutral": "中性时机", "bad": "差时机"}[timing]
        outcome_label = {
            ("high", "good"): "立即采购",
            ("high", "neutral"): "立即采购",
            ("high", "bad"): "少量采购",
            ("medium", "good"): "适量采购",
            ("medium", "neutral"): "观望",
            ("medium", "bad"): "观望",
            ("low", "good"): "战略建仓",
            ("low", "neutral"): "观望",
            ("low", "bad"): "观望",
        }[(urgency, timing)]
        return f"{urgency_label} × {timing_label} → {outcome_label}"

    def _build_price_context(self, snapshot: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        current_price = float(snapshot.get("price", {}).get("current", 0.0) or 0.0)
        last_purchase_price = float(context.get("last_purchase_price", 0.0) or 0.0)
        avg_3m_price = float(context.get("avg_3m_price", 0.0) or 0.0)

        return {
            "current_price": current_price,
            "vs_last_purchase": self._format_delta_pct(current_price, last_purchase_price),
            "vs_3month_avg": self._format_delta_pct(current_price, avg_3m_price),
            "prediction_7d": snapshot.get("prediction", {}).get("direction"),
        }

    def _build_cost_impact(
        self,
        snapshot: dict[str, Any],
        quantity_tons: float,
        budget_remaining: float,
    ) -> dict[str, Any]:
        current_price = float(snapshot.get("price", {}).get("current", 0.0) or 0.0)
        total_purchase_cost = round(current_price * quantity_tons, 2)
        budget_ratio = 0.0
        if budget_remaining > 0:
            budget_ratio = (total_purchase_cost / budget_remaining) * 100

        return {
            "per_pack_cost": snapshot.get("cost", {}).get("total_per_pack"),
            "total_purchase_cost": total_purchase_cost,
            "vs_budget_remaining": f"{budget_ratio:.2f}%",
        }

    def _build_risk_note(self, action: str, timing: str) -> str:
        if action == "observe":
            return "当前置信度不足，建议等待更清晰的价格与信号确认。"
        if timing == "bad":
            return "当前时机偏弱，若必须采购，建议分批建仓以控制追高或抄底风险。"
        return "建议保留分批执行空间，若信号反转可缩减后续采购量。"

    def _build_valid_until(self, current_time: datetime) -> str:
        valid_until = current_time + timedelta(days=1)
        valid_until = valid_until.replace(hour=15, minute=0, second=0, microsecond=0)
        return valid_until.isoformat(timespec="seconds")

    def _format_delta_pct(self, current: float, baseline: float) -> str | None:
        if baseline <= 0:
            return None
        delta_pct = ((current - baseline) / baseline) * 100
        return f"{delta_pct:+.2f}%"
