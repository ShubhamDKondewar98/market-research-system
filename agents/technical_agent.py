import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import yfinance as yf
import finnhub
import pandas_ta as ta
from graph.state import AgentState
import json
load_dotenv()
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from pydantic import BaseModel, Field, ValidationError


class TechnicalScoreOutput(BaseModel):
    technical_score: float = Field(ge=0, le=100)
    technical_summary: str


def get_quote(ticker:str)->dict:
    #getting stock prize  details from  finnhub
    try:
        finnhub_client = finnhub.Client(api_key=os.environ['FINNHUB_API_KEY'])
        
        quote_data = finnhub_client.quote(ticker) 
        return {
            "current_price": quote_data['c'],
            "change": quote_data['d'],
            "percent_change": quote_data['dp'],
            "high": quote_data['h'],
            "low": quote_data['l'],
            "open": quote_data['o'],
            "previous_close": quote_data['pc']
        }
    except Exception as e:
        logger.warning(f"Finnhub API error for {ticker}: {e}")
        return None

def get_indicators(ticker:str , interval: str = "1d")->dict:
    try:
        stock = yf.Ticker(ticker)  
        period_map = {
            "15m": "5d",
            "1h": "1mo",
            "4h": "1mo", 
            "1d": "3mo"
        }
        period = period_map.get(interval, "3mo")
       
        df = stock.history(period=period, interval=interval)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MACD'] = ta.macd(df['Close'])['MACD_12_26_9']
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['EMA50'] = ta.ema(df['Close'], length=50) 
        return {
        "rsi": round(float(df['RSI'].iloc[-1]), 2),
        "macd": round(float(df['MACD'].iloc[-1]), 2),
        "ema20": round(float(df['EMA20'].iloc[-1]), 2),
        "ema50": round(float(df['EMA50'].iloc[-1]), 2)
             }
    except Exception as e:
        logger.warning(f"yahoo finance API error for {ticker}: {e}")
        return None


system_prompt  = """
You are an expert technical analyst specializing in stock market analysis.

Your task is to analyze the provided stock data and return a technical score 
between 0 and 100, along with a concise summary explaining the score.

Scoring Guide:
- Score closer to 100 = Strong bullish signal
- Score closer to 0 = Strong bearish signal
- Score around 50 = Neutral market condition

Interpretation Rules:

RSI Indicator:
- RSI above 70 = Overbought (bearish signal)
- RSI below 30 = Oversold (bullish signal)
- RSI between 30 and 70 = Neutral

MACD Indicator:
- MACD positive = Bullish momentum
- MACD negative = Bearish momentum 

EMA Indicator :
- EMA 20  — short term trend
- EMA 50  — medium term trend

- EMA 20 above EMA 50 = Bullish trend
- EMA 20 below EMA 50 = Bearish trend
- Price above EMA 20  = Short term bullish
- Price below EMA 20  = Short term bearish

Price Action:
- Current price above previous close = Bullish
- Current price below previous close = Bearish
- Percent change >= +2% = Strong bullish
- Percent change <= -2% = Strong bearish

Here is the stock data to analyze:
Ticker: {ticker}
Current Price: {current_price}
Change: {change}
Percent Change: {percent_change}%
High: {high}
Low: {low}
Previous Close: {previous_close}
RSI: {rsi}
MACD: {macd}
EMA20: {ema20}
EMA50: {ema50}

Return your response in this exact JSON format only. 
No extra text, no markdown, no explanation outside the JSON:
{{
    "technical_score": <number between 0 and 100>,
    "technical_summary": "<concise explanation of the score>"
}} 

"""


llm = ChatOpenAI(model="gpt-4o", temperature=0)
structured_llm = llm.with_structured_output(TechnicalScoreOutput)

def technical_agent(state: AgentState) -> AgentState:
    ticker = state["ticker"]  

    # NEW: check if this agent should run fresh or use cache
    run_agents = state.get("run_agents") 

     # If run_agents is None or "technical" is not in the list, use cache
    if run_agents is not None and "technical" not in run_agents:
        return {
            "technical_score": state.get("cached_technical_score"),
            "technical_summary": state.get("cached_technical_summary")
        }
    
    # Step 1 - fetch data
    quote = get_quote(ticker) 
    if quote is None:
        return {   
            "technical_score": state.get("cached_technical_score"),
            "technical_summary": state.get("cached_technical_summary") 
        }  
    interval = state.get("interval", "1d")  # default to daily
    indicators = get_indicators(ticker,interval)
    if indicators is None:
        return {
            "technical_score": state.get("cached_technical_score"),
            "technical_summary": state.get("cached_technical_summary")
        }

    # prompt = ChatPromptTemplate.from_template(system_prompt)
    # chain = prompt | structured_llm 

    # MAX_RETRIES = 2
    
    # for attempt in range(MAX_RETRIES):

    #     try:
    #         response = chain.invoke({ 
    #             "ticker": ticker,
    #             "current_price":quote["current_price"],
    #             "change": quote["change"],
    #             "percent_change": quote["percent_change"],
    #             "high":quote["high"],
    #             "low": quote["low"],
    #             "previous_close": quote["previous_close"],
    #             "rsi": indicators["rsi"],
    #             "macd": indicators["macd"],
    #             "ema20": indicators["ema20"],
    #             "ema50": indicators["ema50"]
    #         }) 
            
    #         return {
    #             "technical_score": response.technical_score,
    #             "technical_summary": response.technical_summary
    #         }

    #     except ValidationError as e:
    #         logger.warning(f"Schema validation failed for {ticker} (attempt {attempt+1}/{MAX_RETRIES}): {e}")

    #     except Exception as e:
    #         logger.warning(f"LLM call failed for {ticker} (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
    # logger.warning(f"All {MAX_RETRIES} attempts failed for {ticker} — falling back to cached technical score")


    return score_technical_data(ticker, quote, indicators, state.get("cached_technical_score"))
    
    # return {
    #         "technical_score": state.get("cached_technical_score"),
    #         "technical_summary": state.get("cached_technical_summary")
    #     }  


#################################

####  LLM evaluation 

fake_quote = {
    "current_price": 185,
    "change": 5,  # 185 - 180
    "percent_change": 2.8,
    "high": 186,
    "low": 179,
    "previous_close": 180
}
fake_indicators = {
    "rsi": 25,
    "macd": 2.5,
    "ema20": 180,
    "ema50": 170
}

def score_technical_data(ticker: str, quote: dict, indicators: dict, cached_fallback_score=None) -> dict:
    """
    Takes already-fetched quote and indicator data and produces a technical score via LLM.
    Extracted from technical_agent() so it can be tested independently (e.g. with synthetic
    indicator values for evaluation) without needing real Finnhub/yfinance data.
    """
    prompt = ChatPromptTemplate.from_template(system_prompt)
    chain = prompt | structured_llm

    MAX_RETRIES = 2
    for attempt in range(MAX_RETRIES):
        try:
            response = chain.invoke({
                "ticker": ticker,
                "current_price": quote["current_price"],
                "change": quote["change"],
                "percent_change": quote["percent_change"],
                "high": quote["high"],
                "low": quote["low"],
                "previous_close": quote["previous_close"],
                "rsi": indicators["rsi"],
                "macd": indicators["macd"],
                "ema20": indicators["ema20"],
                "ema50": indicators["ema50"]
            })
            return {
                "technical_score": response.technical_score,
                "technical_summary": response.technical_summary
            }
        except ValidationError as e:
            logger.warning(f"Schema validation failed for {ticker} (attempt {attempt+1}/{MAX_RETRIES}): {e}")
        except Exception as e:
            logger.warning(f"LLM call failed for {ticker} (attempt {attempt + 1}/{MAX_RETRIES}): {e}")

    logger.warning(f"All {MAX_RETRIES} attempts failed for {ticker} — falling back to cached technical score")
    return {
        "technical_score": cached_fallback_score,
        "technical_summary": None
    }

#####################################################


 
if __name__ == "__main__":
    # Test 1: fresh run (no run_agents)
    result1 = technical_agent({"ticker": "AAPL"})
    logger.info(f"FRESH RUN: {result1}")

    # Test 2: cache-skip path (technical NOT in run_agents)
    result2 = technical_agent({
        "ticker": "AAPL",
        "run_agents": ["sentiment", "risk"],  # technical NOT included
        "cached_technical_score": 65,
        "cached_technical_summary": "Cached: bullish trend from earlier run"
    })
    logger.info(f"CACHED RUN: {result2}")


    # Test 3: LLM evaluation — score using FAKE, synthetic indicator data
    result3 = score_technical_data("TEST", fake_quote, fake_indicators)
    logger.info(f"FAKE DATA (evaluation test): {result3}")







