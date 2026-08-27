
import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from graph.state import AgentState
import json
load_dotenv()
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

system_prompt  = """
You are an expert validation analyst specializing in stock market analysis.

You will be given calculated scores, a confidence value, and a decision that have already been determined. Your only task is to write a short reasoning explanation for this assessment.

Here is the analysis data:
Agent Scores: {scores}
Calculated Confidence: {confidence}
Decision: {decision}
Conflicts Detected: {conflicts}

Write a concise 2-3 sentence explanation covering:
- Which agents have strong or weak signals
- Whether conflicts exist and why
- What the overall assessment means for the investor

STRICT OUTPUT RULES:
- Return ONLY plain prose sentences. No labels, no "key: value" formatting, no JSON, no markdown, no bullet points.
- Do NOT restate or mention the ticker, confidence number, decision, alert type, or changed agents list — the reader already has that information elsewhere. Jump straight into the analysis.
"""


# system_prompt  = """
# You are an expert validation analyst specializing in stock market analysis.

# Your task is to analyze the provided sentiment score and return a 

# confidence, decision,  alert_type ,changed_agents, reasoning 

# confidence > 80  → HIGH_INTEREST
# confidence 60-80 → WATCH
# confidence 40-60 → NEUTRAL
# confidence < 40  → IGNORE 

# Conflict cap
# If conflicts exist → cap confidence at 70 

# decision on the basisc of confidence and conflicts 
#  > 80  → HIGH_INTEREST
#  60-80 → WATCH
#  40-60 → NEUTRAL
#  < 40  → IGNORE

# Conflict detection
# Flag if any two agents differ by more than 30 points 


# Here is the analysis data:
# Ticker: {ticker}
# Agent Scores: {scores}
# Calculated Confidence: {confidence}
# Decision: {decision}
# Conflicts Detected: {conflicts}

# Provide a concise reasoning explanation for this assessment.
# Return ONLY plain text. No JSON, no markdown.

# alert_type values:

# IMMEDIATE        → confidence > 80% (high interest)
# DAILY_DIGEST     → confidence 60-80%
# SILENT           → confidence 30-60%
# CRITICAL_DROP    → confidence dropped > 25 points from last run
# ABSOLUTE_LOW     → confidence dropped below 30%

# reasoning behind the given points on  the basic of provided data 



# Provide a concise 2-3 sentence reasoning explanation focusing only on:
# - Which agents have strong or weak signals
# - Whether conflicts exist and why
# - What the overall assessment means for the investor
# Return ONLY plain text. No labels, no JSON, no markdown.
# Do NOT include Ticker, Confidence, Decision, Alert Type, or Changed Agents in your response.

# """


llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)



def validation_agent(state: AgentState) -> AgentState:
    ticker = state["ticker"]
    technical_score  = state["technical_score"]
    news_score       = state["news_score"]
    sentiment_score  = state["sentiment_score"]
    risk_score       = state["risk_score"]

    # Confidence score

    try:
        confidence = (
            technical_score * 0.30 +
            news_score      * 0.25 +
            sentiment_score * 0.25 +
            risk_score      * 0.20
        ) 
    except TypeError as e:
        logger.error(f"Confidence calculation failed for {ticker} — one or more scores is None: "
                 f"technical={technical_score}, news={news_score}, "
                 f"sentiment={sentiment_score}, risk={risk_score}")
        raise

    conflicts = []

    scores = {
        "technical": technical_score,
        "news": news_score,
        "sentiment": sentiment_score,
        "risk": risk_score
    }

    items = list(scores.items())

    for i in range  (len(items)):
        for j in range(i+1, len(items)):
            agent1, score1 = items[i]
            agent2, score2 = items[j] 
            if abs(score1 - score2) > 30:
                conflicts.append(f"{agent1} vs {agent2}")
            
    if len(conflicts) > 0 :
        if(confidence) > 70 :
            confidence = 70 

    
    if confidence < 30:
        alert_type = "ABSOLUTE_LOW"
    elif confidence > 80:
        alert_type = "IMMEDIATE"
    elif confidence >= 60:
        alert_type = "DAILY_DIGEST"
    else:
        alert_type = "SILENT"

    if confidence > 80:
        decision = "HIGH_INTEREST"
    elif confidence >= 60:
        decision = "WATCH"
    elif confidence >= 40:
        decision = "NEUTRAL"
    else:
        decision = "IGNORE"

    prompt = ChatPromptTemplate.from_template(system_prompt)
    chain = prompt | llm
    
    response = chain.invoke({"ticker": ticker ,
                             "confidence":round(confidence, 2) ,
                               "scores":scores,
                               "conflicts":conflicts ,
                               "decision":decision})
        
    reasoning  = response.content.strip()

    changed_agents = []
    threshold = 5.0  # score change > 5 points = meaningful change

    prev_scores = {
        "technical": state.get("previous_technical_score"),
        "news": state.get("previous_news_score"),
        "sentiment": state.get("previous_sentiment_score"),
        "risk": state.get("previous_risk_score")
    }

    current_scores = {
        "technical": technical_score,
        "news": news_score,
        "sentiment": sentiment_score,
        "risk": risk_score
    }

    for agent in ["technical", "news", "sentiment", "risk"]:
        prev = prev_scores[agent]
        curr = current_scores[agent]
        if prev is not None and abs(curr - prev) > threshold:
            changed_agents.append(agent)

    return {
    "confidence": round(confidence, 2),
    "decision": decision,
    "alert_type": alert_type,
    "changed_agents": changed_agents, 
    "reasoning": reasoning
            }

if __name__ == "__main__":
    result = validation_agent({
        "ticker": "AAPL",
        "technical_score": 45,
        "news_score": 75,
        "sentiment_score": 65,
        "risk_score": 65
    })
    logger.info(result)