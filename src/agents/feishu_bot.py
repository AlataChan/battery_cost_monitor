#!/usr/bin/env python3
"""
飞书机器人 — 基于 WebSocket 长连接模式
接收用户消息，调用 BatteryAI API + Agent 逻辑，回复分析结果
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    P2ImMessageReceiveV1,
    ReplyMessageRequest,
    ReplyMessageRequestBody,
)
from lark_oapi.ws import Client as WsClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.battery_monitor import BatteryMonitor
from src.agents.common import call_json_api, load_json_file, save_json_file
from src.agents.procurement_advisor import ProcurementAdvisor

logger = logging.getLogger(__name__)

# ── 配置 ──

APP_ID = os.getenv("FEISHU_APP_ID", "")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
API_BASE_URL = os.getenv("BATTERY_API_BASE_URL", "http://127.0.0.1:5001")
API_KEY = os.getenv("API_KEY", "")
MEMORY_PATH = os.getenv("BATTERY_MONITOR_MEMORY_PATH", "data/agent_state/battery_signals.json")
CONTEXT_PATH = os.getenv("PROCUREMENT_CONTEXT_PATH", "data/agent_state/procurement_context.json")
DECISION_LOG_PATH = os.getenv("PROCUREMENT_DECISION_LOG_PATH", "data/agent_state/procurement_decisions.jsonl")

# ── 全局实例 ──

api_client: lark.Client | None = None
monitor = BatteryMonitor()
advisor = ProcurementAdvisor()

# ── 意图识别 ──

INTENT_KEYWORDS = {
    "price": ["价格", "多少钱", "碳酸锂", "锂价", "行情", "报价"],
    "signal": ["信号", "趋势", "方向", "看涨", "看跌", "买卖"],
    "cost": ["成本", "cost", "pack", "电池成本"],
    "monitor": ["监控", "巡检", "检查一下", "monitor"],
    "buy": ["该买吗", "采购", "买入", "建议", "要不要买", "procurement"],
    "help": ["帮助", "help", "你能做什么", "功能"],
}


def detect_intent(text: str) -> str:
    text_lower = text.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return intent
    return "general"


# ── API 调用 ──

def get_snapshot() -> dict:
    url = f"{API_BASE_URL.rstrip('/')}/api/latest"
    return call_json_api(url, api_key=API_KEY)


def format_price_reply(snapshot: dict) -> str:
    price = snapshot.get("price", {})
    signal = snapshot.get("signal", {})
    cost = snapshot.get("cost", {})
    ts = snapshot.get("timestamp", "")

    return (
        f"**碳酸锂实时行情** ({ts})\n\n"
        f"当前价格: **{price.get('current', 'N/A')}** 元/吨\n"
        f"信号方向: {signal.get('direction', 'N/A')} | 强度: {signal.get('strength', 'N/A')}\n"
        f"电池成本: {cost.get('total_per_pack', 'N/A')} 元/pack\n"
        f"成本变化: {cost.get('change_pct', 'N/A')}%"
    )


def format_signal_reply(snapshot: dict) -> str:
    signal = snapshot.get("signal", {})
    indicators = signal.get("indicators", {})
    prediction = snapshot.get("prediction", {})
    ai = snapshot.get("ai_analysis", {})

    return (
        f"**技术信号分析**\n\n"
        f"方向: **{signal.get('direction', 'N/A')}** | 强度: {signal.get('strength', 0)}\n"
        f"置信度: {signal.get('confidence', 0)}%\n"
        f"描述: {signal.get('description', 'N/A')}\n\n"
        f"**技术指标**\n"
        f"EMA趋势: {indicators.get('ema_trend', 'N/A')}\n"
        f"MACD: {indicators.get('macd', 'N/A')}\n"
        f"KDJ: {indicators.get('kdj_status', 'N/A')}\n"
        f"布林带: {indicators.get('bollinger_position', 'N/A')}\n"
        f"量比: {indicators.get('volume_ratio', 'N/A')}\n\n"
        f"**预测**: {prediction.get('direction', 'N/A')} "
        f"(置信度 {prediction.get('confidence', 0)}%)\n"
        f"**AI研判**: {ai.get('market_sentiment', 'N/A')} | "
        f"风险: {ai.get('risk_level', 'N/A')}"
    )


def format_cost_reply(snapshot: dict) -> str:
    cost = snapshot.get("cost", {})
    materials = cost.get("materials", {})
    lc = materials.get("LC", {})

    return (
        f"**电池成本分析**\n\n"
        f"材料: {lc.get('name', '碳酸锂')}\n"
        f"价格: {lc.get('price', 'N/A')} 元/吨\n"
        f"用量: {lc.get('usage_kg', 40)} kg/pack\n"
        f"单pack成本: **{cost.get('total_per_pack', 'N/A')}** 元\n"
        f"基准成本: {cost.get('baseline_per_pack', 'N/A')} 元\n"
        f"变化: {cost.get('change', 'N/A')} 元 ({cost.get('change_pct', 'N/A')}%)"
    )


def format_monitor_reply(snapshot: dict) -> str:
    memory = load_json_file(MEMORY_PATH, {})
    now = datetime.now()

    result = monitor.monitor_cycle(
        snapshot=snapshot,
        memory=memory,
        now=now,
        trading_hours=True,
    )
    save_json_file(MEMORY_PATH, result["memory"])

    evolution = result.get("evolution", {})
    mem = result.get("memory", {})

    text = (
        f"**监控巡检结果**\n\n"
        f"信号方向: {mem.get('last_direction', 'N/A')}\n"
        f"信号强度: {mem.get('last_strength', 0)}\n"
        f"连续确认: {mem.get('consecutive_count', 0)} 次\n"
        f"方向变化: {'是' if evolution.get('direction_changed') else '否'}\n"
        f"需要推送: {'是' if result.get('should_push') else '否'}\n"
        f"原因: {result.get('reason', 'N/A')}\n"
        f"下次检查: {result.get('schedule', '15min')}"
    )
    if result.get("report"):
        text += f"\n\n**报告**: {result['report']}"
    return text


def format_buy_reply(snapshot: dict) -> str:
    context = advisor.load_context(CONTEXT_PATH)
    if not context or not context.get("monthly_demand_tons"):
        return (
            "**采购建议**\n\n"
            "还没有设置业务上下文。请先告诉我：\n"
            "1. 月需求量（吨）\n"
            "2. 当前库存（吨）\n"
            "3. 剩余预算（元）\n\n"
            "例如发送：\n`设置 月需求200 库存50 预算3000万`"
        )

    decision = advisor.generate_advice(
        snapshot=snapshot,
        context=context,
        decision_log_path=DECISION_LOG_PATH,
    )

    return (
        f"**采购决策建议** (需人工确认)\n\n"
        f"建议: **{decision.get('summary', 'N/A')}**\n"
        f"动作: {decision.get('action', 'N/A')}\n"
        f"数量: {decision.get('quantity_tons', 0)} 吨\n"
        f"置信度: {decision.get('confidence', 0)}%\n\n"
        f"**推理过程**\n"
        f"紧迫度: {decision.get('reasoning', {}).get('urgency', 'N/A')}\n"
        f"时机: {decision.get('reasoning', {}).get('timing', 'N/A')}\n"
        f"矩阵: {decision.get('reasoning', {}).get('matrix_cell', 'N/A')}\n\n"
        f"**价格参考**\n"
        f"当前价: {decision.get('price_context', {}).get('current_price', 'N/A')} 元/吨\n"
        f"vs上次采购: {decision.get('price_context', {}).get('vs_last_purchase', 'N/A')}\n"
        f"vs三月均价: {decision.get('price_context', {}).get('vs_3month_avg', 'N/A')}\n\n"
        f"**风险提示**: {decision.get('risk_note', 'N/A')}\n"
        f"有效期至: {decision.get('valid_until', 'N/A')}"
    )


HELP_TEXT = (
    "**BatteryAI 碳酸锂智能助手**\n\n"
    "你可以问我：\n"
    "- **价格** — 碳酸锂多少钱？/ 锂价行情\n"
    "- **信号** — 技术信号 / 趋势分析\n"
    "- **成本** — 电池成本 / pack成本\n"
    "- **监控** — 检查一下 / 巡检\n"
    "- **采购** — 该买吗 / 采购建议\n"
    "- **帮助** — 查看此菜单\n\n"
    "设置采购上下文：\n"
    "`设置 月需求200 库存50 预算3000万`"
)


# ── 设置业务上下文解析 ──

def try_parse_context_update(text: str) -> dict | None:
    """尝试从消息中解析业务上下文设置"""
    if "设置" not in text and "设定" not in text:
        return None

    import re
    context_update = {}

    demand_match = re.search(r"月需求\s*(\d+)", text)
    if demand_match:
        context_update["monthly_demand_tons"] = float(demand_match.group(1))

    inventory_match = re.search(r"库存\s*(\d+)", text)
    if inventory_match:
        context_update["inventory_tons"] = float(inventory_match.group(1))

    budget_match = re.search(r"预算\s*(\d+)\s*万", text)
    if budget_match:
        context_update["budget_remaining"] = float(budget_match.group(1)) * 10000
    else:
        budget_match = re.search(r"预算\s*(\d+)", text)
        if budget_match:
            context_update["budget_remaining"] = float(budget_match.group(1))

    if not context_update:
        return None

    context_update["updated_at"] = datetime.now().isoformat(timespec="seconds")
    return context_update


# ── 消息处理 ──

def handle_message(data: P2ImMessageReceiveV1) -> None:
    msg = data.event.message

    if msg.message_type != "text":
        reply_text(msg.message_id, "暂时只支持文本消息哦")
        return

    text = json.loads(msg.content).get("text", "").strip()
    if not text:
        return

    # 检查是否是设置上下文
    context_update = try_parse_context_update(text)
    if context_update:
        existing = advisor.load_context(CONTEXT_PATH)
        existing.update(context_update)
        advisor.save_context(CONTEXT_PATH, existing)
        reply_text(
            msg.message_id,
            f"**业务上下文已更新**\n\n"
            f"月需求: {existing.get('monthly_demand_tons', 'N/A')} 吨\n"
            f"库存: {existing.get('inventory_tons', 'N/A')} 吨\n"
            f"预算: {existing.get('budget_remaining', 'N/A')} 元",
        )
        return

    # 意图识别
    intent = detect_intent(text)

    try:
        if intent == "help":
            reply_text(msg.message_id, HELP_TEXT)
            return

        # 需要 API 数据的意图
        snapshot = get_snapshot()

        reply_map = {
            "price": format_price_reply,
            "signal": format_signal_reply,
            "cost": format_cost_reply,
            "monitor": format_monitor_reply,
            "buy": format_buy_reply,
        }

        formatter = reply_map.get(intent)
        if formatter:
            reply_text(msg.message_id, formatter(snapshot))
        else:
            # 通用查询：返回价格概览
            reply_text(msg.message_id, format_price_reply(snapshot))

    except Exception as exc:
        logger.error(f"处理消息出错: {exc}", exc_info=True)
        reply_text(msg.message_id, f"出错了: {exc}")


def reply_text(message_id: str, text: str) -> None:
    if api_client is None:
        logger.error("API client not initialized")
        return

    request = (
        ReplyMessageRequest.builder()
        .message_id(message_id)
        .request_body(
            ReplyMessageRequestBody.builder()
            .msg_type("text")
            .content(json.dumps({"text": text}))
            .build()
        )
        .build()
    )

    response = api_client.im.v1.message.reply(request)
    if response.code != 0:
        logger.error(f"飞书回复失败: code={response.code}, msg={response.msg}")


# ── 启动 ──

def start():
    global api_client

    if not APP_ID or not APP_SECRET:
        print("错误: 请在 .env 中设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        sys.exit(1)

    print(f"BatteryAI 飞书机器人启动中...")
    print(f"API 地址: {API_BASE_URL}")
    print(f"APP_ID: {APP_ID[:8]}...")

    # HTTP API 客户端（用于发送消息）
    api_client = (
        lark.Client.builder()
        .app_id(APP_ID)
        .app_secret(APP_SECRET)
        .log_level(lark.LogLevel.INFO)
        .build()
    )

    # 事件处理器
    event_handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(handle_message)
        .build()
    )

    # WebSocket 长连接客户端
    ws_client = WsClient(
        app_id=APP_ID,
        app_secret=APP_SECRET,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO,
        auto_reconnect=True,
    )

    print("已连接飞书，等待消息...")
    ws_client.start()


if __name__ == "__main__":
    start()
