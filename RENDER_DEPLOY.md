# ELARA Deployment Guide - Render.com

This guide explains how to deploy ELARA (agent + API) to Render.com using a **single combined service**.

## Architecture

**Combined Service**:
- **elara-combined**: Runs both the analyzer agent (port 8001) and Flask API (port 10000) in one process
  - Uses `combined_server.py` which starts both services via threading
  - Single deployment, easier to manage
  - Reduces free tier usage (1 service instead of 2)
  - Agent registers with Agentverse Almanac
  - API provides HTTP endpoints with caching

## Prerequisites

1. **GitHub Repository**
   - Push your code to GitHub
   - Make sure `combined_server.py` and `render.yaml` are committed

2. **Render Account**
   - Sign up at https://render.com
   - Free tier is sufficient for testing

3. **Environment Secrets**
   - `OPENROUTER_API_KEY`: Your OpenRouter API key
   - `DATABASE_URL`: Neon PostgreSQL connection string
   - `AGENTVERSE_API_KEY`: Your Agentverse API key (optional)
   - `ANALYZER_AGENT_SEED`: "ELARA" (already set in render.yaml)

## Deployment Steps

### Option 1: Blueprint Deployment (Recommended)

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Deploy ELARA combined service"
   git push origin main
   ```

2. **Deploy via Render Dashboard**:
   - Go to https://dashboard.render.com
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Render will detect `render.yaml` automatically
   - Click "Apply"

3. **Configure Secrets**:
   - Go to the deployed service settings
   - Add environment variables:
     - `OPENROUTER_API_KEY`: (your key)
     - `DATABASE_URL`: (your Neon connection string)
     - `AGENTVERSE_API_KEY`: (your key)
   
4. **Verify Deployment**:
   - Wait for build to complete (~5 minutes)
   - Check logs for "✅ ELARA is ready! Both services running."
   - Visit health endpoint: `https://elara-combined.onrender.com/health`

### Option 2: Manual Deployment

1. **Create Web Service**:
   - Go to Render Dashboard
   - Click "New" → "Web Service"
   - Connect GitHub repository
   - Configure:
     - **Name**: elara-combined
     - **Runtime**: Python 3
     - **Region**: Oregon
     - **Branch**: main
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python combined_server.py`

2. **Add Environment Variables**:
   ```
   PYTHON_VERSION=3.11.0
   OPENROUTER_API_KEY=(your key)
   QWEN_MODEL=qwen/qwen3-max
   ANALYZER_AGENT_SEED=ELARA
   ANALYZER_AGENT_PORT=8001
   AGENTVERSE_API_KEY=(your key)
   DATABASE_URL=(your Neon connection string)
   CACHE_TTL_HOURS=24
   AGENT_API_BASE=https://pair-agent.onrender.com
   FLASK_HOST=0.0.0.0
   ```

3. **Deploy**:
   - Click "Create Web Service"
   - Wait for deployment to complete

## Testing Your Deployment

### 1. Health Check
```bash
curl https://elara-combined.onrender.com/health
```

Expected response:
```json
{
  "status": "ok",
  "service": "elara-combined",
  "agent_running": true,
  "agent_address": "agent1qdntx3ua69pewxqqvxa4gntvqf8t47flu2xv5zsj87n6xd9vpa47kll3wgp",
  "agent_port": 8001,
  "api_port": 10000,
  "qwen_available": true,
  "cache_enabled": true
}
```

### 2. Analyze Trading Pair
```bash
curl -X POST https://elara-combined.onrender.com/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "symbolA": "SOL",
    "symbolB": "BTC",
    "limit": 200
  }'
```

### 3. Check Cache Stats
```bash
curl https://elara-combined.onrender.com/health
```

### 4. Agent Inspector
Visit: `https://agentverse.ai/inspect/?uri=https%3A//elara-combined.onrender.com%3A8001&address=agent1qdntx3ua69pewxqqvxa4gntvqf8t47flu2xv5zsj87n6xd9vpa47kll3wgp`

## Monitoring

### View Logs
1. Go to Render Dashboard
2. Click on your service
3. Click "Logs" tab
4. Look for:
   - "✅ ELARA is ready! Both services running."
   - "Registration on Almanac API successful"
   - "Almanac contract registration is up to date!"

### Check Metrics
- **Response Time**: Monitor via Render dashboard
- **Cache Hit Rate**: Check `/health` endpoint cache_stats
- **Error Rate**: Monitor logs for exceptions

## Keep Services Awake (Optional)

Render free tier services sleep after 15 minutes of inactivity. To keep them awake:

1. **UptimeRobot** (recommended):
   - Sign up at https://uptimerobot.com (free)
   - Add monitor: `https://elara-combined.onrender.com/health`
   - Set interval: 5 minutes
   - This pings your service to keep it active

2. **Cron-job.org**:
   - Sign up at https://cron-job.org
   - Create job to hit `/health` every 5 minutes

## Troubleshooting

### Agent Not Registering
- Check `AGENTVERSE_API_KEY` is set correctly
- Verify `ANALYZER_AGENT_SEED` is "ELARA"
- Check logs for "Registration failed" errors

### Qwen3 Errors
- Verify `OPENROUTER_API_KEY` is valid
- Check OpenRouter account has credits
- Look for "Failed to initialize Qwen3" in logs

### Cache Errors
- Verify `DATABASE_URL` is correct
- Check Neon database is active
- Test connection from Render dashboard

### Port Scanning Message
- "Continuing to scan for open port 3000" is normal
- This is uagents framework behavior, not an error
- Agent is already running on port 8001

## Cost Estimate

**Free Tier**:
- 1 web service (combined): Free (750 hours/month)
- Neon PostgreSQL: Free tier (0.5GB storage)
- OpenRouter API: ~$0.36/month (based on usage)

**Total**: ~$0.36/month for moderate usage

## Next Steps

1. **Set up monitoring** with UptimeRobot
2. **Test end-to-end** with real trading pairs
3. **Monitor cache hit rate** to optimize performance
4. **Scale** to paid tier if needed for 24/7 availability

## Support

- Render Docs: https://render.com/docs
- ASI uAgents: https://docs.fetch.ai/uagents
- OpenRouter: https://openrouter.ai/docs
