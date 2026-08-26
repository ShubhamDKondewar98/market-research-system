
import finnhub
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from graph.state import AgentState
import json
import datetime
load_dotenv()
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from database.queries import get_cached_general_news, save_general_news_cache
from pydantic import BaseModel,Field,ValidationError



class NewsScoreOutput(BaseModel):
    news_score: float = Field(ge=0, le=100)
    news_summary: str

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
        logger.warning(f"Finnhub API error for {ticker}: {e}")
        return None
    

def general_news() -> list:
    try: 
        finnhub_client = finnhub.Client(api_key=os.environ['FINNHUB_API_KEY'])
        general_news_data = finnhub_client.general_news('general', min_id=0)
        #   min_id=0 is Finnhub's parameter it means --give me articles starting from ID 0
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
        logger.warning(f"Finnhub API error : {e}")
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
structured_llm = llm.with_structured_output(NewsScoreOutput)



def news_agent(state: AgentState) -> AgentState:
    ticker = state["ticker"] 

 # NEW: check if this agent should run fresh or use cache
    run_agents = state.get("run_agents") 

    # If run_agents is None or "News" is not in the list, use cache
    if run_agents is not None and "news" not in run_agents:
        return {
            "news_score": state.get("cached_news_score"),
            "news_summary": state.get("cached_news_summary")
        }
    
    c_news = company_news(ticker) 
    if c_news is None:
        return {
            "news_score": state.get("cached_news_score"),
            "news_summary": state.get("cached_news_summary")
        }

    g_news = get_cached_general_news()
    if g_news is None:
        logger.info("General news cache MISS — fetching fresh")  
        g_news = general_news()
        if g_news is None:
            return {
            "news_score": state.get("cached_news_score"), 
            "news_summary": state.get("cached_news_summary")
        }
        save_general_news_cache(g_news)
        logger.info("General news cached successfully")  

    else:
        logger.info("General news cache HIT — using cached data")  
    
    
    prompt = ChatPromptTemplate.from_template(system_prompt)
    chain = prompt | structured_llm 

    MAX_RETRIES = 2

    for attempt in range(MAX_RETRIES):

        try:
            response = chain.invoke({
                "ticker": ticker,
                "company_news":json.dumps(c_news),
                "general_news":json.dumps(g_news)
            }) 
            
            return {
                "news_score": response.news_score,
                "news_summary": response.news_summary
            }

        except ValidationError as e:
            logger.warning(f"Schema validation failed for {ticker} (attempt {attempt+1}/{MAX_RETRIES}): {e}")
        except Exception as e:
            logger.warning(f"LLM call failed for {ticker} (attempt {attempt+1}/{MAX_RETRIES}): {e}")

    logger.warning(f"All {MAX_RETRIES} attempts failed for {ticker} — falling back to cached news score")
    return {
        "news_score": state.get("cached_news_score"),
        "news_summary": state.get("cached_news_summary")
    }

if __name__ == "__main__":
    # Test 1: fresh run (no run_agents)
    result1 = news_agent({"ticker": "AAPL"})
    logger.info(f"FRESH RUN: {result1}")

    # Test 2: cache-skip path (news NOT in run_agents)
    result2 = news_agent({
        "ticker": "AAPL",
        "run_agents": ["technical", "risk"],  # news NOT included
        "cached_news_score": 50,
        "cached_news_summary": "Cached: neutral news flow from earlier run"
    })
    logger.info(f"CACHED RUN: {result2}")
