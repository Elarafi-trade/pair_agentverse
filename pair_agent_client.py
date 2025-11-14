"""Lightweight client for the pair-agent API (https://pair-agent-a2ol.onrender.com)

Provides: get_health, fetch_trades, fetch_performance, post_analyze and
formatting helpers for quick integration into uagents or other Python services.

Usage:
    from pair_agent_client import fetch_trades, fetch_performance, post_analyze

    data = fetch_trades()
    perf = fetch_performance()
    analyze = post_analyze('BTC-PERP', 'ETH-PERP')

The base URL can be overridden via the AGENT_API_BASE environment variable.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests
from requests import Response

from dotenv import load_dotenv
load_dotenv()

def _base() -> str:
    return os.environ.get("AGENT_API_BASE", "https://pair-agent-a2ol.onrender.com").rstrip("/")


def _get(url: str, timeout: int = 10) -> Any:
    resp: Response = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _post(url: str, json: dict, timeout: int = 20) -> Any:
    resp: Response = requests.post(url, json=json, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def get_health(timeout: int = 5) -> Dict[str, Any]:
    """Call the /health endpoint and return parsed JSON."""
    return _get(f"{_base()}/health", timeout=timeout)


def fetch_trades(timeout: int = 10) -> Any:
    """Return trades from the agent API (open/closed structure or list)."""
    return _get(f"{_base()}/api/trades", timeout=timeout)


def fetch_performance(timeout: int = 10) -> Any:
    """Return performance summary object."""
    return _get(f"{_base()}/api/performance", timeout=timeout)


def post_analyze(symbolA: str, symbolB: str, limit: int = 200, timeout: int = 20) -> Any:
    """Request analysis for a pair. Auto-appends -PERP if missing.

    Returns the server JSON result.
    """
    def ensure_perp(s: str) -> str:
        s2 = (s or "").upper()
        return s2 if s2.endswith("-PERP") else f"{s2}-PERP"

    body = {"symbolA": ensure_perp(symbolA), "symbolB": ensure_perp(symbolB), "limit": int(limit)}
    return _post(f"{_base()}/api/analyze", body, timeout=timeout)


def fmt_trade(t: dict) -> str:
    """Format a trade dict into a readable multiline string."""
    if not isinstance(t, dict):
        return str(t)

    def clean(sym: Optional[str]) -> str:
        return (sym or "").replace("-PERP", "")

    ts = t.get("timestamp")
    if ts:
        try:
            from datetime import datetime

            ts = datetime.fromisoformat(ts).isoformat(sep=" ", timespec="seconds")
        except Exception:
            ts = str(ts)
    else:
        ts = "N/A"

    upnl = t.get("upnlPct")
    upnl_str = f"{float(upnl):+.4f}%" if upnl is not None else "N/A"
    corr = f"{float(t.get('correlation')):.4f}" if t.get("correlation") is not None else "N/A"
    z = f"{float(t.get('zScore')):.4f}" if t.get("zScore") is not None else "N/A"
    status = (t.get("status") or "open").upper()
    action = t.get("action") or t.get("signal") or "N/A"
    spread = f"{float(t.get('spread')):.4f}" if t.get("spread") is not None else "N/A"
    beta = f"{float(t.get('beta')):.4f}" if t.get("beta") is not None else "N/A"
    vol = f"{float(t.get('volatility')):.4f}" if t.get("volatility") is not None else "N/A"
    longPrice = f"{float(t.get('longPrice')):.4f}" if t.get("longPrice") is not None else "N/A"
    shortPrice = f"{float(t.get('shortPrice')):.4f}" if t.get("shortPrice") is not None else "N/A"

    pair_display = t.get("pair") or f"{clean(t.get('symbolA'))}/{clean(t.get('symbolB'))}"
    long_asset = clean(t.get("longAsset")) or "N/A"
    short_asset = clean(t.get("shortAsset")) or "N/A"

    lines = [
        f"━━━ {pair_display} (ID: {t.get('id','N/A')}) ━━━",
        f"📊 Status: {status} | ⏱️ Timeframe: 1hr",
        f"⚡ Action: {action}",
        f"📈 Z-Score: {z} | Corr: {corr} | Beta: {beta}",
        f"💰 Unrealized PnL: {upnl_str}",
        f"📉 Spread: {spread} | Volatility: {vol}",
        f"💵 Long {long_asset}: {longPrice} | Short {short_asset}: {shortPrice}",
        f"🕐 Opened: {ts}",
    ]

    if t.get("reason"):
        lines.append(f"💡 Reason: {t.get('reason')}")

    if t.get("closeTimestamp"):
        lines.append(f"🕑 Closed: {t.get('closeTimestamp')}")
        if t.get("closeReason"):
            lines.append(f"🔚 Close Reason: {t.get('closeReason')}")
        if t.get("closePnL") is not None:
            try:
                cp = float(t.get("closePnL"))
                lines.append(f"💸 Close PnL: {cp:.4f}%")
            except Exception:
                lines.append(f"💸 Close PnL: {t.get('closePnL')}")

    return "\n".join(lines)


def fmt_performance(p: Optional[dict]) -> str:
    if not p or not isinstance(p, dict):
        return "No performance data yet."

    total_trades = p.get("totalTrades", 0)
    open_trades = p.get("openTrades", 0)
    closed_trades = p.get("closedTrades", 0)
    winning_trades = p.get("winningTrades", 0)
    losing_trades = p.get("losingTrades", 0)

    win_rate = f"{float(p.get('winRate')):.2f}" if p.get("winRate") is not None else "0.00"
    total_return = f"{float(p.get('totalReturnPct')):.4f}" if p.get("totalReturnPct") is not None else "N/A"
    total_return_lev = f"{float(p.get('totalReturnPctLeveraged')):.4f}" if p.get("totalReturnPctLeveraged") is not None else "N/A"
    avg_duration = f"{float(p.get('avgTradeDurationHours')):.2f}" if p.get("avgTradeDurationHours") is not None else "N/A"
    profit_factor = f"{float(p.get('profitFactor')):.4f}" if p.get("profitFactor") is not None else "N/A"
    apy = f"{float(p.get('estimatedAPY')):.2f}" if p.get("estimatedAPY") is not None else "N/A"
    apy_lev = f"{float(p.get('estimatedAPYLeveraged')):.2f}" if p.get("estimatedAPYLeveraged") is not None else "N/A"

    last_updated = p.get("lastUpdated") or "N/A"

    return "\n".join([
        "━━━━━━ 📊 PERFORMANCE SUMMARY ━━━━━━",
        "",
        "📈 Trade Statistics:",
        f"   Total Trades: {total_trades} ({open_trades} open, {closed_trades} closed)",
        f"   Winning: {winning_trades} | Losing: {losing_trades}",
        f"   Win Rate: {win_rate}%",
        "",
        "💰 Returns:",
        f"   Total Return: {total_return}%",
        f"   Total Return (Leveraged): {total_return_lev}%",
        f"   Estimated APY: {apy}%",
        f"   Estimated APY (Leveraged): {apy_lev}%",
        "",
        "📉 Risk Metrics:",
        f"   Profit Factor: {profit_factor}",
        f"   Avg Trade Duration: {avg_duration} hours",
        "",
        f"🕐 Last Updated: {last_updated}",
    ])


if __name__ == "__main__":
    # Quick smoke test when run directly
    try:
        print("pair-agent base:", _base())
        print("Health:", get_health())
    except Exception as e:
        print("pair_agent_client: error during smoke test:", e)
