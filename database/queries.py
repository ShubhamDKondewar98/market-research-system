import psycopg2
import os 
from dotenv import load_dotenv
load_dotenv()


def get_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])    


def last_known_scores(ticker: str) -> dict | None:
    conn = get_connection()  
    cursor = conn.cursor()   
    row = None
    try:
        cursor.execute(
            "SELECT technical_score, news_score, sentiment_score, risk_score, technical_computed_at , news_computed_at , "
            " sentiment_computed_at ,risk_computed_at FROM agent_scores WHERE ticker = %s ORDER BY sentiment_computed_at DESC LIMIT 1",
            (ticker,)
        )   
        row = cursor.fetchone()

    except Exception as e:
        conn.rollback()
        print(f"Error fetching last known scores for {ticker}: {e}")
    finally:
        cursor.close()
        conn.close()
        
        
    if row is None:
        return None  # brand new ticker, never analyzed before  
    # row exists — build the dict
    return {
        "technical_score": row[0],
        "news_score": row[1],
        "sentiment_score": row[2],
        "risk_score": row[3],
        "technical_computed_at":row[4],
        "news_computed_at":row[5],
        "sentiment_computed_at":row[6],
        "risk_computed_at":row[7]   
    } 


def save_agent_scores(ticker: str,technical_score: float,news_score: float,
                      sentiment_score: float,risk_score: float,technical_computed_at,
                      news_computed_at,sentiment_computed_at,risk_computed_at)-> None:
    conn = get_connection()  
    cursor = conn.cursor() 

    try:
        cursor.execute(
            "INSERT INTO agent_scores  "
         "(ticker, technical_score, news_score, sentiment_score, risk_score, "
         "technical_computed_at, news_computed_at, sentiment_computed_at, risk_computed_at) "
          "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)  " ,
          (ticker,technical_score,news_score,sentiment_score,risk_score,technical_computed_at,
           news_computed_at,sentiment_computed_at,risk_computed_at)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error saving agent scores for {ticker}: {e}")
    finally:
        cursor.close()
        conn.close()
    


def get_previous_confidence(ticker: str) -> float | None:
    conn = get_connection()  
    cursor = conn.cursor()
    row = None
    try:
        cursor.execute(
            "SELECT confidence_score FROM confidence_history "
            "WHERE ticker = %s ORDER BY recorded_at DESC LIMIT 1 " ,
            (ticker,)
            )  
        row = cursor.fetchone()   
    except Exception as e:
        print(f"Error fetching previous confidence for {ticker}: {e}")
    finally:
        cursor.close()
        conn.close()

    if row is None:
        return None
    return float(row[0])


def save_confidence(ticker: str, confidence: float, decision: str, delta: float) -> None:
    conn = get_connection()  
    cursor = conn.cursor() 
    try:
        cursor.execute(
            "INSERT INTO confidence_history (ticker, confidence_score, decision, delta) "
            "VALUES (%s, %s, %s, %s)" ,
            (ticker,confidence,decision,delta)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error saving confidence for {ticker}: {e}")
    finally:
        cursor.close()
        conn.close()

def save_alert(ticker: str, alert_type: str, message: str, confidence: float) -> None:
    conn = get_connection()  
    cursor = conn.cursor() 
    try:
        cursor.execute(
            "INSERT INTO alert_log (ticker, alert_type, message, confidence_score_at_alert) "
            "VALUES (%s, %s, %s, %s)" ,
            (ticker,alert_type,message,confidence)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error saving alert for {ticker}: {e}")
    finally:
        cursor.close()
        conn.close()

def save_execution_log(ticker: str, run_result: str, run_time, error_msg: str = None) -> None:
    conn = get_connection()  
    cursor = conn.cursor() 
    try:
        cursor.execute(
            "INSERT INTO execution_log (ticker, run_result, run_time, error_msg) "
            "VALUES (%s, %s, %s, %s)" ,
            (ticker,run_result,run_time,error_msg)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error saving execution log for {ticker}: {e}")
    finally:
        cursor.close()
        conn.close()


def get_watchlist_by_tier(tier: str) -> list:
    conn = get_connection()  
    cursor = conn.cursor()
    rows = []
    try:
        cursor.execute(
            "SELECT ticker FROM watchlist WHERE tier = %s " ,
            (tier,)
            )  
        rows = cursor.fetchall()   
    except Exception as e:
        print(f"Error fetching watchlist for tier {tier}: {e}")
    finally:
        cursor.close()
        conn.close()

    if rows is None or len(rows) == 0:
        return []
    return [row[0] for row in rows]
    # SELECT ticker FROM watchlist WHERE tier = %s
    # return list of ticker strings 
    
    

    