from __future__ import annotations

import os
import sys
from typing import Any, Dict

import pandas as pd


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from gamma_shock_BYTE import (
    calculate_daily_technical_indicators,
    calculate_technical_indicators,
    detect_futures_signals,
    get_futures_daily_data,
    get_futures_minute_data,
)


class MarketDataAdapter:
    """Thin adapter around the existing market data and signal helpers."""

    def fetch_all(self, symbol: str = "LC0") -> Dict[str, Any]:
        futures_data = get_futures_minute_data(symbol)
        if futures_data is None or futures_data.empty:
            raise RuntimeError(f"Unable to load minute data for {symbol}")

        daily_data = get_futures_daily_data(symbol)

        futures_indicators = calculate_technical_indicators(futures_data)
        daily_indicators = calculate_daily_technical_indicators(daily_data)
        current_price = float(futures_indicators["close"].iloc[-1])

        return {
            "symbol": symbol,
            "futures_data": futures_indicators,
            "daily_data": daily_indicators,
            "current_price": current_price,
        }

    def extract_signal(
        self,
        futures_data: pd.DataFrame,
        daily_data: pd.DataFrame | None,
        symbol: str = "LC",
    ) -> Dict[str, Any]:
        market_data, signal_detected = detect_futures_signals(futures_data, symbol, daily_data)
        if not market_data:
            raise RuntimeError(f"Unable to extract signal for {symbol}")

        daily_current = daily_data.iloc[-1] if daily_data is not None and not daily_data.empty else None

        return {
            "direction": self._normalize_direction(str(market_data.get("signal_type", ""))),
            "strength": int(market_data.get("signal_strength", 0) or 0),
            "confidence": self._estimate_confidence(market_data),
            "description": str(market_data.get("signal_type", "无信号")),
            "indicators": {
                "ema_trend": self._normalize_trend(str(market_data.get("trend_short", "中性"))),
                "macd": self._normalize_macd(market_data),
                "kdj_status": self._normalize_kdj_status(market_data),
                "bollinger_position": self._get_bollinger_percent(market_data, daily_current),
                "volume_ratio": float(market_data.get("vol_ratio", 0.0) or 0.0),
            },
            "signal_detected": bool(signal_detected),
        }

    def _normalize_direction(self, signal_type: str) -> str:
        if any(token in signal_type for token in ("多头", "上涨", "反弹", "突破")):
            return "bullish"
        if any(token in signal_type for token in ("空头", "下跌", "回调", "跌破")):
            return "bearish"
        return "neutral"

    def _normalize_trend(self, trend: str) -> str:
        if trend in {"上涨", "多头", "bullish"}:
            return "bullish"
        if trend in {"下跌", "空头", "bearish"}:
            return "bearish"
        return "neutral"

    def _normalize_macd(self, market_data: Dict[str, Any]) -> str:
        dif = float(market_data.get("DIF", 0.0) or 0.0)
        dea = float(market_data.get("DEA", 0.0) or 0.0)
        if dif > dea:
            return "bullish_crossover"
        if dif < dea:
            return "bearish_crossover"
        return "neutral"

    def _normalize_kdj_status(self, market_data: Dict[str, Any]) -> str:
        k_value = float(market_data.get("K_value", 50.0) or 50.0)
        d_value = float(market_data.get("D_value", 50.0) or 50.0)
        j_value = float(market_data.get("J_value", 50.0) or 50.0)

        if min(k_value, d_value, j_value) < 20:
            return "oversold"
        if max(k_value, d_value, j_value) > 80:
            return "overbought"
        if j_value > k_value > d_value:
            return "bullish"
        if j_value < k_value < d_value:
            return "bearish"
        return "neutral"

    def _get_bollinger_percent(
        self,
        market_data: Dict[str, Any],
        daily_current: pd.Series | None,
    ) -> float:
        if daily_current is not None and "daily_BB_percent" in daily_current:
            value = float(daily_current["daily_BB_percent"])
            return max(0.0, min(1.0, value))

        mapping = {
            "上轨之上": 1.0,
            "中轨之上": 0.75,
            "中轨之下": 0.25,
            "下轨之下": 0.0,
        }
        raw_position = str(market_data.get("bb_position", "中轨之下"))
        return mapping.get(raw_position, 0.5)

    def _estimate_confidence(self, market_data: Dict[str, Any]) -> int:
        strength = int(market_data.get("signal_strength", 0) or 0)
        volume_bonus = 10 if market_data.get("volume_confirmation") else 0
        williams_bonus = 10 if market_data.get("williams_confirmation") else 0
        confidence = (strength * 20) + volume_bonus + williams_bonus
        if strength == 0:
            confidence = 20
        return max(0, min(95, confidence))
