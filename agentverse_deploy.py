"""Deploy ELARA Trade Analyzer to ASI Agentverse.

This script runs the analyzer agent with Agentverse registration.
The agent will be accessible at: agent1qdntx3ua69pewxqqvxa4gntvqf8t47flu2xv5zsj87n6xd9vpa47kll3wgp
"""
from __future__ import annotations

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the analyzer agent components
from analyzer_agent import (
    analyzer_agent,
    AnalyzeRequest,
    AnalysisResponse,
    qwen_analyzer,
    initialize_qwen,
    handle_analyze_request,
    analysis_protocol
)

# Agentverse configuration
AGENTVERSE_API_KEY = os.getenv("AGENTVERSE_API_KEY")

if not AGENTVERSE_API_KEY:
    print("⚠️  Warning: AGENTVERSE_API_KEY not set in .env")
    print("   The agent will run locally but won't register with Agentverse")

# Print agent information
print("=" * 60)
print("ELARA Trade Analyzer - Agentverse Deployment")
print("=" * 60)
print(f"Agent Name: {analyzer_agent.name}")
print(f"Agent Address: {analyzer_agent.address}")
print(f"Expected Address: agent1qdntx3ua69pewxqqvxa4gntvqf8t47flu2xv5zsj87n6xd9vpa47kll3wgp")
print(f"Port: {analyzer_agent._port}")
print(f"Agentverse API Key: {'✓ Configured' if AGENTVERSE_API_KEY else '✗ Not set'}")
print("=" * 60)

# Verify the agent address matches
expected_address = "agent1qdntx3ua69pewxqqvxa4gntvqf8t47flu2xv5zsj87n6xd9vpa47kll3wgp"
if str(analyzer_agent.address) == expected_address:
    print("✓ Agent address matches registered ELARA address")
else:
    print("⚠️  Agent address mismatch!")
    print(f"   Current: {analyzer_agent.address}")
    print(f"   Expected: {expected_address}")
    print("   Update ANALYZER_AGENT_SEED in .env to match ELARA's seed")

print("\nProtocols:")
print(f"  - TradeAnalysis v1.0")
print("\nMessage Models:")
print(f"  - AnalyzeRequest (input)")
print(f"  - AnalysisResponse (output)")
print("\n" + "=" * 60)

# Run the agent
if __name__ == "__main__":
    print("\n🚀 Starting ELARA agent for Agentverse...")
    print("   The agent will register with Almanac and Agentverse")
    print("   Press Ctrl+C to stop\n")
    
    try:
        analyzer_agent.run()
    except KeyboardInterrupt:
        print("\n\n✓ Agent stopped gracefully")
