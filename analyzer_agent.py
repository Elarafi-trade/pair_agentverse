"""Trade Analyzer uAgent with Qwen3 integration.

This agent receives analysis requests via uAgents protocol and uses
Qwen3 for detailed reasoning and confidence scoring.
"""
from __future__ import annotations

import os
from typing import Optional
from uagents import Agent, Context, Model, Protocol
from qwen3_client import Qwen3Analyzer


# Message models for analysis protocol
class AnalyzeRequest(Model):
    """Request to analyze a trading pair."""
    symbolA: str
    symbolB: str
    zScore: float
    correlation: float
    spread_mean: float
    spread_std: float
    beta: float
    volatility: Optional[float] = 0.0
    limit: Optional[int] = 200


class AnalysisResponse(Model):
    """Response with detailed Qwen3 analysis."""
    symbolA: str
    symbolB: str
    signal: str  # LONG, SHORT, NEUTRAL
    confidence: float  # 0.0 to 1.0
    reasoning: str
    risk_level: str  # LOW, MEDIUM, HIGH
    key_factors: list[str]
    entry_recommendation: str
    # Original metrics for reference
    zScore: float
    correlation: float
    spread_mean: float
    spread_std: float
    beta: float


# Create analyzer agent
AGENT_SEED = os.getenv("ANALYZER_AGENT_SEED", "analyzer_agent_seed_phrase_change_me")
AGENT_PORT = int(os.getenv("ANALYZER_AGENT_PORT", "8001"))
AGENT_ENDPOINT = os.getenv("ANALYZER_AGENT_ENDPOINT", f"http://localhost:{AGENT_PORT}/submit")

analyzer_agent = Agent(
    name="trade_analyzer",
    seed=AGENT_SEED,
    port=AGENT_PORT,
    endpoint=AGENT_ENDPOINT,
)

# Initialize Qwen3 client (stored in agent's storage for reuse)
qwen_analyzer: Optional[Qwen3Analyzer] = None


@analyzer_agent.on_event("startup")
async def initialize_qwen(ctx: Context):
    """Initialize Qwen3 model on agent startup."""
    global qwen_analyzer
    ctx.logger.info("Initializing Qwen3 analyzer with OpenRouter...")
    
    try:
        qwen_analyzer = Qwen3Analyzer()
        ctx.logger.info(f"✓ Qwen3 analyzer ready (model: {qwen_analyzer.model_name})")
    except Exception as e:
        ctx.logger.error(f"✗ Failed to initialize Qwen3: {e}")
        raise RuntimeError("Qwen3 initialization failed - check OPENROUTER_API_KEY in .env")


# Analysis protocol
analysis_protocol = Protocol(name="TradeAnalysis", version="1.0")


@analysis_protocol.on_message(model=AnalyzeRequest)
async def handle_analyze_request(ctx: Context, sender: str, msg: AnalyzeRequest):
    """Handle incoming analysis request with Qwen3 reasoning."""
    ctx.logger.info(f"Received analysis request from {sender}: {msg.symbolA}/{msg.symbolB}")
    
    if not qwen_analyzer:
        ctx.logger.error("Qwen3 analyzer not initialized!")
        error_response = AnalysisResponse(
            symbolA=msg.symbolA,
            symbolB=msg.symbolB,
            signal="NEUTRAL",
            confidence=0.0,
            reasoning="Qwen3 analyzer not initialized - check configuration",
            risk_level="HIGH",
            key_factors=["ERROR: Analyzer not available"],
            entry_recommendation="Do not trade - system error",
            zScore=msg.zScore,
            correlation=msg.correlation,
            spread_mean=msg.spread_mean,
            spread_std=msg.spread_std,
            beta=msg.beta,
        )
        await ctx.send(sender, error_response)
        return
    
    try:
        # Prepare metrics for Qwen3
        metrics = {
            "symbolA": msg.symbolA,
            "symbolB": msg.symbolB,
            "zScore": msg.zScore,
            "corr": msg.correlation,
            "mean": msg.spread_mean,
            "std": msg.spread_std,
            "beta": msg.beta,
            "volatility": msg.volatility or 0.0,
        }
        
        # Get Qwen3 analysis
        ctx.logger.info("Calling Qwen3 for detailed analysis...")
        analysis = qwen_analyzer.analyze_pair(metrics, temperature=0.3)
        
        # Build response
        response = AnalysisResponse(
            symbolA=msg.symbolA,
            symbolB=msg.symbolB,
            signal=analysis.get("signal", "NEUTRAL"),
            confidence=float(analysis.get("confidence", 0.5)),
            reasoning=analysis.get("reasoning", "No detailed reasoning available"),
            risk_level=analysis.get("risk_level", "MEDIUM"),
            key_factors=analysis.get("key_factors", []),
            entry_recommendation=analysis.get("entry_recommendation", "Consult additional sources"),
            zScore=msg.zScore,
            correlation=msg.correlation,
            spread_mean=msg.spread_mean,
            spread_std=msg.spread_std,
            beta=msg.beta,
        )
        
        ctx.logger.info(f"Sending analysis response: signal={response.signal}, confidence={response.confidence:.2f}")
        await ctx.send(sender, response)
        
    except Exception as e:
        ctx.logger.error(f"Analysis failed: {e}")
        # Send error response
        error_response = AnalysisResponse(
            symbolA=msg.symbolA,
            symbolB=msg.symbolB,
            signal="NEUTRAL",
            confidence=0.0,
            reasoning=f"Analysis error: {str(e)}",
            risk_level="HIGH",
            key_factors=["ERROR"],
            entry_recommendation="Do not trade - analysis failed",
            zScore=msg.zScore,
            correlation=msg.correlation,
            spread_mean=msg.spread_mean,
            spread_std=msg.spread_std,
            beta=msg.beta,
        )
        await ctx.send(sender, error_response)


# Register protocol
res = analyzer_agent.include(analysis_protocol)
print("Registered TradeAnalysis protocol:", res)



if __name__ == "__main__":
    print(f"Starting Trade Analyzer Agent on port {AGENT_PORT}...")
    print(f"Agent address: {analyzer_agent.address}")
    analyzer_agent.run()
