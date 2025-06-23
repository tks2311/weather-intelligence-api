from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
import asyncio
from .config import settings

class HistoricalRequest(BaseModel):
    city: str
    country: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    units: Optional[str] = "metric"

class HistoricalWeatherData(BaseModel):
    date: str
    temperature: Dict[str, float]  # min, max, avg
    humidity: float
    pressure: float
    wind_speed: float
    description: str
    precipitation: float

class HistoricalResponse(BaseModel):
    location: Dict[str, Any]
    period: Dict[str, Any]
    historical_data: List[HistoricalWeatherData]
    statistics: Dict[str, Any]
    ai_trends: Dict[str, Any]

async def fetch_historical_weather(request: HistoricalRequest) -> HistoricalResponse:
    """
    Fetch historical weather data using OpenWeather One Call API
    Note: This requires a paid OpenWeather subscription for historical data
    For demo purposes, we'll simulate historical data based on current patterns
    """
    try:
        # Get current weather to base historical simulation on
        async with httpx.AsyncClient(timeout=30.0) as client:
            current_url = "http://api.openweathermap.org/data/2.5/weather"
            
            if request.lat and request.lon:
                params = {
                    "lat": request.lat,
                    "lon": request.lon,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": request.units
                }
            else:
                params = {
                    "q": f"{request.city},{request.country}" if request.country else request.city,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": request.units
                }
            
            response = await client.get(current_url, params=params)
            response.raise_for_status()
            current_data = response.json()
            
            # Parse date range
            start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(request.end_date, "%Y-%m-%d")
            
            if (end_date - start_date).days > 365:
                raise ValueError("Maximum historical period is 365 days")
            
            # Generate simulated historical data based on current weather patterns
            historical_data = []
            current_temp = current_data["main"]["temp"]
            current_humidity = current_data["main"]["humidity"]
            current_pressure = current_data["main"]["pressure"]
            
            date_iter = start_date
            while date_iter <= end_date:
                # Add realistic variations to simulate historical data
                import random
                temp_variation = random.uniform(-5, 5)
                humidity_variation = random.uniform(-10, 10)
                pressure_variation = random.uniform(-5, 5)
                
                daily_data = HistoricalWeatherData(
                    date=date_iter.strftime("%Y-%m-%d"),
                    temperature={
                        "min": round(current_temp + temp_variation - 3, 1),
                        "max": round(current_temp + temp_variation + 3, 1),
                        "avg": round(current_temp + temp_variation, 1)
                    },
                    humidity=max(0, min(100, current_humidity + humidity_variation)),
                    pressure=round(current_pressure + pressure_variation, 1),
                    wind_speed=round(random.uniform(2, 15), 1),
                    description=current_data["weather"][0]["description"],
                    precipitation=round(random.uniform(0, 5), 1) if random.random() > 0.7 else 0.0
                )
                
                historical_data.append(daily_data)
                date_iter += timedelta(days=1)
            
            # Calculate statistics
            temperatures = [day.temperature["avg"] for day in historical_data]
            humidities = [day.humidity for day in historical_data]
            pressures = [day.pressure for day in historical_data]
            
            statistics = {
                "temperature": {
                    "average": round(sum(temperatures) / len(temperatures), 1),
                    "minimum": min(temperatures),
                    "maximum": max(temperatures),
                    "trend": "stable"  # Could be calculated based on actual data
                },
                "humidity": {
                    "average": round(sum(humidities) / len(humidities), 1),
                    "minimum": min(humidities),
                    "maximum": max(humidities)
                },
                "pressure": {
                    "average": round(sum(pressures) / len(pressures), 1),
                    "minimum": min(pressures),
                    "maximum": max(pressures)
                },
                "total_days": len(historical_data),
                "rainy_days": len([d for d in historical_data if d.precipitation > 0])
            }
            
            # AI-powered trend analysis
            ai_trends = {
                "weather_patterns": analyze_weather_patterns(historical_data),
                "seasonal_insights": analyze_seasonal_patterns(historical_data, start_date),
                "business_impact": analyze_historical_business_impact(historical_data),
                "climate_summary": generate_climate_summary(statistics)
            }
            
            return HistoricalResponse(
                location={
                    "city": current_data["name"],
                    "country": current_data["sys"]["country"],
                    "coordinates": {
                        "lat": current_data["coord"]["lat"],
                        "lon": current_data["coord"]["lon"]
                    }
                },
                period={
                    "start_date": request.start_date,
                    "end_date": request.end_date,
                    "days_count": len(historical_data)
                },
                historical_data=historical_data,
                statistics=statistics,
                ai_trends=ai_trends
            )
            
    except Exception as e:
        raise Exception(f"Historical weather data fetch failed: {str(e)}")

def analyze_weather_patterns(data: List[HistoricalWeatherData]) -> Dict[str, Any]:
    """Analyze weather patterns from historical data"""
    temp_changes = []
    for i in range(1, len(data)):
        temp_changes.append(data[i].temperature["avg"] - data[i-1].temperature["avg"])
    
    if not temp_changes:
        # Single day of data
        return {
            "volatility": "minimal",
            "dominant_conditions": data[0].description if data else "unknown",
            "temperature_stability": "stable"
        }
    
    return {
        "volatility": "high" if max(temp_changes) - min(temp_changes) > 10 else "moderate",
        "dominant_conditions": max(set([d.description for d in data]), key=[d.description for d in data].count),
        "temperature_stability": "stable" if max(temp_changes) - min(temp_changes) < 5 else "variable"
    }

def analyze_seasonal_patterns(data: List[HistoricalWeatherData], start_date: datetime) -> Dict[str, Any]:
    """Analyze seasonal patterns"""
    month = start_date.month
    season = "winter" if month in [12, 1, 2] else "spring" if month in [3, 4, 5] else "summer" if month in [6, 7, 8] else "autumn"
    
    avg_temp = sum([d.temperature["avg"] for d in data]) / len(data)
    
    return {
        "season": season,
        "typical_for_season": "yes" if (season == "summer" and avg_temp > 20) or (season == "winter" and avg_temp < 10) else "no",
        "seasonal_recommendation": f"This {season} period shows typical weather patterns for the region"
    }

def analyze_historical_business_impact(data: List[HistoricalWeatherData]) -> Dict[str, Any]:
    """Analyze business impact from historical weather"""
    rainy_days = len([d for d in data if d.precipitation > 0])
    hot_days = len([d for d in data if d.temperature["max"] > 30])
    cold_days = len([d for d in data if d.temperature["min"] < 5])
    
    return {
        "retail_impact": {
            "favorable_days": len(data) - rainy_days - hot_days - cold_days,
            "challenging_days": rainy_days + hot_days + cold_days,
            "impact_score": round((len(data) - rainy_days - hot_days - cold_days) / len(data) * 100, 1)
        },
        "agriculture_impact": {
            "growing_conditions": "favorable" if rainy_days > len(data) * 0.2 and hot_days < len(data) * 0.3 else "challenging",
            "irrigation_days_needed": max(0, len(data) - rainy_days - 5)
        },
        "events_impact": {
            "suitable_days": len(data) - rainy_days,
            "weather_cancellation_risk": round(rainy_days / len(data) * 100, 1)
        }
    }

def generate_climate_summary(statistics: Dict[str, Any]) -> str:
    """Generate AI-powered climate summary"""
    avg_temp = statistics["temperature"]["average"]
    avg_humidity = statistics["humidity"]["average"]
    rainy_days = statistics["rainy_days"]
    total_days = statistics["total_days"]
    
    climate_type = "tropical" if avg_temp > 25 and avg_humidity > 70 else \
                   "arid" if avg_temp > 20 and avg_humidity < 40 else \
                   "temperate" if 10 <= avg_temp <= 25 else \
                   "cold" if avg_temp < 10 else "moderate"
    
    rain_frequency = "frequent" if rainy_days > total_days * 0.4 else \
                     "moderate" if rainy_days > total_days * 0.2 else "infrequent"
    
    return f"The period shows {climate_type} climate conditions with {rain_frequency} precipitation patterns. " \
           f"Average temperature of {avg_temp}°C indicates favorable conditions for most outdoor activities."