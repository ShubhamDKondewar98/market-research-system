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


def sentimentOfCompany(ticker:str)->list:
    try:
        today = datetime.date.today()
        year_ago = today - datetime.timedelta(days=365)
        finnhub_client = finnhub.Client(api_key=os.environ['FINNHUB_API_KEY'])
        sentiment_data = finnhub_client.stock_insider_sentiment(ticker,_from=year_ago.strftime("%Y-%m-%d"),to=today.strftime("%Y-%m-%d"))    
        return [
        {
            "year": data["year"],
            "month": data["month"],
            "change": data["change"],
            "mspr": data["mspr"]
        }
        for data in sentiment_data["data"][:10]
        ]
    except Exception as e:
        print(f"Finnhub API error for {ticker}: {e}")
        return None
    

def get_analyst_data(ticker:str)-> dict:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info 
        return {
        "current_price": info["currentPrice"],           
        "target_mean_price": info["targetMeanPrice"],    
        "target_high_price": info["targetHighPrice"],    
        "target_low_price": info["targetLowPrice"],      
        "recommendation": info["recommendationKey"],     
        "analyst_count": info["numberOfAnalystOpinions"],
        "recommendation_mean": info["recommendationMean"],
        "earnings_growth": info["earningsGrowth"],       
        "revenue_growth": info["revenueGrowth"],         
        "profit_margins": info["profitMargins"],         
        } 
    except Exception as e:
        print(f"yfinance API error for {ticker}: {e}")
        return None


system_prompt  = """
You are an expert sentiment analyst specializing in stock market analysis.

Your task is to analyze the provided stock data and return a sentiment score 
between 0 and 100, along with a concise summary explaining the score.

Scoring Guide:
- Score closer to 100 = Strong bullish signal
- Score closer to 0 = Strong bearish signal
- Score around 50 = Neutral market condition

Interpretation Rules:


- year: The year the insider transaction occurred
- month: The month the insider transaction occurred (1=January, 12=December)
- change: Net shares bought (positive) or sold (negative) by insiders that month
- mspr: Monthly Share Purchase Ratio (-100 to +100)
         Positive = insiders net buying = bullish signal
         Negative = insiders net selling = bearish signal
         Above +50 = strong insider conviction to buy
         Below -50 = strong insider conviction to sell
	    mspr > 50  = strong insider buying = bullish
	    mspr > 0   = insider buying = moderately bullish
	    mspr < 0   = insider selling = bearish
	    mspr < -50 = heavy insider selling = strongly bearish

recommendation_mean scale:
    1.0 = Strong Buy
    2.0 = Buy
    3.0 = Hold
    4.0 = Underperform
    5.0 = Sell 


recommendation = "buy" or "strong_buy" = bullish
recommendation = "hold" = neutral
recommendation = "sell" = bearish
target_mean_price > current_price = upside potential = bullish
recommendation_mean < 2.0 = strong buy consensus
recommendation_mean > 3.5 = sell consensus
earnings_growth > 15% = strong fundamental growth  
current_price: Current stock price
target_mean_price: Average analyst price target
target_high_price: Most optimistic analyst target
target_low_price: Most pessimistic analyst target
recommendation: Consensus recommendation (strong_buy/buy/hold/sell)
recommendation_mean: Score 1-5 (1=Strong Buy, 3=Hold, 5=Strong Sell)
analyst_count: Number of analysts covering this stock
earnings_growth: Year over year earnings growth rate
revenue_growth: Year over year revenue growth rate
profit_margins: Net profit margin percentage


Here is the stock data to analyze:

Ticker: {ticker}

INSIDER SENTIMENT DATA (last 12 months):
{insider_sentiment}

ANALYST DATA:
{analyst_data}

Return your response in this exact JSON format only. 
No extra text, no markdown, no explanation outside the JSON:
{{
    "sentiment_score": <number between 0 and 100>,
    "sentiment_summary": "<concise explanation of the score>"
}} 
"""




llm = ChatOpenAI(model="gpt-4o", temperature=0)


def sentiment_agent(state: AgentState) -> AgentState:
    ticker = state["ticker"]

    # NEW: check if this agent should run fresh or use cache
    run_agents = state.get("run_agents") 

    # If run_agents is None or "technical" is not in the list, use cache
    if run_agents is not None and "sentiment" not in run_agents:
        return {
            **state,
            "sentiment_score": state.get("cached_sentiment_score"),
            "sentiment_summary": state.get("cached_sentiment_summary")
        }

    C_sentiments = sentimentOfCompany(ticker) 
    if C_sentiments is None:
        return {
            **state,
            "sentiment_score": None,
            "sentiment_summary": "sentiment data unavailable — Finnhub API error"
        }
    
    analyst_data = get_analyst_data(ticker) 
    if analyst_data is None:
        return {
            **state,
            "sentiment_score": None,
            "sentiment_summary": "sentiment data unavailable — Finnhub API error"
        }
    
    prompt = ChatPromptTemplate.from_template(system_prompt)
    chain = prompt | llm 

    response = chain.invoke({
        "ticker": ticker,
        "insider_sentiment":json.dumps(C_sentiments,indent=2),
        "analyst_data":json.dumps(analyst_data, indent=2)

    })

    raw = response.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]  # get content between backticks
        if raw.startswith("json"):
            raw = raw[4:]  # remove the word "json"

    result = json.loads(raw.strip())

    return {
        **state,
        "sentiment_score": result["sentiment_score"],
        "sentiment_summary": result["sentiment_summary"]
    }


# if __name__ == "__main__":
#     result = sentiment_agent({"ticker": "AAPL"})
#     print(result)

if __name__ == "__main__":
    # Test 1: fresh run (no run_agents)
    result1 = sentiment_agent({"ticker": "AAPL"})
    print("FRESH RUN:", result1)

    # Test 2: cache-skip path (sentiment NOT in run_agents)
    result2 = sentiment_agent({
        "ticker": "AAPL",
        "run_agents": ["technical", "risk"],  # sentiment NOT included
        "cached_sentiment_score": 70,
        "cached_sentiment_summary": "Cached: moderately bullish from earlier run"
    })
    print("CACHED RUN:", result2)

