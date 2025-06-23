from fastapi import HTTPException, status
from datetime import datetime, timedelta
import secrets
import hashlib
from typing import Dict, Optional

API_KEYS_DB = {
    "demo_key_12345": {
        "name": "Demo Key",
        "tier": "basic",
        "created_at": datetime.utcnow(),
        "is_active": True,
        "requests_count": 0,
        "daily_limit": 1000,
        "monthly_limit": 10000,
        "last_used": None
    }
}

TIER_LIMITS = {
    "basic": {"daily": 1000, "monthly": 10000, "rate_limit": "100/minute"},
    "premium": {"daily": 10000, "monthly": 100000, "rate_limit": "500/minute"},
    "enterprise": {"daily": 100000, "monthly": 1000000, "rate_limit": "1000/minute"}
}

def verify_api_key(api_key: str) -> Dict:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required"
        )
    
    if api_key not in API_KEYS_DB:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    key_info = API_KEYS_DB[api_key]
    
    if not key_info["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is inactive"
        )
    
    if _check_rate_limits(api_key, key_info):
        key_info["requests_count"] += 1
        key_info["last_used"] = datetime.utcnow()
        return key_info
    else:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )

def _check_rate_limits(api_key: str, key_info: Dict) -> bool:
    tier = key_info["tier"]
    limits = TIER_LIMITS[tier]
    
    now = datetime.utcnow()
    
    if key_info["last_used"] and (now - key_info["last_used"]).days == 0:
        if key_info["requests_count"] >= limits["daily"]:
            return False
    
    return True

def generate_api_key(name: str, tier: str = "basic") -> str:
    api_key = f"{tier}_{secrets.token_urlsafe(32)}"
    
    API_KEYS_DB[api_key] = {
        "name": name,
        "tier": tier,
        "created_at": datetime.utcnow(),
        "is_active": True,
        "requests_count": 0,
        "daily_limit": TIER_LIMITS[tier]["daily"],
        "monthly_limit": TIER_LIMITS[tier]["monthly"],
        "last_used": None
    }
    
    return api_key

def deactivate_api_key(api_key: str) -> bool:
    if api_key in API_KEYS_DB:
        API_KEYS_DB[api_key]["is_active"] = False
        return True
    return False

def get_api_key_info(api_key: str) -> Optional[Dict]:
    return API_KEYS_DB.get(api_key)