"""Qwen3 model client for trade analysis reasoning.

Uses OpenRouter API for cloud-based inference.
Provides structured prompts for trade pair analysis with strong reasoning.
"""
from __future__ import annotations

import os
import json
from typing import Dict, Any, Optional
import requests

from dotenv import load_dotenv
load_dotenv()



class Qwen3Analyzer:
    """Trade analysis client using Qwen3 via OpenRouter API."""
    
    def __init__(
        self,
        model_name: str = None,
        openrouter_api_key: str = None,
    ):
        """Initialize Qwen3 client with OpenRouter.
        
        Args:
            model_name: Model identifier (e.g., "qwen/qwen3-max")
            openrouter_api_key: OpenRouter API key (or use OPENROUTER_API_KEY env var)
        """
        self.openrouter_api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        self.openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.model_name = model_name or os.getenv("QWEN_MODEL", "qwen/qwen3-max")
        
        if not self.openrouter_api_key:
            raise RuntimeError("OpenRouter API key not configured. Set OPENROUTER_API_KEY environment variable.")
    
    def _build_analysis_prompt(self, metrics: Dict[str, Any]) -> str:
        """Build structured prompt for trade analysis."""
        symbolA = metrics.get("symbolA", "UNKNOWN")
        symbolB = metrics.get("symbolB", "UNKNOWN")
        z_score = metrics.get("zScore", 0.0)
        correlation = metrics.get("corr", 0.0)
        spread_mean = metrics.get("mean", 0.0)
        spread_std = metrics.get("std", 0.0)
        beta = metrics.get("beta", 1.0)
        volatility = metrics.get("volatility", 0.0)
        # Optional extended metrics (may be None)
        current_spread = metrics.get("currentSpread")
        half_life = metrics.get("halfLife")
        coint_p = metrics.get("cointegrationPValue")
        is_coint = metrics.get("isCointegrated")
        sharpe = metrics.get("sharpe")
        signal_type = metrics.get("signalType")
        
        
        prompt = f"""You are an expert cryptocurrency pairs trading analyst. Analyze the following trading pair metrics and provide detailed reasoning.

**Trading Pair:** {symbolA} / {symbolB}

**Statistical Metrics:**
- Z-Score: {z_score:.4f}
- Correlation: {correlation:.4f}
- Spread Mean: {spread_mean:.6f}
- Spread Std Dev: {spread_std:.6f}
- Beta (hedge ratio): {beta:.4f}
- Volatility: {volatility:.4f}

**Additional Metrics (if available):**
{('- Current Spread: ' + str(current_spread)) if current_spread is not None else ''}
{('- Half-life: ' + str(half_life)) if half_life is not None else ''}
{('- Cointegration p-value: ' + str(coint_p)) if coint_p is not None else ''}
{('- Cointegrated: ' + str(is_coint)) if is_coint is not None else ''}
{('- Sharpe: ' + str(sharpe)) if sharpe is not None else ''}
{('- Upstream signal: ' + str(signal_type)) if signal_type is not None else ''}

**Analysis Requirements:**
1. **Signal Strength**: Evaluate if Z-score indicates a trading opportunity (typically |Z| > 2.0 suggests mean reversion opportunity)
2. **Pair Suitability**: Assess correlation strength (>0.7 is good for pairs trading)
3. **Risk Assessment**: Consider volatility and spread characteristics
4. **Trading Recommendation**: Provide clear LONG/SHORT/NEUTRAL recommendation with confidence level
5. **Reasoning**: Explain the statistical rationale step-by-step

**Output Format (JSON):**
```json
{{
  "signal": "LONG" | "SHORT" | "NEUTRAL",
  "confidence": 0.0-1.0,
  "reasoning": "detailed explanation with statistical justification",
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "key_factors": ["factor1", "factor2", ...],
  "entry_recommendation": "specific guidance on entry timing"
}}
```

Provide your analysis now:"""
        return prompt
    
    def _call_openrouter(self, prompt: str, temperature: float = 0.3, max_tokens: int = 1024) -> str:
        """Call OpenRouter API for inference."""
        if not self.openrouter_api_key:
            raise RuntimeError("OpenRouter API key not configured. Set OPENROUTER_API_KEY environment variable.")
        
        url = f"{self.openrouter_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "https://github.com/pair-agentverse"),
            "X-Title": os.getenv("OPENROUTER_TITLE", "ELARA Trade Analyzer"),
        }
        
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                return content.strip()
            else:
                raise RuntimeError(f"Unexpected OpenRouter response format: {result}")
                
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"OpenRouter API request failed: {e}")
    
    def analyze_pair(self, metrics: Dict[str, Any], temperature: float = 0.3) -> Dict[str, Any]:
        """Analyze trading pair using Qwen3 reasoning via OpenRouter.
        
        Args:
            metrics: Dict with symbolA, symbolB, zScore, corr, mean, std, beta, volatility
            temperature: Sampling temperature (lower = more deterministic)
            
        Returns:
            Dict with signal, confidence, reasoning, risk_level, key_factors, entry_recommendation
        """
        prompt = self._build_analysis_prompt(metrics)
        raw_response = self._call_openrouter(prompt, temperature)
        
        # Parse JSON response (extract from markdown code blocks if present)
        try:
            # Try to find JSON in code blocks
            if "```json" in raw_response:
                start = raw_response.index("```json") + 7
                end = raw_response.index("```", start)
                json_str = raw_response[start:end].strip()
            elif "```" in raw_response:
                start = raw_response.index("```") + 3
                end = raw_response.index("```", start)
                json_str = raw_response[start:end].strip()
            else:
                json_str = raw_response
            
            parsed = json.loads(json_str)
            
            # Validate required fields
            required = ["signal", "confidence", "reasoning", "risk_level"]
            for field in required:
                if field not in parsed:
                    parsed[field] = "UNKNOWN" if field != "confidence" else 0.5
            
            return parsed
            
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback: return raw response with basic structure
            print(f"[Qwen3] Failed to parse JSON response: {e}")
            return {
                "signal": "NEUTRAL",
                "confidence": 0.5,
                "reasoning": raw_response,
                "risk_level": "MEDIUM",
                "key_factors": [],
                "entry_recommendation": "Manual review recommended"
            }


# Convenience function
def analyze_trade_pair(
    symbolA: str,
    symbolB: str,
    metrics: Dict[str, Any],
    model_name: str = None
) -> Dict[str, Any]:
    """Analyze a trading pair with Qwen3 via OpenRouter.
    
    Args:
        symbolA: First symbol
        symbolB: Second symbol  
        metrics: Statistical metrics dict
        model_name: Optional model override
        
    Returns:
        Analysis result with signal, confidence, reasoning, etc.
    """
    # Ensure symbols are in metrics
    metrics["symbolA"] = symbolA
    metrics["symbolB"] = symbolB
    
    analyzer = Qwen3Analyzer(model_name=model_name)
    return analyzer.analyze_pair(metrics)


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Smoke test
    test_metrics = {
        "symbolA": "BTC-PERP",
        "symbolB": "ETH-PERP",
        "zScore": 2.5,
        "corr": 0.85,
        "mean": 0.0012,
        "std": 0.0045,
        "beta": 1.15,
        "volatility": 0.023,
    }
    
    print("Testing Qwen3 analyzer with OpenRouter...")
    try:
        result = analyze_trade_pair("BTC-PERP", "ETH-PERP", test_metrics)
        print("\nAnalysis Result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")
        print("\nNote: Ensure OPENROUTER_API_KEY is set in .env file")
