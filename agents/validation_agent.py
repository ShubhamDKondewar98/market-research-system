import finnhub
import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
import yfinance as yf
import pandas_ta as ta
from graph.state import AgentState
import json
import datetime
load_dotenv()
import json



system_prompt  = """
You are an expert validation analyst specializing in stock market analysis.

Your task is to analyze the provided sentiment score and return a 

confidence, decision,  alert_type ,changed_agents, reasoning 

confidence > 80  → HIGH_INTEREST
confidence 60-80 → WATCH
confidence 40-60 → NEUTRAL
confidence < 40  → IGNORE 

Conflict cap
If conflicts exist → cap confidence at 70 

decision on the basisc of confidence and conflicts 
 > 80  → HIGH_INTEREST
 60-80 → WATCH
 40-60 → NEUTRAL
 < 40  → IGNORE

Conflict detection
Flag if any two agents differ by more than 30 points 


Here is the analysis data:
Ticker: {ticker}
Agent Scores: {scores}
Calculated Confidence: {confidence}
Decision: {decision}
Conflicts Detected: {conflicts}

Provide a concise reasoning explanation for this assessment.
Return ONLY plain text. No JSON, no markdown.

alert_type values:

IMMEDIATE        → confidence > 80% (high interest)
DAILY_DIGEST     → confidence 60-80%
SILENT           → confidence 30-60%
CRITICAL_DROP    → confidence dropped > 25 points from last run
ABSOLUTE_LOW     → confidence dropped below 30%

reasoning behind the given points on  the basic of provided data 

Provide a concise reasoning explanation for this assessment.
Return ONLY plain text. No JSON, no markdown. 2-3 sentences maximum. 

"""


llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)



def validation_agent(state: AgentState) -> AgentState:
    ticker = state["ticker"]
    technical_score  = state["technical_score"]
    news_score       = state["news_score"]
    sentiment_score  = state["sentiment_score"]
    risk_score       = state["risk_score"]

    # Confidence score
    confidence = (
        technical_score * 0.30 +
        news_score      * 0.25 +
        sentiment_score * 0.25 +
        risk_score      * 0.20
    ) 

    conflicts = []

    scores = {
        "technical": technical_score,
        "news": news_score,
        "sentiment": sentiment_score,
        "risk": risk_score
    }

    # Compare every pair of agents
    for agent1,score1 in scores.items():
        for agent2, score2 in scores.items():
            if agent1 != agent2:
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

    return {
    **state,
    "confidence": round(confidence, 2),
    "decision": decision,
    "alert_type": alert_type,
    "changed_agents": [],
    "reasoning": reasoning
            }


# if __name__ == "__main__":
#     result  = validation_agent({"ticker": "AAPL"})
#     print(result)

if __name__ == "__main__":
    result = validation_agent({
        "ticker": "AAPL",
        "technical_score": 45,
        "news_score": 75,
        "sentiment_score": 65,
        "risk_score": 65
    })
    print(result)