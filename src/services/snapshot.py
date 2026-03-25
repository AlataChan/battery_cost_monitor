from __future__ import annotations

import copy
import os
import sys
import threading
from datetime import datetime, timedelta
from typing import Any, Dict


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CORE_DIR = os.path.join(PROJECT_ROOT, "src", "core")

for path in (PROJECT_ROOT, CORE_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from cost_calculator import BatteryCostCalculator
from src.core.price_predictor import PricePredictor

try:
    from .data_adapter import MarketDataAdapter
except ImportError:
    from data_adapter import MarketDataAdapter


class AnalysisSnapshot:
    """Builds and caches a structured analysis snapshot for API consumers."""

    def __init__(self, symbol: str = "LC0"):
        self.symbol = symbol
        self._adapter = MarketDataAdapter()
        self._calculator = BatteryCostCalculator()
        self._predictor = PricePredictor()
        self._cache: Dict[str, Any] | None = None
        self._cache_time: datetime | None = None
        self._cache_ttl = int(os.getenv("SNAPSHOT_CACHE_TTL", "300"))
        self._lock = threading.Lock()

    def get_snapshot(self, force_refresh: bool = False) -> Dict[str, Any]:
        with self._lock:
            if not force_refresh and self._cache and not self._is_expired():
                return copy.deepcopy(self._cache)

            try:
                snapshot = self._build_snapshot()
            except Exception as exc:
                if self._cache:
                    stale_snapshot = copy.deepcopy(self._cache)
                    stale_snapshot["stale"] = True
                    stale_snapshot["error_message"] = str(exc)
                    return stale_snapshot
                raise

            self._cache = snapshot
            self._cache_time = datetime.now()
            return copy.deepcopy(snapshot)

    def get_cache_status(self) -> Dict[str, Any]:
        now = datetime.now()
        age_seconds = None
        if self._cache_time is not None:
            age_seconds = max(0, int((now - self._cache_time).total_seconds()))

        return {
            "cached": self._cache is not None,
            "cached_at": self._cache_time.isoformat(timespec="seconds") if self._cache_time else None,
            "age_seconds": age_seconds,
            "ttl_seconds": self._cache_ttl,
        }

    def _is_expired(self) -> bool:
        if self._cache_time is None:
            return True
        return datetime.now() >= self._cache_time + timedelta(seconds=self._cache_ttl)

    def _build_snapshot(self) -> Dict[str, Any]:
        now = datetime.now()
        market_data = self._adapter.fetch_all(self.symbol)
        signal = self._adapter.extract_signal(
            market_data["futures_data"],
            market_data["daily_data"],
            self._material_symbol,
        )
        cost = self._build_cost(market_data["current_price"])
        combined_prediction = self._build_prediction(
            market_data["futures_data"],
            market_data["daily_data"],
        )

        snapshot_time = now.isoformat(timespec="seconds")
        prediction = self._map_prediction(combined_prediction)
        ai_analysis = self._map_ai_analysis(combined_prediction)

        return {
            "timestamp": snapshot_time,
            "data_source": f"akshare_futures_{self.symbol}",
            "price": {
                "current": market_data["current_price"],
                "unit": "元/吨",
            },
            "signal": signal,
            "cost": cost,
            "prediction": prediction,
            "ai_analysis": ai_analysis,
            "snapshot_cached_at": snapshot_time,
            "snapshot_ttl_seconds": self._cache_ttl,
            "stale": False,
        }

    @property
    def _material_symbol(self) -> str:
        return self.symbol.rstrip("0123456789") or self.symbol

    def _build_cost(self, current_price: float) -> Dict[str, Any]:
        material_config = self._calculator.config["materials"][self._material_symbol]
        material_cost = self._calculator._calculate_material_cost(
            self._material_symbol,
            material_config,
            current_price,
        )
        total_cost = float(material_cost["current_cost"])
        baseline_total = float(self._calculator.config["baseline_total_cost"])
        change = total_cost - baseline_total
        change_pct = (change / baseline_total) * 100 if baseline_total else 0.0

        return {
            "total_per_pack": total_cost,
            "baseline_per_pack": baseline_total,
            "change": change,
            "change_pct": change_pct,
            "unit": f"元/pack({int(material_cost['usage'])}kg {self._material_symbol})",
            "materials": {
                self._material_symbol: {
                    "name": material_cost["name"],
                    "price": current_price,
                    "usage_kg": material_cost["usage"],
                    "cost": total_cost,
                }
            },
        }

    def _build_prediction(self, futures_data, daily_data) -> Dict[str, Any]:
        technical_prediction = self._predictor._generate_prediction(
            self._material_symbol,
            futures_data,
            daily_data,
        )
        ai_analysis = self._predictor._get_ai_analysis(self._material_symbol, technical_prediction)
        return self._predictor._combine_predictions(technical_prediction, ai_analysis)

    def _map_prediction(self, combined_prediction: Dict[str, Any]) -> Dict[str, Any]:
        price_prediction = combined_prediction.get("price_prediction", {})
        technical_analysis = combined_prediction.get("technical_analysis", {})
        ai_data = combined_prediction.get("ai_mentor_analysis", {})
        lower = price_prediction.get("confidence_lower", combined_prediction.get("current_price", 0.0))
        upper = price_prediction.get("confidence_upper", combined_prediction.get("current_price", 0.0))

        return {
            "direction": self._normalize_prediction_direction(
                technical_analysis.get("overall_signal", "neutral"),
                combined_prediction.get("trend_prediction", {}).get("trend_direction", "down"),
            ),
            "price_range_7d": [lower, upper] if lower <= upper else [upper, lower],
            "confidence": round(float(combined_prediction.get("confidence", 0.0)), 2),
            "ai_summary": ai_data.get("ai_analysis") or ai_data.get("message"),
        }

    def _map_ai_analysis(self, combined_prediction: Dict[str, Any]) -> Dict[str, Any]:
        ai_data = combined_prediction.get("ai_mentor_analysis", {})
        risk_assessment = ai_data.get("risk_assessment", {})

        return {
            "trend_judgment": ai_data.get("ai_analysis") or ai_data.get("message"),
            "risk_level": self._normalize_risk_level(risk_assessment.get("risk_level", "中")),
            "market_sentiment": self._normalize_market_sentiment(ai_data.get("market_sentiment", "中性")),
            "key_factors": risk_assessment.get("risk_factors", []),
        }

    def _normalize_prediction_direction(self, signal: str, trend_direction: str) -> str:
        if signal == "bullish" and trend_direction == "up":
            return "bullish"
        if signal == "bearish" and trend_direction == "down":
            return "bearish"
        if signal == "bullish":
            return "neutral_to_bullish"
        if signal == "bearish":
            return "neutral_to_bearish"
        return "neutral"

    def _normalize_risk_level(self, risk_level: str) -> str:
        mapping = {"高": "high", "中": "medium", "低": "low"}
        return mapping.get(risk_level, "medium")

    def _normalize_market_sentiment(self, sentiment: str) -> str:
        mapping = {
            "看涨": "bullish",
            "看跌": "bearish",
            "震荡": "rangebound",
            "中性": "neutral",
        }
        return mapping.get(sentiment, "neutral")
