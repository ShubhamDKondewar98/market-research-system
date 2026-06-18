import psycopg2

def last_known_scores(ticker: str) -> dict | None:

    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT technical_score, news_score, sentiment_score, risk_score, run_timestamp "
        "FROM agent_scores WHERE ticker = %s ORDER BY run_timestamp DESC LIMIT 1",
        (ticker,)
    )
    
    row = cursor.fetchone()
    
    if row is None:
        return None  # brand new ticker, never analyzed before
    
    # row exists — build the dict
    return {
        "technical_score": row[0],
        "news_score": row[1],
        "sentiment_score": row[2],
        "risk_score": row[3],
        "run_timestamp": row[4]
    } 

    