import finnhub
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import yfinance as yf
import pandas_ta as ta
from graph.state import AgentState
import json
import datetime
load_dotenv()
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from pydantic import BaseModel, Field, ValidationError



class RiskScoreOutput(BaseModel):
    risk_score: float = Field(ge=0, le=100)
    risk_summary: str



def get_risk_data(ticker:str)-> dict:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info 
        return {
        "beta": info.get("beta","data not available for this stock"),           
        "volume": info.get("volume","data not available for this stock"),    
        "averageVolume": info.get("averageVolume","data not available for this stock"),    
        "shortRatio": info.get("shortRatio","data not available for this stock"),      
        "fiftyTwoWeekHigh": info["fiftyTwoWeekHigh"],     
        "fiftyTwoWeekLow": info["fiftyTwoWeekLow"],
        "regularMarketPrice": info["regularMarketPrice"],      
        } 
    except Exception as e:
        logger.warning(f"yfinance API error for {ticker}: {e}")
        return None
    

system_prompt  = """
You are an expert risk analyst specializing in stock market analysis.

Your task is to analyze the provided stock data and return a risk score 
between 0 and 100, along with a concise summary explaining the score.

Scoring Guide:
- Score closer to 100 = very safe
- Score closer to 0 = very dangerous
- Score around 50 = Neutral 

Interpretation Rules:

Beta Interpretation:
- Beta < 0.8  = Low volatility, moves less than market = Low risk
- Beta 0.8 to 1.2 = Moderate volatility, moves with market = Medium risk
- Beta 1.2 to 1.5 = Above average volatility = Medium-High risk
- Beta > 1.5  = High volatility, moves more than market = High risk

Volume Interpretation:
- Volume close to averageVolume = Normal liquidity = Low risk
- Volume much lower than average = Low liquidity, hard to exit = High risk
- Volume much higher than average = Unusual activity, investigate = Medium risk

Short Ratio Interpretation:
- Short ratio < 3  = Low short interest = Low risk
- Short ratio 3-7  = Moderate short interest = Medium risk
- Short ratio > 7  = High short interest, many betting against = High risk
- Short ratio > 10 = Extreme short interest = Very High risk

52 Week Range Interpretation:
- Price near 52W high (within 5%) = Extended, potential reversal risk = Medium risk
- Price near 52W low (within 10%) = Potential value or continued decline = High risk
- Price in middle range = Normal trading range = Low-Medium risk

Price vs 52W Range Position:
- Calculate: position = (current - 52W low) / (52W high - 52W low)
- position > 0.8 = Near highs = caution
- position < 0.2 = Near lows = high risk
- position 0.2-0.8 = Healthy range = lower risk

Here is the stock data to analyze:

Ticker: {ticker}

RISK DATA:
{risk_data}

Return your response in this exact JSON format only. 
No extra text, no markdown, no explanation outside the JSON:
{{
    "risk_score": <number between 0 and 100>,
    "risk_summary": "<concise explanation of the score>"
}} 
"""


llm = ChatOpenAI(model="gpt-4o", temperature=0)
structured_llm = llm.with_structured_output(RiskScoreOutput)


def risk_agent(state: AgentState) -> AgentState:
    ticker = state["ticker"]

    # NEW: check if this agent should run fresh or use cache
    run_agents = state.get("run_agents")  

      # If run_agents is None or "risk" is not in the list, use cache
    if run_agents is not None and "risk" not in run_agents:
        return {
            "risk_score": state.get("cached_risk_score"),
            "risk_summary": state.get("cached_risk_summary")
        }

    Risk = get_risk_data(ticker) 
    if Risk is None:
        return {
            "risk_score": state.get("cached_risk_score"),
            "risk_summary": state.get("cached_risk_summary")
        }
    
    prompt = ChatPromptTemplate.from_template(system_prompt)
    chain = prompt | structured_llm 

    MAX_RETRIES = 2
    for attempt in range(MAX_RETRIES):
        try:
            response = chain.invoke({
                "ticker": ticker,
                "risk_data":json.dumps(Risk),
            })
            
            return {
                "risk_score": response.risk_score,
                "risk_summary": response.risk_summary
            }

        except ValidationError as e:
            logger.warning(f"Schema validation failed for {ticker} (attempt {attempt+1}/{MAX_RETRIES}): {e}")
        except Exception as e:
            logger.warning(f"LLM call failed for {ticker} (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
    logger.warning(f"All {MAX_RETRIES} attempts failed for {ticker} — falling back to cached risk score")
    return {
            "risk_score": state.get("cached_risk_score"),
            "risk_summary": state.get("cached_risk_summary")
            }
    


if __name__ == "__main__":
    # Test 1: fresh run (no run_agents)
    result1 = risk_agent({"ticker": "AAPL"})
    logger.info(f"FRESH RUN: {result1}")

    # Test 2: cache-skip path (sentiment NOT in run_agents)
    result2 = risk_agent({
        "ticker": "AAPL",
        "run_agents": ["technical", "sentiment"],  # sentiment NOT included
        "cached_risk_score": 70,
        "cached_risk_summary": "Cached: moderately bullish from earlier run"
    })
    logger.info(f"CACHED RUN: {result2}")
