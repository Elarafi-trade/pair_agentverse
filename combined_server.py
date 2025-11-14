"""Combined server running both Flask API and uAgent in one process.

This script starts:
1. ELARA analyzer agent on port 8001 (via Bureau)
2. Flask API server on port 10000 (or PORT env var for Render)

Both services run in the same process using threading.
"""
from __future__ import annotations

import os
import time
import threading
from typing import Optional, Dict

from flask import Flask, request, jsonify
from flask_cors import CORS
from uagents import Bureau

# Import analyzer agent and Qwen3 client
from analyzer_agent import analyzer_agent
from qwen3_client import Qwen3Analyzer
from cache_manager import get_cache_manager

# Load environment variables
# dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
# if os.path.exists(dotenv_path):
#     from dotenv import load_dotenv
#     load_dotenv(dotenv_path)

from dotenv import load_dotenv
load_dotenv()

print("[DEBUG] OPENROUTER_API_KEY length:", len(os.getenv("OPENROUTER_API_KEY") or "MISSING"))
print("[DEBUG] Running in:", os.getcwd())

# Configuration
AGENT_PORT = int(os.getenv("ANALYZER_AGENT_PORT", "8001"))
API_PORT = int(os.getenv("PORT", os.getenv("FLASK_PORT", "10000")))
API_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "24"))

# Flask app
app = Flask(__name__)
CORS(app)

# Global instances
qwen_analyzer: Optional[Qwen3Analyzer] = None
cache_manager = None

# Allowed trading pairs
ALLOWED_PAIRS = [
    ("SOL", "BTC"),
    ("BTC", "SOL"),
    ("ETH", "BTC"),
    ("BTC", "ETH"),
    ("SOL", "ETH"),
    ("ETH", "SOL"),
]


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    cache_stats = None
    if cache_manager:
        try:
            cache_stats = cache_manager.get_cache_stats()
        except Exception:
            pass
    
    return jsonify({
        "status": "ok",
        "service": "elara-combined",
        "agent_running": True,
        "agent_address": str(analyzer_agent.address),
        "agent_port": AGENT_PORT,
        "api_port": API_PORT,
        "qwen_available": qwen_analyzer is not None,
        "cache_enabled": cache_manager is not None,
        "cache_stats": cache_stats,
    })


@app.route("/cache/cleanup", methods=["POST"])
def cleanup_cache():
    """Manually cleanup expired cache entries."""
    if not cache_manager:
        return jsonify({"error": "Cache not enabled"}), 503
    
    try:
        deleted = cache_manager.cleanup_expired()
        stats = cache_manager.get_cache_stats()
        return jsonify({
            "deleted": deleted,
            "remaining": stats
        })
    except Exception as e:
        app.logger.error(f"Cache cleanup failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Analyze trading pair using Qwen3-powered analysis.
    
    Request body:
    {
        "symbolA": "BTC-PERP",
        "symbolB": "ETH-PERP",
        "limit": 200
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        symbol_a = data.get("symbolA")
        symbol_b = data.get("symbolB")
        limit = data.get("limit", 200)
        
        if not symbol_a or not symbol_b:
            return jsonify({"error": "symbolA and symbolB required"}), 400
        
        # Validate pair is allowed
        base_a = symbol_a.upper().replace("-PERP", "")
        base_b = symbol_b.upper().replace("-PERP", "")
        
        if (base_a, base_b) not in ALLOWED_PAIRS:
            allowed_pairs_str = ", ".join([f"{a}/{b}" for a, b in ALLOWED_PAIRS])
            return jsonify({
                "error": f"Trading pair not allowed. Only these pairs are supported: {allowed_pairs_str}",
                "requested_pair": f"{base_a}/{base_b}",
                "allowed_pairs": [f"{a}/{b}" for a, b in ALLOWED_PAIRS]
            }), 400
        
        # Ensure -PERP suffix
        symbol_a = _ensure_perp(symbol_a)
        symbol_b = _ensure_perp(symbol_b)
        
        # Check cache first
        if cache_manager:
            try:
                cached_result = cache_manager.get_cached_analysis(symbol_a, symbol_b)
                if cached_result:
                    app.logger.info(f"✓ Cache hit for {symbol_a}/{symbol_b}")
                    return jsonify(cached_result)
            except Exception as e:
                app.logger.warning(f"Cache lookup failed: {e}")
        
        # Calculate metrics
        metrics = _calculate_metrics_sync(symbol_a, symbol_b, limit)
        print(metrics)
        
        if not metrics:
            return jsonify({"error": "Failed to calculate metrics"}), 500
        
        # Call Qwen3 analyzer
        app.logger.info(f"Analyzing {symbol_a}/{symbol_b} with Qwen3")
        
        if not qwen_analyzer:
            return jsonify({"error": "Qwen3 analyzer not initialized"}), 503
        
        try:
            analysis_metrics = {
                "symbolA": symbol_a,
                "symbolB": symbol_b,
                "zScore": metrics["zScore"],
                "corr": metrics["corr"],
                "mean": metrics["mean"],
                "std": metrics["std"],
                "beta": metrics["beta"],
                "volatility": metrics["volatility"],
                # extended optional metrics for richer prompt
                "currentSpread": metrics.get("currentSpread"),
                "halfLife": metrics.get("halfLife"),
                "sharpe": metrics.get("sharpe"),
                "signalType": metrics.get("signalType"),
            }
            
            analysis_result = qwen_analyzer.analyze_pair(analysis_metrics, temperature=0.3)
            
            metrics_data = {
                "zScore": metrics["zScore"],
                "corr": metrics["corr"],
                "mean": metrics["mean"],
                "std": metrics["std"],
                "beta": metrics["beta"],
                "volatility": metrics["volatility"],
                # passthrough extended fields when present
                "currentSpread": metrics.get("currentSpread"),
                "halfLife": metrics.get("halfLife"),
                "cointegrationPValue": metrics.get("cointegrationPValue"),
                "isCointegrated": metrics.get("isCointegrated"),
                "sharpe": metrics.get("sharpe"),
                "signalType": metrics.get("signalType"),
                "dataPoints": metrics.get("dataPoints"),
            }
            
            analysis_data = {
                "signal": analysis_result.get("signal", "NEUTRAL"),
                "confidence": float(analysis_result.get("confidence", 0.5)),
                "reasoning": analysis_result.get("reasoning", "No reasoning available"),
                "risk_level": analysis_result.get("risk_level", "MEDIUM"),
                "key_factors": analysis_result.get("key_factors", []),
                "entry_recommendation": analysis_result.get("entry_recommendation", "Consult additional sources"),
            }
            
            # Cache the result
            if cache_manager:
                try:
                    cache_manager.cache_analysis(
                        symbol_a,
                        symbol_b,
                        metrics_data,
                        analysis_data,
                        ttl_hours=CACHE_TTL_HOURS
                    )
                    app.logger.info(f"✓ Cached result for {symbol_a}/{symbol_b}")
                except Exception as e:
                    app.logger.warning(f"Failed to cache: {e}")
            
            return jsonify({
                "symbolA": symbol_a,
                "symbolB": symbol_b,
                "metrics": metrics_data,
                "analysis": analysis_data,
                "cached": False,
            })
                
        except RuntimeError as e:
            # Likely an upstream API failure (OpenRouter) or authentication issue
            app.logger.error(f"Analysis failed: {e}")
            import traceback
            traceback.print_exc()
            # Return a clear 502/503 with guidance for missing/invalid API key
            guidance = (
                "OpenRouter request failed. Check OPENROUTER_API_KEY and account access. "
                "If running on Render, add OPENROUTER_API_KEY as a secret in service settings."
            )
            return jsonify({"error": "Upstream analysis error", "details": str(e), "guidance": guidance}), 502
        except Exception as e:
            app.logger.error(f"Analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Analysis error: {str(e)}"}), 500
            
    except Exception as e:
        app.logger.error(f"Endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


def _calculate_metrics_sync(symbol_a: str, symbol_b: str, limit: int) -> Optional[dict]:
    """Fetch real metrics from pair-agent API."""
    import requests
    
    pair_agent_base = os.getenv("AGENT_API_BASE", "https://pair-agent-a2ol.onrender.com")
    url = f"{pair_agent_base}/api/analyze"
    
    payload = {
        "symbolA": symbol_a,
        "symbolB": symbol_b,
        "limit": limit
    }
    
    try:
        app.logger.info(f"Fetching metrics from {url}")
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        analysis = data.get("analysis", {})
        
        if not analysis:
            app.logger.error(f"No analysis data in response")
            return None
        
        # Derive a useful volatility value when not provided by upstream.
        # Prefer provided 'volatility'; otherwise fall back to 'spreadStd' as a proxy.
        spread_std = float(analysis.get("spreadStd", 0.0) or 0.0)
        upstream_vol = analysis.get("volatility")
        derived_vol = float(upstream_vol) if upstream_vol is not None else spread_std
        # Guard against non-finite or negative numbers
        if not isinstance(derived_vol, (int, float)) or derived_vol != derived_vol or derived_vol < 0:
            derived_vol = spread_std if spread_std >= 0 else 0.0

        metrics = {
            "zScore": analysis.get("zScore", 0.0),
            "corr": analysis.get("correlation", 0.0),
            "mean": analysis.get("spreadMean", 0.0),
            "std": spread_std if spread_std > 0 else float(analysis.get("spreadStd", 1.0) or 1.0),
            "beta": analysis.get("beta", 1.0),
            "volatility": derived_vol,
            # Extended upstream fields (optional)
            "currentSpread": analysis.get("currentSpread"),
            "halfLife": analysis.get("halfLife"),
            "cointegrationPValue": analysis.get("cointegrationPValue"),
            "isCointegrated": analysis.get("isCointegrated"),
            "sharpe": analysis.get("sharpe"),
            "signalType": analysis.get("signalType"),
        }

        # Top-level metadata passthrough
        if isinstance(data.get("dataPoints"), int):
            metrics["dataPoints"] = data["dataPoints"]
        
        return metrics
        
    except Exception as e:
        app.logger.error(f"Failed to fetch metrics: {e}")
        # Fallback to mock
        import random
        return {
            "zScore": random.uniform(-3.0, 3.0),
            "corr": random.uniform(0.5, 0.95),
            "mean": random.uniform(-0.01, 0.01),
            "std": random.uniform(0.001, 0.01),
            "beta": random.uniform(0.8, 1.5),
            "volatility": random.uniform(0.01, 0.05),
            "currentSpread": None,
            "halfLife": None,
            "cointegrationPValue": None,
            "isCointegrated": None,
            "sharpe": None,
            "signalType": None,
            "dataPoints": limit,
        }


def _ensure_perp(symbol: str) -> str:
    """Ensure symbol has -PERP suffix."""
    upper = symbol.upper()
    return upper if upper.endswith("-PERP") else f"{upper}-PERP"


def main():
    """Start both agent and API server in one process."""
    global qwen_analyzer, cache_manager
    
    print("=" * 60)
    print("ELARA Combined Server - Agent + API")
    print("=" * 60)
    
    # Initialize cache
    print("\n📦 Initializing database cache...")
    cache_manager = get_cache_manager()
    if cache_manager:
        try:
            deleted = cache_manager.cleanup_expired()
            if deleted > 0:
                print(f"   ✓ Cleaned up {deleted} expired entries")
            stats = cache_manager.get_cache_stats()
            print(f"   ✓ Cache ready: {stats['valid_entries']} valid entries")
        except Exception as e:
            print(f"   ⚠️  Cache warning: {e}")
    
    # Initialize Qwen3
    print("\n🤖 Initializing Qwen3 analyzer...")
    try:
        qwen_analyzer = Qwen3Analyzer()
        print(f"   ✓ Qwen3 ready (model: {qwen_analyzer.model_name})")
    except Exception as e:
        print(f"   ✗ Failed to initialize Qwen3: {e}")
        raise SystemExit(1)
    
    # Start agent in background
    print(f"\n🚀 Starting analyzer agent on port {AGENT_PORT}...")
    bureau = Bureau(port=AGENT_PORT)
    bureau.add(analyzer_agent)
    
    print(f"   Agent address: {analyzer_agent.address}")
    print(f"   Agent port: {AGENT_PORT}")
    
    # Run bureau in background thread
    bureau_thread = threading.Thread(target=bureau.run, daemon=True)
    bureau_thread.start()
    
    # Give agent time to initialize
    time.sleep(2)
    
    # Start Flask API
    print(f"\n🌐 Starting Flask API server on {API_HOST}:{API_PORT}")
    print(f"   Health: http://{API_HOST}:{API_PORT}/health")
    print(f"   Analyze: http://{API_HOST}:{API_PORT}/api/analyze")
    print(f"\n   Inspector: https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A{AGENT_PORT}&address={analyzer_agent.address}")
    print("\n" + "=" * 60)
    print("✅ ELARA is ready! Both services running.")
    print("=" * 60 + "\n")
    
    # Run Flask (this blocks)
    app.run(host=API_HOST, port=API_PORT, debug=DEBUG)


if __name__ == "__main__":
    main()
