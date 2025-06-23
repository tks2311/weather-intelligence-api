from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import httpx
from .config import settings

class BatchLocationRequest(BaseModel):
    city: str
    country: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

class BatchWeatherRequest(BaseModel):
    locations: List[BatchLocationRequest]
    endpoints: List[str]  # ["current", "forecast", "analytics"]
    units: Optional[str] = "metric"
    forecast_days: Optional[int] = 5

class BatchWeatherResponse(BaseModel):
    results: List[Dict[str, Any]]
    summary: Dict[str, Any]
    processing_time_ms: float

async def fetch_weather_data(location: BatchLocationRequest, endpoint: str, units: str, forecast_days: int = 5) -> Dict[str, Any]:
    """Fetch weather data for a single location and endpoint"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if endpoint == "current":
                url = "http://api.openweathermap.org/data/2.5/weather"
            elif endpoint == "forecast":
                url = "http://api.openweathermap.org/data/2.5/forecast"
            else:
                return {"error": f"Unsupported endpoint: {endpoint}"}
            
            # Build parameters
            if location.lat and location.lon:
                params = {
                    "lat": location.lat,
                    "lon": location.lon,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": units
                }
            else:
                params = {
                    "q": f"{location.city},{location.country}" if location.country else location.city,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": units
                }
            
            if endpoint == "forecast":
                params["cnt"] = forecast_days * 8
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Transform data based on endpoint
            if endpoint == "current":
                return {
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
                        "description": data["weather"][0]["description"],
                        "icon": data["weather"][0]["icon"],
                        "wind": {
                            "speed": data["wind"]["speed"],
                            "direction": data["wind"].get("deg", 0)
                        }
                    },
                    "endpoint": endpoint
                }
            elif endpoint == "forecast":
                forecast_items = []
                for item in data["list"]:
                    forecast_items.append({
                        "datetime": item["dt_txt"],
                        "temperature": item["main"]["temp"],
                        "description": item["weather"][0]["description"],
                        "humidity": item["main"]["humidity"],
                        "wind_speed": item["wind"]["speed"]
                    })
                
                return {
                    "location": {
                        "city": data["city"]["name"],
                        "country": data["city"]["country"],
                        "coordinates": {
                            "lat": data["city"]["coord"]["lat"],
                            "lon": data["city"]["coord"]["lon"]
                        }
                    },
                    "forecast": forecast_items,
                    "endpoint": endpoint
                }
            
    except Exception as e:
        return {
            "error": str(e),
            "location": location.dict(),
            "endpoint": endpoint
        }

async def process_batch_request(batch_request: BatchWeatherRequest) -> BatchWeatherResponse:
    """Process multiple weather requests concurrently"""
    import time
    start_time = time.time()
    
    # Create tasks for all location-endpoint combinations
    tasks = []
    for location in batch_request.locations:
        for endpoint in batch_request.endpoints:
            task = fetch_weather_data(
                location, 
                endpoint, 
                batch_request.units,
                batch_request.forecast_days
            )
            tasks.append(task)
    
    # Execute all requests concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    processed_results = []
    error_count = 0
    success_count = 0
    
    for result in results:
        if isinstance(result, Exception):
            processed_results.append({"error": str(result)})
            error_count += 1
        elif "error" in result:
            processed_results.append(result)
            error_count += 1
        else:
            processed_results.append(result)
            success_count += 1
    
    processing_time = (time.time() - start_time) * 1000
    
    summary = {
        "total_requests": len(tasks),
        "successful": success_count,
        "failed": error_count,
        "locations_processed": len(batch_request.locations),
        "endpoints_requested": batch_request.endpoints,
        "processing_time_ms": round(processing_time, 2)
    }
    
    return BatchWeatherResponse(
        results=processed_results,
        summary=summary,
        processing_time_ms=round(processing_time, 2)
    )