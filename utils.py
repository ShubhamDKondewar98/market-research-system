from datetime import datetime, timedelta, timezone

import time
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)



def validate_agent_score(value, field_name: str, cached_fallback, ticker: str) -> float:
    """
    Validates that an LLM-produced score is a float within 0-100.
    Falls back to cached_fallback and logs a warning if validation fails.
    """
    try:
        score = float(value)
        if not (0 <= score <= 100):
            raise ValueError(f"{field_name} value {score} out of range for {ticker}")
        return score
    except (TypeError, ValueError) as e:
        logger.warning(f"Validation failed for {field_name} ({ticker}): {e} — using cached fallback")
        return cached_fallback



def utc_now():
    """
    return the current time as timezone-aware UTC datetime for consistent freshness 
    comparison against datbase timestamp  
    """
    return  datetime.now(timezone.utc)