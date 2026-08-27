import sys
sys.path.insert(0, '.')
from graph.pipeline import graph
from database.queries import (
    last_known_scores, save_agent_scores, 
    get_previous_confidence, save_confidence,
    save_alert, save_execution_log,
    update_tier, get_confidence_history , get_current_tier
)
from datetime import datetime, timedelta
import time
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from utils import utc_now

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
        return current_tier  
    
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
    now = utc_now()
    
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

                # Add previous scores for changed_agents calculation
        #if last_scores is not None:
        payload["previous_technical_score"] = last_scores.get("technical_score")
        payload["previous_news_score"] = last_scores.get("news_score")
        payload["previous_sentiment_score"] = last_scores.get("sentiment_score")
        payload["previous_risk_score"] = last_scores.get("risk_score")
    
    # Step 4 — call LangGraph pipeline
    logger.info(f"\nRunning pipeline for {ticker}")
    logger.info(f"Fresh agents: {run_agents}")
    
    result = graph.invoke(payload)
    
    # Step 5 — calculate delta
    previous_confidence = get_previous_confidence(ticker)
    current_confidence = result["confidence"]
    delta = round(current_confidence - previous_confidence, 2) if previous_confidence is not None else 0.0
    
    # Step 6 — write results to DB
    now = utc_now()
    
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
    current_tier = get_current_tier(ticker)
    new_tier = evaluate_tier(ticker, current_tier)
    update_tier(ticker, new_tier)
    logger.info(f"Tier: {new_tier}")
    
    # logger.info results
    logger.info("\n=== MARKET ANALYSIS RESULT ===")
    logger.info(f"Ticker:     {result['ticker']}")
    logger.info(f"Decision:   {result['decision']}")
    logger.info(f"Confidence: {result['confidence']}%")
    logger.info(f"Delta:      {delta}")
    logger.info(f"Alert Type: {result['alert_type']}")
    logger.info(f"Fresh agents ran: {run_agents}")
    logger.info(f"\nAgent Scores:")
    logger.info(f"  Technical:  {result['technical_score']}")
    logger.info(f"  News:       {result['news_score']}")
    logger.info(f"  Sentiment:  {result['sentiment_score']}")
    logger.info(f"  Risk:       {result['risk_score']}")
    logger.info(f"\nReasoning: {result['reasoning']}")
    logger.info(f"Changed Agents: {result['changed_agents']}")

if __name__ == "__main__":
    #run_pipeline("AAPL", "1d")

    tickers = ["AAPL", "NVDA", "TSLA", "MSFT" , "JPM"]
    for ticker in tickers:
        logger.info(f"\n{'='*50}")
        run_pipeline(ticker, "1d")



