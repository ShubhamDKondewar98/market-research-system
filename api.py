from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import sys
sys.path.insert(0, '.')
from graph.pipeline import graph
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
import os
from fastapi import FastAPI, Header, HTTPException , Request
from fastapi.responses import JSONResponse


API_KEY = os.environ.get("API_SECRET_KEY")

app = FastAPI()

@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    if request.url.path == "/health":
        response = await call_next(request)
        return response

    api_key = request.headers.get("X-API-Key")
    if api_key != API_KEY:
        return JSONResponse(status_code=401, content = {"details":"Unathorised"})
    response = await call_next(request)
    return response
    

class PipelineRequest(BaseModel):
    ticker: str
    interval: str = "1d"
    run_agents: Optional[List[str]] = None
    cached_technical_score: Optional[float] = None
    cached_technical_summary: Optional[str] = None
    cached_news_score: Optional[float] = None
    cached_news_summary: Optional[str] = None
    cached_sentiment_score: Optional[float] = None
    cached_sentiment_summary: Optional[str] = None
    cached_risk_score: Optional[float] = None
    cached_risk_summary: Optional[str] = None
    previous_confidence: Optional[float] = None
    previous_technical_score: Optional[float] = None
    previous_news_score: Optional[float] = None
    previous_sentiment_score: Optional[float] = None
    previous_risk_score: Optional[float] = None


@app.post("/analyze")
def analyze(request: PipelineRequest):
    payload = request.model_dump()

    try:
        result = graph.invoke(payload)
        return {
            "ticker": result["ticker"],
            "decision": result["decision"],
            "confidence": result["confidence"],
            "alert_type": result["alert_type"],
            "reasoning": result["reasoning"],
            "technical_score": result["technical_score"],
            "news_score": result["news_score"],
            "sentiment_score": result["sentiment_score"],
            "risk_score": result["risk_score"],
            "technical_summary": result["technical_summary"],
            "news_summary": result["news_summary"],
            "sentiment_summary": result["sentiment_summary"],
            "risk_summary": result["risk_summary"]
        }
    except Exception as e:
        logger.warning(f"Error invoking pipeline for {request.ticker}: {e}")
        return {"error": str(e), "ticker": request.ticker}
            
    
@app.get("/health")
def health():
    return {"status": "ok"}