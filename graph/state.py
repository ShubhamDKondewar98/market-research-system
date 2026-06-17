from typing import TypedDict, Optional, List 

class AgentState(TypedDict):
    ticker: str      #### initail ticker 
    technical_score:Optional[float]   ##   technical agent score
    technical_summary:Optional[str]   ##   technical agent summary
    news_score:Optional[float]        ##   news agent score
    news_summary:Optional[str]        ##   news  agent  summary
    sentiment_score:Optional[float]   ##   sentimental  agent  score 
    sentiment_summary:Optional[str]   ##   sentimental agent  summary 
    risk_score:Optional[float]        ##   risk  agent  score 
    risk_summary:Optional[str]        ##   risk agent  summary 
    previous_confidence:Optional[int]  ##  for delta previous confidence required from db
    confidence:Optional[int]            ##  current confidence generated
    decision:Optional[str]               ##  final decision what need to do 
    delta:Optional[float]                 ##  chnage in previous and current
    changed_agents:Optional[list]
    reasoning:Optional[str]
    alert_type:Optional[str]                
    run_agents:Optional[list]
    interval: str

    cached_technical_score: Optional[float]
    cached_technical_summary: Optional[str]
    cached_news_score: Optional[float]      
    cached_news_summary:Optional[str]  
    cached_sentiment_score:Optional[float]  
    cached_sentiment_summary:Optional[str]    
    cached_risk_score:Optional[float]       
    cached_risk_summary:Optional[str]  




 