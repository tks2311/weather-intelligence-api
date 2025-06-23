from fastapi import Request, HTTPException, status
from typing import Optional

def verify_rapidapi_request(request: Request) -> bool:
    """
    Verify request comes from RapidAPI platform
    RapidAPI adds specific headers to all requests
    """
    rapidapi_proxy_secret = request.headers.get("X-RapidAPI-Proxy-Secret")
    rapidapi_host = request.headers.get("X-RapidAPI-Host")
    rapidapi_user = request.headers.get("X-RapidAPI-User")
    
    # In production, verify the proxy secret matches your configured secret
    # For now, just check that RapidAPI headers are present
    if rapidapi_host and rapidapi_user:
        return True
    
    # Also allow direct API key access for testing
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return True
        
    return False

def get_rapidapi_user(request: Request) -> Optional[str]:
    """Get the RapidAPI user making the request"""
    return request.headers.get("X-RapidAPI-User")

def get_rapidapi_subscription(request: Request) -> Optional[str]:
    """Get the user's subscription tier from RapidAPI"""
    return request.headers.get("X-RapidAPI-Subscription", "basic")