from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class WeatherQuery(BaseModel):
    city: Optional[str] = Field(None, description="City name")
    country: Optional[str] = Field(None, description="Country code (ISO 3166)")
    lat: Optional[float] = Field(None, description="Latitude")
    lon: Optional[float] = Field(None, description="Longitude")
    units: Optional[str] = Field("metric", description="Units: metric, imperial, kelvin")

class HistoricalWeatherQuery(WeatherQuery):
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")

class Location(BaseModel):
    city: str
    country: str
    coordinates: Dict[str, float]

class CurrentWeather(BaseModel):
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    visibility: float
    uv_index: float
    description: str
    icon: str
    wind: Dict[str, float]

class AIInsights(BaseModel):
    comfort_level: str
    activity_recommendations: List[str]
    weather_score: int

class WeatherResponse(BaseModel):
    location: Location
    current: CurrentWeather
    ai_insights: AIInsights
    timestamp: str
    units: str

class BusinessInsights(BaseModel):
    retail_impact: Dict[str, Any]
    agriculture_conditions: Dict[str, Any]
    outdoor_events_suitability: Dict[str, Any]
    energy_demand_forecast: Dict[str, Any]

class Trends(BaseModel):
    temperature_trend: str
    humidity_trend: str
    pressure_trend: str

class WeatherAnalyticsResponse(BaseModel):
    location: Location
    analysis_period: str
    business_insights: BusinessInsights
    trends: Trends
    recommendations: List[str]
    timestamp: str

class APIKeyCreate(BaseModel):
    name: str = Field(..., description="API key name/description")
    tier: str = Field("basic", description="API tier: basic, premium, enterprise")

class APIKeyResponse(BaseModel):
    key: str
    name: str
    tier: str
    created_at: datetime
    is_active: bool