# How to Interact with ELARA uAgent on Agentverse

ELARA is a trading pair analyzer agent deployed on the ASI Agentverse. Users can interact with it in multiple ways.

## Agent Details

- **Name**: ELARA Trade Analyzer
- **Address**: `agent1qdntx3ua69pewxqqvxa4gntvqf8t47flu2xv5zsj87n6xd9vpa47kll3wgp`
- **Protocol**: TradeAnalysis v1.0
- **Capabilities**: AI-powered trading pair analysis using Qwen3

## Analyze Daily Top Trading Pairs

ASI ELARA uAgent only analyzes these 6 whitelisted pairs only because of rate limits of qwen3, use Our telegram bot to access Full ELARA Agent for all pairs support ([text](https://t.me/Elara_pair_agent_bot)) :
- SOL/BTC
- BTC/SOL
- ETH/BTC
- BTC/ETH
- SOL/ETH
- ETH/SOL

## Method 1: Agent-to-Agent Communication (Recommended)

Other agents can send messages directly to ELARA using the uAgents framework.

### Python Example

```python
from uagents import Agent, Context, Model, Protocol

# Define the request/response models (must match ELARA's protocol)
class AnalyzeRequest(Model):
    symbolA: str
    symbolB: str
    zScore: float
    corr: float
    mean: float
    std: float
    beta: float
    volatility: float

class AnalysisResponse(Model):
    symbolA: str
    symbolB: str
    signal: str  # "LONG", "SHORT", "NEUTRAL"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    key_factors: list[str]
    entry_recommendation: str

# Create your agent
my_agent = Agent(
    name="my_trader",
    seed="my_unique_seed_phrase",
    port=8002
)

# ELARA's address
ELARA_ADDRESS = "agent1qdntx3ua69pewxqqvxa4gntvqf8t47flu2xv5zsj87n6xd9vpa47kll3wgp"

@my_agent.on_event("startup")
async def send_request(ctx: Context):
    # Send analysis request to ELARA
    await ctx.send(
        ELARA_ADDRESS,
        AnalyzeRequest(
            symbolA="SOL-PERP",
            symbolB="BTC-PERP",
            zScore=2.5,
            corr=0.85,
            mean=0.0012,
            std=0.0045,
            beta=1.15,
            volatility=0.023
        )
    )
    ctx.logger.info("📤 Sent analysis request to ELARA")

@my_agent.on_message(model=AnalysisResponse)
async def handle_response(ctx: Context, sender: str, msg: AnalysisResponse):
    ctx.logger.info(f"📥 Received from ELARA:")
    ctx.logger.info(f"   Pair: {msg.symbolA}/{msg.symbolB}")
    ctx.logger.info(f"   Signal: {msg.signal}")
    ctx.logger.info(f"   Confidence: {msg.confidence * 100:.1f}%")
    ctx.logger.info(f"   Risk: {msg.risk_level}")
    ctx.logger.info(f"   Reasoning: {msg.reasoning[:200]}...")

if __name__ == "__main__":
    my_agent.run()
```


## Method 2: HTTP API (Easiest for Web/Mobile Apps)

For non-agent applications, use the HTTP REST API.

### Endpoint
```
POST https://pair-agentverse.onrender.com/api/analyze
Content-Type: application/json
```

### Request Format
```json
{
  "symbolA": "SOL",
  "symbolB": "BTC",
  "limit": 200
}
```

### Response Format
```json
{
  "symbolA": "SOL-PERP",
  "symbolB": "BTC-PERP",
  "metrics": {
    "zScore": 2.5,
    "corr": 0.85,
    "mean": 0.0012,
    "std": 0.0045,
    "beta": 1.15,
    "volatility": 0.023
  },
  "analysis": {
    "signal": "SHORT",
    "confidence": 0.85,
    "reasoning": "The Z-score of 2.5 indicates...",
    "risk_level": "MEDIUM",
    "key_factors": [
      "Z-score > 2.0 indicating overvaluation",
      "Strong correlation (0.85) supporting cointegration",
      "Beta of 1.15 defines hedge ratio"
    ],
    "entry_recommendation": "Enter the trade immediately..."
  },
  "cached": false
}
```

### cURL Example
```bash
curl -X POST https://pair-agentverse.onrender.com/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "symbolA": "SOL",
    "symbolB": "BTC",
    "limit": 200
  }'
```

### Python Requests Example
```python
import requests

response = requests.post(
    "https://pair-agentverse.onrender.com/api/analyze",
    json={
        "symbolA": "SOL",
        "symbolB": "BTC",
        "limit": 200
    }
)

data = response.json()
print(f"Signal: {data['analysis']['signal']}")
print(f"Confidence: {data['analysis']['confidence'] * 100:.1f}%")
print(f"Risk: {data['analysis']['risk_level']}")
```

### JavaScript Fetch Example
```javascript
const response = await fetch('https://pair-agentverse.onrender.com/api/analyze', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    symbolA: 'SOL',
    symbolB: 'BTC',
    limit: 200
  })
});

const data = await response.json();
console.log('Signal:', data.analysis.signal);
console.log('Confidence:', data.analysis.confidence);
```

## Method 3: Agentverse Dashboard

### Register and Interact via Web UI

1. **Visit Agentverse**:
   - Go to https://agentverse.ai
   - Sign in with your Fetch.ai account

2. **Find ELARA**:
   - Search for agent address: `agent1qdntx3ua69pewxqqvxa4gntvqf8t47flu2xv5zsj87n6xd9vpa47kll3wgp`
   - Or search by name: "trade_analyzer"

3. **Inspect Agent**:
   - View agent details, protocols, and message formats
   - See available operations and response schemas

4. **Send Test Message**:
   - Use the built-in message sender
   - Fill in the AnalyzeRequest fields
   - Send and view response





## Message Protocol Details

### AnalyzeRequest Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `symbolA` | string | First trading pair symbol | "SOL-PERP" |
| `symbolB` | string | Second trading pair symbol | "BTC-PERP" |
| `zScore` | float | Z-score of spread | 2.5 |
| `corr` | float | Correlation coefficient | 0.85 |
| `mean` | float | Mean of spread | 0.0012 |
| `std` | float | Standard deviation | 0.0045 |
| `beta` | float | Beta (hedge ratio) | 1.15 |
| `volatility` | float | Volatility measure | 0.023 |

### AnalysisResponse Fields

| Field | Type | Description | Values |
|-------|------|-------------|--------|
| `signal` | string | Trading signal | LONG, SHORT, NEUTRAL |
| `confidence` | float | Confidence level | 0.0 to 1.0 |
| `reasoning` | string | Detailed explanation | Full text |
| `risk_level` | string | Risk assessment | LOW, MEDIUM, HIGH |
| `key_factors` | list | Important factors | Array of strings |
| `entry_recommendation` | string | Entry advice | Full text |

## Response Time

- **Cached**: < 100ms (24-hour cache)
- **Fresh Analysis**: 2-5 seconds (Qwen3 processing)
- **Timeout**: 30 seconds maximum

## Rate Limits

Free tier limits:
- No built-in rate limiting on agent protocol
- HTTP API: Limited by Render free tier (750 hours/month)
- OpenRouter: ~$0.36/month budget (~100 requests)

## Best Practices

1. **Cache Results**: Responses are cached for 24 hours
2. **Batch Requests**: Group analysis for multiple pairs
3. **Error Handling**: Always handle timeout and error responses
4. **Pair Validation**: Check allowed pairs before sending
5. **Confidence Threshold**: Only act on confidence > 0.7

## Integration Examples

### Trading Bot
```python
# Automated trading bot using ELARA
from uagents import Agent, Context

trading_bot = Agent(name="auto_trader", seed="bot_seed")

@trading_bot.on_interval(period=300.0)  # Every 5 minutes
async def check_opportunities(ctx: Context):
    # Fetch metrics from exchange
    metrics = get_current_metrics("SOL-PERP", "BTC-PERP")
    
    # Ask ELARA for analysis
    response = await ctx.send_and_wait(
        ELARA_ADDRESS,
        AnalyzeRequest(**metrics),
        timeout=10.0
    )
    
    # Execute if confidence is high
    if response.confidence > 0.8:
        execute_trade(response.signal, response.entry_recommendation)
```

### Web Dashboard
```javascript
// React component for trading dashboard
async function analyzeAndDisplay(symbolA, symbolB) {
  const response = await fetch('/api/analyze', {
    method: 'POST',
    body: JSON.stringify({ symbolA, symbolB, limit: 200 })
  });
  
  const data = await response.json();
  
  // Display results
  setSignal(data.analysis.signal);
  setConfidence(data.analysis.confidence);
  setRiskLevel(data.analysis.risk_level);
}
```

### Telegram Bot
```python
# Telegram bot using ELARA API
from telegram import Update
from telegram.ext import CommandHandler

async def analyze_command(update: Update, context):
    symbols = context.args  # ["SOL", "BTC"]
    
    response = requests.post(
        "https://pair-agentverse.onrender.com/api/analyze",
        json={"symbolA": symbols[0], "symbolB": symbols[1]}
    )
    
    data = response.json()
    
    await update.message.reply_text(
        f"🎯 Signal: {data['analysis']['signal']}\n"
        f"📊 Confidence: {data['analysis']['confidence']*100:.1f}%\n"
        f"⚠️ Risk: {data['analysis']['risk_level']}"
    )
```



## Example Response

```json
{
  "symbolA": "SOL-PERP",
  "symbolB": "BTC-PERP",
  "metrics": {
    "zScore": 2.34,
    "corr": 0.87,
    "mean": 0.0015,
    "std": 0.0042,
    "beta": 1.12,
    "volatility": 0.021
  },
  "analysis": {
    "signal": "SHORT",
    "confidence": 0.82,
    "reasoning": "The Z-score of 2.34 indicates that SOL-PERP is overvalued relative to BTC-PERP by 2.34 standard deviations. Given the strong correlation (0.87) and stable beta (1.12), mean reversion is highly probable. The current spread is significantly above its historical mean, creating a high-probability short opportunity.",
    "risk_level": "MEDIUM",
    "key_factors": [
      "Z-score > 2.0 signals strong overvaluation of SOL relative to BTC",
      "High correlation (0.87) validates cointegration assumption",
      "Beta of 1.12 provides optimal hedge ratio for market-neutral position",
      "Moderate volatility (2.1%) indicates manageable execution risk",
      "Spread divergence is statistically significant (2.3σ)"
    ],
    "entry_recommendation": "Enter immediately with short SOL-PERP, long BTC-PERP at 1.12:1 hedge ratio. Set stop-loss at Z-score 2.8 (±0.5σ). Target profit at mean reversion (Z-score 0.0). Expected holding period: 2-5 days. Position sizing: 2% of portfolio given medium risk level."
  },
  "cached": false
}
```

---

**Ready to integrate ELARA into your trading system?** Start with the HTTP API for quick testing, then migrate to agent-to-agent communication for production use! 🚀
