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
import json



def get_risk_data(ticker:str)-> dict:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info 
        return {
        "beta": info["beta"],           
        "volume": info["volume"],    
        "averageVolume": info["averageVolume"],    
        "shortRatio": info["shortRatio"],      
        "fiftyTwoWeekHigh": info["fiftyTwoWeekHigh"],     
        "fiftyTwoWeekLow": info["fiftyTwoWeekLow"],
        "regularMarketPrice": info["regularMarketPrice"],      
        } 
    except Exception as e:
        print(f"yfinance API error for {ticker}: {e}")
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


def risk_agent(state: AgentState) -> AgentState:
    ticker = state["ticker"]
    Risk = get_risk_data(ticker) 
    if Risk is None:
        return {
            **state,
            "risk_score": None,
            "risk_summary": "Technical data unavailable — yfinance API error"
        }
    
    prompt = ChatPromptTemplate.from_template(system_prompt)
    chain = prompt | llm 

    response = chain.invoke({
        "ticker": ticker,
        "risk_data":json.dumps(Risk,indent=2),
    })

    raw = response.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]  # get content between backticks
        if raw.startswith("json"):
            raw = raw[4:]  # remove the word "json"

    result = json.loads(raw.strip())

    return {
        
        "risk_score": result["risk_score"],
        "risk_summary": result["risk_summary"]
    }
    

if __name__ == "__main__":
    result = risk_agent({"ticker": "AAPL"})
    print(result)
