# import sys
# sys.path.insert(0, '.')
# from graph.pipeline import graph

# if __name__ == "__main__":
#     result = graph.invoke({
#         "ticker": "AAPL",
#         "interval": "1d"
#     })


#     # Visualize the graph
#     from IPython.display import Image
#     graph_image = graph.get_graph().draw_mermaid_png()
#     with open("graph_visualization.png", "wb") as f:
#         f.write(graph_image)
#     print("Graph saved as graph_visualization.png")
    
#     print("\n=== MARKET ANALYSIS RESULT ===")
#     print(f"Ticker:     {result['ticker']}")
#     print(f"Decision:   {result['decision']}")
#     print(f"Confidence: {result['confidence']}%")
#     print(f"Alert Type: {result['alert_type']}")
#     print(f"Reasoning:  {result['reasoning']}")
#     print("\nAgent Scores:")
#     print(f"  Technical:  {result['technical_score']}")
#     print(f"  News:       {result['news_score']}")
#     print(f"  Sentiment:  {result['sentiment_score']}")
#     print(f"  Risk:       {result['risk_score']}")


import sys
sys.path.insert(0, '.')
from graph.pipeline import graph
from database.queries import (
    last_known_scores, save_agent_scores, 
    get_previous_confidence, save_confidence,
    save_alert, save_execution_log,
    update_tier, get_confidence_history
)
from datetime import datetime, timedelta
import time


# Freshness rules in minutes
FRESHNESS_RULES = {
    "technical": 240,  # 4 hours
    "news": 60,        # 1 hour
    "sentiment": 30,   # 30 minutes
    "risk": 120        # 2 hours
}


def evaluate_tier(ticker: str, current_tier: str) -> str:
    history = get_confidence_history(ticker, limit=3)
    
    if len(history) < 2:
        return current_tier  # not enough data to make a decision
    
    avg = sum(history) / len(history)
    trend = history[0] - history[-1]  # positive = rising, negative = falling
    
    # Promotion rules
    if avg > 75 and trend >= 0:
        return "HOT"
    
    # Demotion rules  
    if avg < 55 or trend < -15:
        return "RADAR"
    
    return "WATCH"


def run_pipeline(ticker: str, interval: str = "1d"):
    start_time = datetime.now()
    
    # Step 1 — get last known scores
    last_scores = last_known_scores(ticker)
    
    # Step 2 — decide which agents need fresh run
    run_agents = []
    now = datetime.now()
    
    if last_scores is None:
        # brand new ticker — run all agents fresh
        run_agents = ["technical", "news", "sentiment", "risk"]
    else:
        # check each agent's freshness
        for agent in ["technical", "news", "sentiment", "risk"]:
            computed_at = last_scores[f"{agent}_computed_at"]
            freshness_minutes = FRESHNESS_RULES[agent]
            age_minutes = (now - computed_at).total_seconds() / 60
            if age_minutes > freshness_minutes:
                run_agents.append(agent)
    
    # Step 3 — build payload
    payload = {
        "ticker": ticker,
        "interval": interval,
        "run_agents": run_agents,
    }
    
    # Add cached scores for agents NOT running fresh
    if last_scores is not None:
        for agent in ["technical", "news", "sentiment", "risk"]:
            if agent not in run_agents:
                payload[f"cached_{agent}_score"] = last_scores[f"{agent}_score"]
                payload[f"cached_{agent}_summary"] = None  # summaries not stored in DB yet
    
    # Step 4 — call LangGraph pipeline
    print(f"\nRunning pipeline for {ticker}")
    print(f"Fresh agents: {run_agents}")
    result = graph.invoke(payload)
    
    # Step 5 — calculate delta
    previous_confidence = get_previous_confidence(ticker)
    current_confidence = result["confidence"]
    delta = round(current_confidence - previous_confidence, 2) if previous_confidence else 0.0
    
    # Step 6 — write results to DB
    now = datetime.now()
    
    # Build timestamps — fresh agents get NOW(), cached agents carry forward old timestamp
    timestamps = {}
    for agent in ["technical", "news", "sentiment", "risk"]:
        if agent in run_agents:
            timestamps[f"{agent}_computed_at"] = now
        else:
            timestamps[f"{agent}_computed_at"] = last_scores[f"{agent}_computed_at"]
    
    save_agent_scores(
        ticker=ticker,
        technical_score=result["technical_score"],
        news_score=result["news_score"],
        sentiment_score=result["sentiment_score"],
        risk_score=result["risk_score"],
        technical_computed_at=timestamps["technical_computed_at"],
        news_computed_at=timestamps["news_computed_at"],
        sentiment_computed_at=timestamps["sentiment_computed_at"],
        risk_computed_at=timestamps["risk_computed_at"]
    )
    
    save_confidence(
        ticker=ticker,
        confidence=current_confidence,
        decision=result["decision"],
        delta=delta
    )
    
    if result["alert_type"] in ["IMMEDIATE", "ABSOLUTE_LOW", "CRITICAL_DROP"]:
        save_alert(
            ticker=ticker,
            alert_type=result["alert_type"],
            message=result["reasoning"],
            confidence=current_confidence
        )
    
    end_time = datetime.now()
    save_execution_log(
        ticker=ticker,
        run_result="succeeded",
        run_time=end_time - start_time,
        error_msg=None
    )


    # Evaluate and update tier
    new_tier = evaluate_tier(ticker, "WATCH")
    update_tier(ticker, new_tier)
    print(f"Tier: {new_tier}")
    
    # Print results
    print("\n=== MARKET ANALYSIS RESULT ===")
    print(f"Ticker:     {result['ticker']}")
    print(f"Decision:   {result['decision']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"Delta:      {delta}")
    print(f"Alert Type: {result['alert_type']}")
    print(f"Fresh agents ran: {run_agents}")
    print(f"\nAgent Scores:")
    print(f"  Technical:  {result['technical_score']}")
    print(f"  News:       {result['news_score']}")
    print(f"  Sentiment:  {result['sentiment_score']}")
    print(f"  Risk:       {result['risk_score']}")
    print(f"\nReasoning: {result['reasoning']}")

if __name__ == "__main__":
    #run_pipeline("AAPL", "1d")
    tickers = ["AAPL", "NVDA", "TSLA", "MSFT"]
    for ticker in tickers:
        print(f"\n{'='*50}")
        run_pipeline(ticker, "1d")