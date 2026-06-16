
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




def company_news(ticker:str) -> list:
    try:
        today = datetime.date.today()
        week_ago = today - datetime.timedelta(days=7)
        finnhub_client = finnhub.Client(api_key=os.environ['FINNHUB_API_KEY'])
        News_data = finnhub_client.company_news(ticker,_from=week_ago.strftime("%Y-%m-%d"),to=today.strftime("%Y-%m-%d"))    
        return [
        {
            "headline": article["headline"],
            "summary": article["summary"],
            "source": article["source"],
            "datetime": article["datetime"]
        }
        for article in News_data[:10]
        ]
    except Exception as e:
        print(f"Finnhub API error for {ticker}: {e}")
        return None
    

def general_news() -> list:
    try: 
        finnhub_client = finnhub.Client(api_key=os.environ['FINNHUB_API_KEY'])
        general_news_data = finnhub_client.general_news('general', min_id=0)
        return [
        {
            "category": article["category"],
            "headline": article["headline"],
            "summary": article["summary"],
            "source": article["source"],
            "datetime": article["datetime"]
        }
        for article in general_news_data[:10]
        ]

    except Exception as e:
        print(f"Finnhub API error  : {e}")
        return None


system_prompt  = """
You are an expert news analyst specializing in stock market analysis.

Your task is to analyze the provided news data and return a news score
between 0 and 100, along with a concise summary explaining the score.

Scoring Guide:
- Score closer to 100 = Strong bullish news signal
- Score closer to 0 = Strong bearish news signal
- Score around 50 = Neutral market condition

Interpretation Rules:

Earnings beat expectations     → bullish
New product launch             → bullish
Major contract/partnership     → bullish
Analyst upgrade                → bullish

Earnings miss                  → bearish
CEO resignation                → bearish
Regulatory fine/investigation  → bearish
Analyst downgrade              → bearish
Macroeconomic recession fears  → bearish
War/geopolitical conflict      → bearish

Routine company updates        → neutral
Mixed analyst opinions         → neutral
Unrelated sector news          → neutral


Here is the stock news to analyze:
Ticker Being Analyzed: {ticker}

COMPANY NEWS:
{company_news}

GENERAL MARKET NEWS:
{general_news}

Return your response in this exact JSON format only. 
No extra text, no markdown, no explanation outside the JSON:
{{
    "news_score": <number between 0 and 100>,
    "news_summary": "<concise explanation of the score>"
}} 

""" 

llm = ChatOpenAI(model="gpt-4o", temperature=0)


def news_agent(state: AgentState) -> AgentState:
    ticker = state["ticker"] 
    
    c_news = company_news(ticker) 
    if c_news is None:
        return {
            **state,
            "news_score": None,
            "news_summary": "Technical data unavailable — Finnhub API error"
        }

    g_news = general_news() 
    if g_news is None:
        return {
            **state,
            "news_score": None,
            "news_summary": "Technical data unavailable — Finnhub API error"
        } 
    
    
    prompt = ChatPromptTemplate.from_template(system_prompt)
    chain = prompt | llm 

    response = chain.invoke({
        "ticker": ticker,
        "company_news":json.dumps(c_news,indent=2),
        "general_news":json.dumps(g_news, indent=2)

    }) 

    raw = response.content.strip() 
    
    if raw.startswith("```"):
        raw = raw.split("```")[1]  # get content between backticks
        if raw.startswith("json"):
            raw = raw[4:]  # remove the word "json"

    result = json.loads(raw.strip())

    return {
        
        "news_score": result["news_score"],
        "news_summary": result["news_summary"]
    }


if __name__ == "__main__":
    # company = company_news("AAPL")
    # general = general_news()
    # print("Company News:", company)
    # print("General News:", general)
    result = news_agent({"ticker": "AAPL"}) 
    print(result)
