from __future__ import annotations

import copy
from datetime import datetime, timedelta
from typing import Any


class BatteryMonitor:
    def __init__(self, cooldown_hours: int = 2, history_hours: int = 24):
        self.cooldown_hours = cooldown_hours
        self.history_hours = history_hours

    def monitor_cycle(
        self,
        snapshot: dict[str, Any],
        memory: dict[str, Any] | None = None,
        now: datetime | None = None,
        trading_hours: bool = True,
    ) -> dict[str, Any]:
        current_time = now or datetime.now()
        state = copy.deepcopy(memory or {})

        if not trading_hours:
            return {
                "schedule": "next_open",
                "should_push": False,
                "reason": "outside_trading_hours",
                "memory": state,
                "evolution": {},
                "report": None,
            }

        signal = snapshot.get("signal", {})
        direction = signal.get("direction", "neutral")
        strength = int(signal.get("strength", 0) or 0)
        previous_direction = state.get("last_direction")
        previous_strength = int(state.get("last_strength", 0) or 0)
        direction_changed = previous_direction is not None and direction != previous_direction

        if previous_direction == direction and previous_direction is not None:
            consecutive_count = int(state.get("consecutive_count", 0) or 0) + 1
            consecutive_since = state.get("consecutive_since") or current_time.isoformat(timespec="seconds")
        else:
            consecutive_count = 1
            consecutive_since = current_time.isoformat(timespec="seconds")

        evolution = {
            "direction_changed": direction_changed,
            "strength_delta": strength - previous_strength,
            "consecutive": consecutive_count,
        }

        updated_memory = self._build_updated_memory(
            state=state,
            snapshot=snapshot,
            direction=direction,
            strength=strength,
            current_time=current_time,
            consecutive_count=consecutive_count,
            consecutive_since=consecutive_since,
            evolution=evolution,
        )

        should_push, reason = self._evaluate_push(
            direction_changed=direction_changed,
            strength=strength,
            consecutive_count=consecutive_count,
            current_time=current_time,
            last_push_time=state.get("last_push_time"),
        )

        if should_push:
            updated_memory["last_push_time"] = current_time.isoformat(timespec="seconds")

        report = None
        if should_push:
            report = self._format_report(snapshot, evolution, reason)

        return {
            "schedule": "15min",
            "should_push": should_push,
            "reason": reason,
            "memory": updated_memory,
            "evolution": evolution,
            "report": report,
        }

    def _build_updated_memory(
        self,
        state: dict[str, Any],
        snapshot: dict[str, Any],
        direction: str,
        strength: int,
        current_time: datetime,
        consecutive_count: int,
        consecutive_since: str,
        evolution: dict[str, Any],
    ) -> dict[str, Any]:
        history = list(state.get("signal_history_24h", []))
        history.append(
            {
                "time": current_time.isoformat(timespec="seconds"),
                "direction": direction,
                "strength": strength,
                "price": snapshot.get("price", {}).get("current"),
            }
        )
        history = self._trim_history(history, current_time)

        updated = copy.deepcopy(state)
        updated.update(
            {
                "last_check": current_time.isoformat(timespec="seconds"),
                "last_direction": direction,
                "last_strength": strength,
                "consecutive_count": consecutive_count,
                "consecutive_since": consecutive_since,
                "signal_history_24h": history,
                "last_cost_change_pct": snapshot.get("cost", {}).get("change_pct"),
                "last_evolution": evolution,
            }
        )
        return updated

    def _trim_history(self, history: list[dict[str, Any]], current_time: datetime) -> list[dict[str, Any]]:
        cutoff = current_time - timedelta(hours=self.history_hours)
        trimmed = []
        for item in history:
            item_time = self._parse_iso(item.get("time"))
            if item_time is None or item_time >= cutoff:
                trimmed.append(item)
        return trimmed

    def _evaluate_push(
        self,
        direction_changed: bool,
        strength: int,
        consecutive_count: int,
        current_time: datetime,
        last_push_time: str | None,
    ) -> tuple[bool, str]:
        if direction_changed:
            return True, "direction_changed"

        cooldown_active = self._recently_pushed(last_push_time, current_time)

        if strength >= 4:
            if cooldown_active:
                return False, "cooldown_active"
            return True, "strong_signal"

        if consecutive_count >= 3:
            if cooldown_active:
                return False, "cooldown_active"
            return True, "consecutive_confirmation"

        return False, "no_push_condition"

    def _recently_pushed(self, last_push_time: str | None, current_time: datetime) -> bool:
        previous_push = self._parse_iso(last_push_time)
        if previous_push is None:
            return False
        return current_time - previous_push < timedelta(hours=self.cooldown_hours)

    def _format_report(self, snapshot: dict[str, Any], evolution: dict[str, Any], reason: str) -> str:
        direction = snapshot.get("signal", {}).get("direction", "neutral")
        strength = snapshot.get("signal", {}).get("strength", 0)
        price = snapshot.get("price", {}).get("current")
        cost_change_pct = snapshot.get("cost", {}).get("change_pct")

        headline_map = {
            "direction_changed": "方向反转",
            "strong_signal": "强信号确认",
            "consecutive_confirmation": "连续确认",
        }
        headline = headline_map.get(reason, "监控更新")

        return (
            f"{headline}: 价格 {price}, 方向 {direction}, 强度 {strength}, "
            f"成本变化 {cost_change_pct}%, 连续次数 {evolution.get('consecutive', 1)}"
        )

    def _parse_iso(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
