import sys
sys.path.insert(0, '.')
from graph.pipeline import graph

if __name__ == "__main__":
    result = graph.invoke({
        "ticker": "AAPL",
        "interval": "1d"
    })
    
    print("\n=== MARKET ANALYSIS RESULT ===")
    print(f"Ticker:     {result['ticker']}")
    print(f"Decision:   {result['decision']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"Alert Type: {result['alert_type']}")
    print(f"Reasoning:  {result['reasoning']}")
    print("\nAgent Scores:")
    print(f"  Technical:  {result['technical_score']}")
    print(f"  News:       {result['news_score']}")
    print(f"  Sentiment:  {result['sentiment_score']}")
    print(f"  Risk:       {result['risk_score']}")