from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import httpx
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os

from .models import WeatherResponse, WeatherQuery, HistoricalWeatherQuery, WeatherAnalyticsResponse
from .auth import verify_api_key
from .config import settings

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="Weather Intelligence API",
    description="Advanced weather data and analytics API with AI-powered insights",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

@app.get("/")
async def root():
    return {
        "message": "Weather Intelligence API",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "current_weather": "/weather/current",
            "forecast": "/weather/forecast",
            "historical": "/weather/historical",
            "analytics": "/weather/analytics"
        }
    }

@app.get("/weather/current", response_model=WeatherResponse)
@limiter.limit("100/minute")
async def get_current_weather(
    request: Request,
    city: str,
    country: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    units: Optional[str] = "metric",
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    verify_api_key(credentials.credentials)
    
    try:
        async with httpx.AsyncClient() as client:
            weather_url = f"http://api.openweathermap.org/data/2.5/weather"
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
            
            response = await client.get(weather_url, params=params)
            response.raise_for_status()
            data = response.json()
            
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
                    "temperature": data["main"]["temp"],
                    "feels_like": data["main"]["feels_like"],
                    "humidity": data["main"]["humidity"],
                    "pressure": data["main"]["pressure"],
                    "visibility": data.get("visibility", 0) / 1000,
                    "uv_index": 0,
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
            
            return enhanced_data
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"Weather service error: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/weather/forecast")
@limiter.limit("50/minute")
async def get_weather_forecast(
    request: Request,
    city: str,
    country: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    units: Optional[str] = "metric",
    days: int = 5,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    verify_api_key(credentials.credentials)
    
    try:
        async with httpx.AsyncClient() as client:
            forecast_url = f"http://api.openweathermap.org/data/2.5/forecast"
            if lat and lon:
                params = {
                    "lat": lat,
                    "lon": lon,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": units,
                    "cnt": days * 8
                }
            else:
                params = {
                    "q": f"{city},{country}" if country else city,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": units,
                    "cnt": days * 8
                }
            
            response = await client.get(forecast_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            forecast_data = {
                "location": {
                    "city": data["city"]["name"],
                    "country": data["city"]["country"],
                    "coordinates": {
                        "lat": data["city"]["coord"]["lat"],
                        "lon": data["city"]["coord"]["lon"]
                    }
                },
                "forecast": []
            }
            
            for item in data["list"]:
                forecast_item = {
                    "datetime": item["dt_txt"],
                    "temperature": {
                        "current": item["main"]["temp"],
                        "feels_like": item["main"]["feels_like"],
                        "min": item["main"]["temp_min"],
                        "max": item["main"]["temp_max"]
                    },
                    "humidity": item["main"]["humidity"],
                    "pressure": item["main"]["pressure"],
                    "description": item["weather"][0]["description"],
                    "icon": item["weather"][0]["icon"],
                    "wind": {
                        "speed": item["wind"]["speed"],
                        "direction": item["wind"].get("deg", 0)
                    },
                    "precipitation_probability": item.get("pop", 0) * 100
                }
                forecast_data["forecast"].append(forecast_item)
            
            return forecast_data
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"Weather service error: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/weather/analytics", response_model=WeatherAnalyticsResponse)
@limiter.limit("20/minute")
async def get_weather_analytics(
    request: Request,
    city: str,
    country: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    units: Optional[str] = "metric",
    days_back: int = 30,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    verify_api_key(credentials.credentials)
    
    current_weather = await get_current_weather(request, city, country, lat, lon, units, credentials)
    
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
            "temperature_trend": "stable",
            "humidity_trend": "increasing",
            "pressure_trend": "stable"
        },
        "recommendations": _generate_business_recommendations(current_weather["current"]),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return analytics

def _calculate_comfort_level(temp: float, humidity: int) -> str:
    if 18 <= temp <= 24 and 40 <= humidity <= 60:
        return "optimal"
    elif 15 <= temp <= 28 and 30 <= humidity <= 70:
        return "comfortable"
    elif 10 <= temp <= 32 and 20 <= humidity <= 80:
        return "acceptable"
    else:
        return "uncomfortable"

def _get_activity_recommendations(weather_data: Dict[str, Any]) -> list:
    temp = weather_data["main"]["temp"]
    description = weather_data["weather"][0]["description"].lower()
    
    recommendations = []
    
    if "rain" in description or "drizzle" in description:
        recommendations.extend(["indoor activities", "museum visits", "shopping"])
    elif "clear" in description and 20 <= temp <= 28:
        recommendations.extend(["outdoor sports", "hiking", "picnic"])
    elif temp > 30:
        recommendations.extend(["swimming", "indoor activities", "early morning exercise"])
    elif temp < 10:
        recommendations.extend(["indoor activities", "winter sports", "hot beverages"])
    else:
        recommendations.extend(["walking", "sightseeing", "outdoor dining"])
    
    return recommendations

def _calculate_weather_score(weather_data: Dict[str, Any]) -> int:
    temp = weather_data["main"]["temp"]
    humidity = weather_data["main"]["humidity"]
    description = weather_data["weather"][0]["description"].lower()
    
    score = 50
    
    if 18 <= temp <= 25:
        score += 30
    elif 15 <= temp <= 30:
        score += 20
    elif 10 <= temp <= 35:
        score += 10
    
    if 40 <= humidity <= 60:
        score += 20
    elif 30 <= humidity <= 70:
        score += 10
    
    if "clear" in description:
        score += 20
    elif "clouds" in description:
        score += 10
    elif "rain" in description:
        score -= 20
    elif "storm" in description:
        score -= 30
    
    return max(0, min(100, score))

def _analyze_retail_impact(weather: Dict[str, Any]) -> Dict[str, Any]:
    temp = weather["temperature"]
    description = weather["description"].lower()
    
    impact = {
        "foot_traffic_prediction": "normal",
        "recommended_promotions": [],
        "seasonal_demand": "moderate"
    }
    
    if "rain" in description:
        impact["foot_traffic_prediction"] = "low"
        impact["recommended_promotions"] = ["umbrellas", "indoor entertainment", "delivery promotions"]
    elif temp > 30:
        impact["foot_traffic_prediction"] = "low"
        impact["recommended_promotions"] = ["cooling products", "beverages", "indoor activities"]
        impact["seasonal_demand"] = "high for cooling products"
    elif 20 <= temp <= 28 and "clear" in description:
        impact["foot_traffic_prediction"] = "high"
        impact["recommended_promotions"] = ["outdoor products", "seasonal items"]
        impact["seasonal_demand"] = "high"
    
    return impact

def _analyze_agriculture_conditions(weather: Dict[str, Any]) -> Dict[str, Any]:
    temp = weather["temperature"]
    humidity = weather["humidity"]
    description = weather["description"].lower()
    
    conditions = {
        "growing_conditions": "moderate",
        "irrigation_needs": "moderate",
        "pest_risk": "low",
        "harvest_suitability": "good"
    }
    
    if 15 <= temp <= 25 and 50 <= humidity <= 70:
        conditions["growing_conditions"] = "excellent"
    elif temp > 35 or humidity < 30:
        conditions["irrigation_needs"] = "high"
        conditions["growing_conditions"] = "challenging"
    
    if "rain" in description:
        conditions["irrigation_needs"] = "low"
        conditions["pest_risk"] = "moderate"
    
    if temp > 30 and humidity > 70:
        conditions["pest_risk"] = "high"
    
    return conditions

def _analyze_event_suitability(weather: Dict[str, Any]) -> Dict[str, Any]:
    temp = weather["temperature"]
    description = weather["description"].lower()
    wind_speed = weather["wind"]["speed"]
    
    suitability = {
        "overall_rating": "good",
        "recommended_event_types": [],
        "precautions": []
    }
    
    if "rain" in description or "storm" in description:
        suitability["overall_rating"] = "poor"
        suitability["recommended_event_types"] = ["indoor events"]
        suitability["precautions"] = ["covered areas", "backup indoor venue"]
    elif 18 <= temp <= 28 and "clear" in description and wind_speed < 10:
        suitability["overall_rating"] = "excellent"
        suitability["recommended_event_types"] = ["outdoor concerts", "festivals", "sports events"]
    elif temp > 32:
        suitability["precautions"] = ["shade structures", "hydration stations", "cooling areas"]
        suitability["recommended_event_types"] = ["water events", "evening events"]
    
    return suitability

def _analyze_energy_demand(weather: Dict[str, Any]) -> Dict[str, Any]:
    temp = weather["temperature"]
    
    demand = {
        "predicted_demand": "normal",
        "peak_hours": "evening",
        "efficiency_tips": []
    }
    
    if temp > 28:
        demand["predicted_demand"] = "high"
        demand["peak_hours"] = "afternoon"
        demand["efficiency_tips"] = ["use fans", "close curtains", "avoid heat-generating appliances"]
    elif temp < 15:
        demand["predicted_demand"] = "high"
        demand["peak_hours"] = "morning and evening"
        demand["efficiency_tips"] = ["seal windows", "use programmable thermostat", "wear layers"]
    
    return demand

def _generate_business_recommendations(weather: Dict[str, Any]) -> list:
    temp = weather["temperature"]
    description = weather["description"].lower()
    
    recommendations = []
    
    if "rain" in description:
        recommendations.extend([
            "Promote indoor delivery services",
            "Increase inventory of weather-related products",
            "Offer weather-based discounts"
        ])
    elif temp > 30:
        recommendations.extend([
            "Stock cooling products and beverages",
            "Adjust operating hours to avoid peak heat",
            "Promote air-conditioned spaces"
        ])
    elif 20 <= temp <= 28:
        recommendations.extend([
            "Promote outdoor activities and products",
            "Extend outdoor seating capacity",
            "Plan outdoor marketing events"
        ])
    
    return recommendations

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)