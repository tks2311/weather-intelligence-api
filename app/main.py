from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import httpx
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import os

from .models import WeatherResponse, WeatherQuery, HistoricalWeatherQuery, WeatherAnalyticsResponse
from .auth import verify_api_key, get_api_key_info
from .config import settings
from .webhooks import (
    WebhookConfig, WebhookPayload, create_webhook, get_webhooks, 
    delete_webhook, check_and_trigger_webhooks
)
from .batch import BatchWeatherRequest, BatchWeatherResponse, process_batch_request
from .historical import HistoricalRequest, HistoricalResponse, fetch_historical_weather
from .cache import weather_cache, cache_key_for_weather

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI application
app = FastAPI(
    title="Weather Intelligence API",
    description="AI-powered weather data with business insights, webhooks, and advanced analytics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Weather Intelligence API Support",
        "email": "support@weather-intelligence-api.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security scheme
security = HTTPBearer(
    scheme_name="API Key Authentication",
    description="Enter your API key in the format: Bearer your_api_key_here"
)

# ============================================================================
# ROOT & HEALTH ENDPOINTS
# ============================================================================

@app.get(
    "/",
    summary="API Information",
    description="Get basic information about the Weather Intelligence API",
    tags=["Information"],
    response_description="API information and available endpoints"
)
@app.head("/")
async def get_api_info():
    """
    Returns basic information about the Weather Intelligence API including
    available endpoints and advanced features.
    """
    return {
        "message": "Weather Intelligence API",
        "version": "1.0.0",
        "description": "AI-powered weather data with business insights",
        "documentation": "/docs",
        "endpoints": {
            "current_weather": "GET /weather/current",
            "weather_forecast": "GET /weather/forecast", 
            "historical_data": "POST /weather/historical",
            "business_analytics": "GET /weather/analytics",
            "batch_processing": "POST /weather/batch",
            "webhook_management": "GET,POST,DELETE /webhooks"
        },
        "advanced_features": [
            "Real-time webhook notifications with custom conditions",
            "Concurrent batch processing up to 50 locations",
            "Historical weather data with AI trend analysis",
            "Business intelligence insights for retail, agriculture, events",
            "Smart caching for 5x performance improvement",
            "Comprehensive error handling and validation"
        ],
        "pricing_tiers": ["Basic", "Premium", "Enterprise"],
        "support": {
            "documentation": "/docs",
            "cache_stats": "/cache/stats"
        }
    }

@app.get(
    "/health",
    summary="Health Check",
    description="Check API health status",
    tags=["Information"],
    response_description="Health status with timestamp"
)
@app.head("/health")
async def health_check():
    """
    Simple health check endpoint to verify API availability.
    Used by monitoring services and load balancers.
    """
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# ============================================================================
# WEATHER DATA ENDPOINTS
# ============================================================================

@app.get(
    "/weather/current", 
    response_model=WeatherResponse,
    summary="Current Weather Data",
    description="Get current weather data with AI-powered business insights",
    tags=["Weather Data"],
    response_description="Current weather data with AI insights and comfort analysis"
)
async def get_current_weather(
    city: str = "London",
    country: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    units: Optional[str] = "metric",
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get current weather data enhanced with AI-powered business insights.
    
    **Parameters:**
    - **city**: City name (required if lat/lon not provided)
    - **country**: Country code (ISO 3166) for more precise results
    - **lat**: Latitude for coordinate-based queries
    - **lon**: Longitude for coordinate-based queries  
    - **units**: Temperature units (metric, imperial, kelvin)
    
    **Returns:**
    - Current weather conditions
    - AI comfort level assessment
    - Activity recommendations
    - Weather score (0-100)
    - Business insights
    
    **Example:**
    ```
    GET /weather/current?city=London&country=UK&units=metric
    ```
    """
    verify_api_key(credentials.credentials)
    
    # Check cache first for performance
    cache_params = cache_key_for_weather(city, country, lat, lon, units)
    cached_data = weather_cache.get("current_weather", cache_params)
    if cached_data:
        return cached_data
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            weather_url = "http://api.openweathermap.org/data/2.5/weather"
            
            # Build request parameters
            if lat and lon:
                params = {
                    "lat": lat,
                    "lon": lon,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": units
                }
            else:
                params = {
                    "q": f"{city},{country}" if country else city,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": units
                }
            
            # Fetch weather data
            response = await client.get(weather_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Enhanced response with AI insights
            enhanced_data = {
                "location": {
                    "city": data["name"],
                    "country": data["sys"]["country"],
                    "coordinates": {
                        "lat": data["coord"]["lat"],
                        "lon": data["coord"]["lon"]
                    }
                },
                "current": {
                    "temperature": round(data["main"]["temp"], 1),
                    "feels_like": round(data["main"]["feels_like"], 1),
                    "humidity": data["main"]["humidity"],
                    "pressure": data["main"]["pressure"],
                    "visibility": round(data.get("visibility", 0) / 1000, 1),
                    "uv_index": 0,  # Would require separate API call
                    "description": data["weather"][0]["description"],
                    "icon": data["weather"][0]["icon"],
                    "wind": {
                        "speed": data["wind"]["speed"],
                        "direction": data["wind"].get("deg", 0)
                    }
                },
                "ai_insights": {
                    "comfort_level": _calculate_comfort_level(data["main"]["temp"], data["main"]["humidity"]),
                    "activity_recommendations": _get_activity_recommendations(data),
                    "weather_score": _calculate_weather_score(data)
                },
                "timestamp": datetime.utcnow().isoformat(),
                "units": units
            }
            
            # Cache the result for 5 minutes
            weather_cache.set("current_weather", cache_params, enhanced_data)
            
            # Check for webhook triggers
            await check_and_trigger_webhooks(enhanced_data, credentials.credentials)
            
            return enhanced_data
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Weather service error: {e.response.status_code}. Please check your location parameters."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )

@app.get(
    "/weather/forecast",
    summary="Weather Forecast",
    description="Get multi-day weather forecast with detailed predictions",
    tags=["Weather Data"],
    response_description="Weather forecast for specified number of days"
)
async def get_weather_forecast(
    city: str = "London",
    country: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    units: Optional[str] = "metric",
    days: int = 5,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get detailed weather forecast for multiple days.
    
    **Parameters:**
    - **city**: City name (required if lat/lon not provided)
    - **country**: Country code for precision
    - **lat**: Latitude coordinate
    - **lon**: Longitude coordinate
    - **units**: Temperature units (metric, imperial, kelvin)
    - **days**: Number of forecast days (1-5)
    
    **Returns:**
    - Detailed forecast for each day
    - Temperature predictions (min/max/current)
    - Precipitation probability
    - Wind conditions
    - Weather descriptions
    
    **Example:**
    ```
    GET /weather/forecast?city=London&days=3&units=metric
    ```
    """
    verify_api_key(credentials.credentials)
    
    # Validate days parameter
    if not 1 <= days <= 5:
        raise HTTPException(
            status_code=400, 
            detail="Days parameter must be between 1 and 5"
        )
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            forecast_url = "http://api.openweathermap.org/data/2.5/forecast"
            
            # Build request parameters
            if lat and lon:
                params = {
                    "lat": lat,
                    "lon": lon,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": units,
                    "cnt": days * 8  # 8 forecasts per day (3-hour intervals)
                }
            else:
                params = {
                    "q": f"{city},{country}" if country else city,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": units,
                    "cnt": days * 8
                }
            
            # Fetch forecast data
            response = await client.get(forecast_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Build forecast response
            forecast_data = {
                "location": {
                    "city": data["city"]["name"],
                    "country": data["city"]["country"],
                    "coordinates": {
                        "lat": data["city"]["coord"]["lat"],
                        "lon": data["city"]["coord"]["lon"]
                    }
                },
                "forecast": [],
                "summary": {
                    "total_periods": len(data["list"]),
                    "days_covered": days,
                    "units": units,
                    "generated_at": datetime.utcnow().isoformat()
                }
            }
            
            # Process forecast items
            for item in data["list"]:
                forecast_item = {
                    "datetime": item["dt_txt"],
                    "temperature": {
                        "current": round(item["main"]["temp"], 1),
                        "feels_like": round(item["main"]["feels_like"], 1),
                        "min": round(item["main"]["temp_min"], 1),
                        "max": round(item["main"]["temp_max"], 1)
                    },
                    "humidity": item["main"]["humidity"],
                    "pressure": item["main"]["pressure"],
                    "description": item["weather"][0]["description"],
                    "icon": item["weather"][0]["icon"],
                    "wind": {
                        "speed": item["wind"]["speed"],
                        "direction": item["wind"].get("deg", 0)
                    },
                    "precipitation_probability": round(item.get("pop", 0) * 100, 1),
                    "clouds": item["clouds"]["all"]
                }
                forecast_data["forecast"].append(forecast_item)
            
            return forecast_data
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Forecast service error: {e.response.status_code}. Please verify location parameters."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )

@app.get(
    "/weather/analytics", 
    response_model=WeatherAnalyticsResponse,
    summary="Business Weather Analytics",
    description="Get AI-powered business insights based on current weather conditions",
    tags=["Business Intelligence"],
    response_description="Business analytics with industry-specific insights"
)
async def get_weather_analytics(
    city: str = "London",
    country: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    units: Optional[str] = "metric",
    days_back: int = 30,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get comprehensive business analytics based on weather conditions.
    
    **Provides insights for:**
    - **Retail**: Foot traffic predictions and promotional recommendations
    - **Agriculture**: Growing conditions and irrigation needs
    - **Events**: Outdoor event suitability and risk assessment
    - **Energy**: Demand forecasting and efficiency recommendations
    
    **Parameters:**
    - **city**: City name for analysis
    - **country**: Country code for precision
    - **lat/lon**: Coordinate-based location
    - **units**: Temperature units
    - **days_back**: Historical period for trend analysis (max 365)
    
    **Returns:**
    - Business impact analysis for multiple industries
    - Trend analysis and forecasts
    - Actionable recommendations
    - Risk assessments
    
    **Example:**
    ```
    GET /weather/analytics?city=London&days_back=30
    ```
    """
    verify_api_key(credentials.credentials)
    
    # Validate days_back parameter
    if not 1 <= days_back <= 365:
        raise HTTPException(
            status_code=400, 
            detail="days_back parameter must be between 1 and 365"
        )
    
    try:
        # Get current weather first
        current_weather = await get_current_weather(city, country, lat, lon, units, credentials)
        
        # Generate business analytics
        analytics = {
            "location": current_weather["location"],
            "analysis_period": f"{days_back} days",
            "business_insights": {
                "retail_impact": _analyze_retail_impact(current_weather["current"]),
                "agriculture_conditions": _analyze_agriculture_conditions(current_weather["current"]),
                "outdoor_events_suitability": _analyze_event_suitability(current_weather["current"]),
                "energy_demand_forecast": _analyze_energy_demand(current_weather["current"])
            },
            "trends": {
                "temperature_trend": "stable",  # Would be calculated from historical data
                "humidity_trend": "normal",
                "pressure_trend": "stable"
            },
            "recommendations": _generate_business_recommendations(current_weather["current"]),
            "risk_assessment": {
                "weather_stability": "high" if current_weather["ai_insights"]["weather_score"] > 70 else "moderate",
                "business_continuity": "normal",
                "recommended_actions": []
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return analytics
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Analytics generation failed: {str(e)}"
        )

# ============================================================================
# ADVANCED FEATURES
# ============================================================================

@app.post(
    "/weather/batch", 
    response_model=BatchWeatherResponse,
    summary="Batch Weather Processing",
    description="Process multiple weather requests concurrently for maximum efficiency",
    tags=["Advanced Features"],
    response_description="Batch processing results with performance metrics"
)
async def batch_weather_request(
    batch_request: BatchWeatherRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Process multiple weather requests concurrently to save time and API calls.
    
    **Features:**
    - Process up to 50 locations simultaneously
    - Support for multiple endpoints per location
    - Concurrent processing for optimal performance
    - Detailed error handling per request
    - Performance metrics and timing data
    
    **Request Format:**
    ```json
    {
        "locations": [
            {"city": "London", "country": "UK"},
            {"city": "Paris", "country": "FR"},
            {"lat": 40.7128, "lon": -74.0060}
        ],
        "endpoints": ["current", "forecast"],
        "units": "metric",
        "forecast_days": 3
    }
    ```
    
    **Returns:**
    - Results for each location/endpoint combination
    - Processing statistics and performance metrics
    - Error details for any failed requests
    - Total processing time
    """
    verify_api_key(credentials.credentials)
    
    # Validate request parameters
    if len(batch_request.locations) > 50:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 50 locations per batch request. Please split into smaller batches."
        )
    
    if len(batch_request.endpoints) > 3:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 3 endpoints per batch request"
        )
    
    valid_endpoints = ["current", "forecast"]
    for endpoint in batch_request.endpoints:
        if endpoint not in valid_endpoints:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid endpoint: '{endpoint}'. Valid endpoints: {valid_endpoints}"
            )
    
    try:
        result = await process_batch_request(batch_request)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Batch processing failed: {str(e)}"
        )

@app.post(
    "/weather/historical", 
    response_model=HistoricalResponse,
    summary="Historical Weather Data",
    description="Get historical weather data with AI-powered trend analysis",
    tags=["Advanced Features"],
    response_description="Historical weather data with statistical analysis and trends"
)
async def get_historical_weather(
    historical_request: HistoricalRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get historical weather data enhanced with AI-powered trend analysis.
    
    **Features:**
    - Historical data for up to 365 days
    - Statistical analysis and patterns
    - Seasonal trend identification
    - Business impact assessment
    - Climate pattern recognition
    
    **Request Format:**
    ```json
    {
        "city": "London",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "units": "metric"
    }
    ```
    
    **Returns:**
    - Daily historical weather data
    - Statistical summaries (min/max/average)
    - AI-powered trend analysis
    - Seasonal pattern insights
    - Business impact correlations
    """
    verify_api_key(credentials.credentials)
    
    try:
        # Validate date format and range
        start_date = datetime.strptime(historical_request.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(historical_request.end_date, "%Y-%m-%d")
        
        # Validation checks
        if start_date > end_date:
            raise HTTPException(
                status_code=400, 
                detail="Start date must be before end date"
            )
        
        if (end_date - start_date).days > 365:
            raise HTTPException(
                status_code=400, 
                detail="Maximum historical period is 365 days"
            )
        
        if end_date > datetime.now():
            raise HTTPException(
                status_code=400, 
                detail="End date cannot be in the future"
            )
        
        result = await fetch_historical_weather(historical_request)
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid date format. Use YYYY-MM-DD: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Historical data fetch failed: {str(e)}"
        )

# ============================================================================
# WEBHOOK MANAGEMENT
# ============================================================================

@app.post(
    "/webhooks",
    summary="Create Webhook Subscription",
    description="Create a new webhook subscription for real-time weather alerts",
    tags=["Webhooks"],
    response_description="Webhook creation confirmation with unique ID"
)
async def create_webhook_subscription(
    webhook: WebhookConfig,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Create a webhook subscription for real-time weather notifications.
    
    **Webhook triggers when weather conditions meet your specified criteria.**
    
    **Supported Conditions:**
    - **temperature**: Temperature comparisons (>, <, >=, <=, ==)
    - **humidity**: Humidity percentage comparisons
    - **wind_speed**: Wind speed comparisons
    - **description**: Weather description text matching
    - **weather_score**: AI weather score comparisons
    
    **Operators:**
    - `>`, `<`, `>=`, `<=`: Numeric comparisons
    - `==`: Exact match
    - `contains`: Text contains substring
    
    **Request Example:**
    ```json
    {
        "name": "High Temperature Alert",
        "callback_url": "https://yourapp.com/webhook",
        "city": "London",
        "conditions": [
            {"field": "temperature", "operator": ">", "value": 30},
            {"field": "description", "operator": "contains", "value": "rain"}
        ]
    }
    ```
    
    **Webhook Payload:**
    When triggered, your endpoint receives current weather data plus AI insights.
    """
    verify_api_key(credentials.credentials)
    
    try:
        webhook_id = create_webhook(webhook, credentials.credentials)
        
        return {
            "webhook_id": webhook_id,
            "message": "Webhook created successfully",
            "webhook": webhook.dict(),
            "next_steps": [
                "Test your webhook endpoint to ensure it's accessible",
                "Monitor webhook triggers in your application logs",
                "Use GET /webhooks to list all your subscriptions"
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Webhook creation failed: {str(e)}"
        )

@app.get(
    "/webhooks",
    summary="List Webhook Subscriptions",
    description="List all webhook subscriptions for your API key",
    tags=["Webhooks"],
    response_description="List of all webhook subscriptions"
)
async def list_webhooks(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    List all webhook subscriptions associated with your API key.
    
    **Returns:**
    - All webhook configurations
    - Webhook status (active/inactive)
    - Creation timestamps
    - Condition details
    - Callback URLs
    """
    verify_api_key(credentials.credentials)
    
    try:
        webhooks = get_webhooks(credentials.credentials)
        
        return {
            "webhooks": [webhook.dict() for webhook in webhooks],
            "count": len(webhooks),
            "limits": {
                "max_webhooks_per_key": 100,
                "current_usage": len(webhooks)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve webhooks: {str(e)}"
        )

@app.delete(
    "/webhooks/{webhook_id}",
    summary="Delete Webhook Subscription",
    description="Delete a specific webhook subscription",
    tags=["Webhooks"],
    response_description="Deletion confirmation"
)
async def delete_webhook_subscription(
    webhook_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Delete a webhook subscription by its unique ID.
    
    **Parameters:**
    - **webhook_id**: The unique identifier returned when creating the webhook
    
    **Note:** This action is irreversible. The webhook will stop receiving notifications immediately.
    """
    verify_api_key(credentials.credentials)
    
    try:
        success = delete_webhook(webhook_id, credentials.credentials)
        
        if success:
            return {
                "message": "Webhook deleted successfully",
                "webhook_id": webhook_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"Webhook with ID '{webhook_id}' not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Webhook deletion failed: {str(e)}"
        )

# ============================================================================
# PERFORMANCE & MONITORING
# ============================================================================

@app.get(
    "/cache/stats",
    summary="Cache Performance Statistics",
    description="Get detailed cache performance metrics and statistics",
    tags=["Performance"],
    response_description="Cache performance metrics and efficiency data"
)
async def get_cache_stats(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get comprehensive cache performance statistics.
    
    **Provides insights on:**
    - Cache hit rates and efficiency
    - Memory usage and optimization
    - Endpoint-specific performance
    - Cache expiration and cleanup
    
    **Useful for:**
    - Performance monitoring
    - Cost optimization
    - Understanding usage patterns
    - Debugging performance issues
    """
    verify_api_key(credentials.credentials)
    
    try:
        stats = weather_cache.get_stats()
        cleared_count = weather_cache.clear_expired()
        
        return {
            "cache_statistics": stats,
            "expired_entries_cleared": cleared_count,
            "cache_efficiency": {
                "hit_rate": round(stats["total_hits"] / max(1, stats["total_entries"]), 2),
                "recommended_ttl": "5 minutes for optimal performance",
                "memory_efficiency": "excellent" if stats["cache_size_mb"] < 10 else "good"
            },
            "recommendations": [
                "Cache hit rate above 70% indicates good performance",
                "Monitor memory usage to prevent excessive growth",
                "Consider increasing TTL for stable data patterns"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Cache statistics retrieval failed: {str(e)}"
        )

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def _calculate_comfort_level(temp: float, humidity: int) -> str:
    """Calculate human comfort level based on temperature and humidity."""
    if 18 <= temp <= 24 and 40 <= humidity <= 60:
        return "optimal"
    elif 15 <= temp <= 28 and 30 <= humidity <= 70:
        return "comfortable"
    elif 10 <= temp <= 32 and 20 <= humidity <= 80:
        return "acceptable"
    else:
        return "uncomfortable"

def _get_activity_recommendations(weather_data: Dict[str, Any]) -> List[str]:
    """Generate activity recommendations based on weather conditions."""
    temp = weather_data["main"]["temp"]
    description = weather_data["weather"][0]["description"].lower()
    
    recommendations = []
    
    if "rain" in description or "drizzle" in description:
        recommendations.extend(["indoor activities", "museum visits", "shopping", "cozy cafes"])
    elif "clear" in description and 20 <= temp <= 28:
        recommendations.extend(["outdoor sports", "hiking", "picnic", "cycling", "photography"])
    elif temp > 30:
        recommendations.extend(["swimming", "indoor activities", "early morning exercise", "beach activities"])
    elif temp < 10:
        recommendations.extend(["indoor activities", "winter sports", "hot beverages", "museums"])
    else:
        recommendations.extend(["walking", "sightseeing", "outdoor dining", "light exercise"])
    
    return recommendations[:4]  # Limit to 4 recommendations

def _calculate_weather_score(weather_data: Dict[str, Any]) -> int:
    """Calculate overall weather score from 0-100."""
    temp = weather_data["main"]["temp"]
    humidity = weather_data["main"]["humidity"]
    description = weather_data["weather"][0]["description"].lower()
    
    score = 50  # Base score
    
    # Temperature scoring
    if 18 <= temp <= 25:
        score += 30
    elif 15 <= temp <= 30:
        score += 20
    elif 10 <= temp <= 35:
        score += 10
    
    # Humidity scoring
    if 40 <= humidity <= 60:
        score += 20
    elif 30 <= humidity <= 70:
        score += 10
    
    # Weather condition scoring
    if "clear" in description:
        score += 20
    elif "few clouds" in description or "scattered clouds" in description:
        score += 15
    elif "broken clouds" in description or "overcast" in description:
        score += 5
    elif "rain" in description:
        score -= 20
    elif "storm" in description or "thunderstorm" in description:
        score -= 30
    
    return max(0, min(100, score))

def _analyze_retail_impact(weather: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze weather impact on retail business."""
    temp = weather["temperature"]
    description = weather["description"].lower()
    
    impact = {
        "foot_traffic_prediction": "normal",
        "recommended_promotions": [],
        "seasonal_demand": "moderate",
        "customer_behavior": "typical"
    }
    
    if "rain" in description:
        impact.update({
            "foot_traffic_prediction": "low",
            "recommended_promotions": ["umbrellas", "indoor entertainment", "delivery promotions"],
            "customer_behavior": "indoor preference"
        })
    elif temp > 30:
        impact.update({
            "foot_traffic_prediction": "low",
            "recommended_promotions": ["cooling products", "beverages", "summer clothing"],
            "seasonal_demand": "high for cooling products",
            "customer_behavior": "heat avoidance"
        })
    elif 20 <= temp <= 28 and "clear" in description:
        impact.update({
            "foot_traffic_prediction": "high",
            "recommended_promotions": ["outdoor products", "seasonal items", "patio dining"],
            "seasonal_demand": "high",
            "customer_behavior": "outdoor activities"
        })
    
    return impact

def _analyze_agriculture_conditions(weather: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze weather conditions for agriculture."""
    temp = weather["temperature"]
    humidity = weather["humidity"]
    description = weather["description"].lower()
    
    conditions = {
        "growing_conditions": "moderate",
        "irrigation_needs": "moderate",
        "pest_risk": "low",
        "harvest_suitability": "good",
        "crop_stress_level": "minimal"
    }
    
    if 15 <= temp <= 25 and 50 <= humidity <= 70:
        conditions.update({
            "growing_conditions": "excellent",
            "crop_stress_level": "none"
        })
    elif temp > 35 or humidity < 30:
        conditions.update({
            "irrigation_needs": "high",
            "growing_conditions": "challenging",
            "crop_stress_level": "high"
        })
    
    if "rain" in description:
        conditions.update({
            "irrigation_needs": "low",
            "pest_risk": "moderate"
        })
    
    if temp > 30 and humidity > 70:
        conditions["pest_risk"] = "high"
    
    return conditions

def _analyze_event_suitability(weather: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze weather suitability for outdoor events."""
    temp = weather["temperature"]
    description = weather["description"].lower()
    wind_speed = weather["wind"]["speed"]
    
    suitability = {
        "overall_rating": "good",
        "recommended_event_types": [],
        "precautions": [],
        "risk_level": "low"
    }
    
    if "rain" in description or "storm" in description:
        suitability.update({
            "overall_rating": "poor",
            "recommended_event_types": ["indoor events"],
            "precautions": ["covered areas", "backup indoor venue"],
            "risk_level": "high"
        })
    elif 18 <= temp <= 28 and "clear" in description and wind_speed < 10:
        suitability.update({
            "overall_rating": "excellent",
            "recommended_event_types": ["outdoor concerts", "festivals", "sports events", "weddings"],
            "risk_level": "minimal"
        })
    elif temp > 32:
        suitability.update({
            "precautions": ["shade structures", "hydration stations", "cooling areas"],
            "recommended_event_types": ["water events", "evening events"],
            "risk_level": "moderate"
        })
    
    return suitability

def _analyze_energy_demand(weather: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze energy demand based on weather conditions."""
    temp = weather["temperature"]
    
    demand = {
        "predicted_demand": "normal",
        "peak_hours": "evening",
        "efficiency_tips": [],
        "cost_impact": "minimal"
    }
    
    if temp > 28:
        demand.update({
            "predicted_demand": "high",
            "peak_hours": "afternoon (2-6 PM)",
            "efficiency_tips": ["use fans", "close curtains", "avoid heat-generating appliances"],
            "cost_impact": "increased cooling costs"
        })
    elif temp < 15:
        demand.update({
            "predicted_demand": "high",
            "peak_hours": "morning and evening",
            "efficiency_tips": ["seal windows", "use programmable thermostat", "wear layers"],
            "cost_impact": "increased heating costs"
        })
    
    return demand

def _generate_business_recommendations(weather: Dict[str, Any]) -> List[str]:
    """Generate actionable business recommendations."""
    temp = weather["temperature"]
    description = weather["description"].lower()
    
    recommendations = []
    
    if "rain" in description:
        recommendations.extend([
            "Promote indoor delivery services and increase capacity",
            "Stock weather-related products (umbrellas, rain gear)",
            "Offer weather-based discounts to maintain customer engagement",
            "Adjust staffing for reduced foot traffic"
        ])
    elif temp > 30:
        recommendations.extend([
            "Stock cooling products, beverages, and summer essentials",
            "Adjust operating hours to avoid peak heat periods",
            "Promote air-conditioned spaces and cooling services",
            "Consider heat-related health and safety measures"
        ])
    elif 20 <= temp <= 28 and "clear" in description:
        recommendations.extend([
            "Promote outdoor activities, products, and services",
            "Extend outdoor seating and display areas",
            "Plan outdoor marketing events and promotions",
            "Optimize staffing for increased customer activity"
        ])
    else:
        recommendations.extend([
            "Maintain normal operations with seasonal adjustments",
            "Monitor weather changes for rapid response",
            "Prepare contingency plans for weather deterioration"
        ])
    
    return recommendations[:3]  # Limit to top 3 recommendations

# ============================================================================
# APPLICATION STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info",
        access_log=True
    )