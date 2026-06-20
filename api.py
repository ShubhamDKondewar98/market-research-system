from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import sys
sys.path.insert(0, '.')
from graph.pipeline import graph

app = FastAPI()

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

@app.post("/analyze")
def analyze(request: PipelineRequest):
    payload = request.dict()
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

@app.get("/health")
def health():
    return {"status": "ok"}