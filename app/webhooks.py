from fastapi import HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
import asyncio
import httpx
import json
from datetime import datetime
import uuid

class WebhookCondition(BaseModel):
    field: str  # "temperature", "humidity", "wind_speed", "description"
    operator: str  # ">", "<", ">=", "<=", "==", "contains"
    value: float | str

class WebhookConfig(BaseModel):
    id: Optional[str] = None
    name: str
    callback_url: HttpUrl
    city: str
    country: Optional[str] = None
    conditions: List[WebhookCondition]
    is_active: bool = True
    created_at: Optional[datetime] = None

class WebhookPayload(BaseModel):
    webhook_id: str
    webhook_name: str
    triggered_at: datetime
    city: str
    country: str
    condition_met: WebhookCondition
    current_weather: Dict[str, Any]
    ai_insights: Dict[str, Any]

# In-memory storage (in production, use Redis or database)
WEBHOOKS_DB: Dict[str, WebhookConfig] = {}

def create_webhook(webhook: WebhookConfig, api_key: str) -> str:
    """Create a new webhook subscription"""
    webhook_id = str(uuid.uuid4())
    webhook.id = webhook_id
    webhook.created_at = datetime.utcnow()
    
    # Store with API key association
    WEBHOOKS_DB[f"{api_key}:{webhook_id}"] = webhook
    
    return webhook_id

def get_webhooks(api_key: str) -> List[WebhookConfig]:
    """Get all webhooks for an API key"""
    return [webhook for key, webhook in WEBHOOKS_DB.items() if key.startswith(f"{api_key}:")]

def delete_webhook(webhook_id: str, api_key: str) -> bool:
    """Delete a webhook"""
    key = f"{api_key}:{webhook_id}"
    if key in WEBHOOKS_DB:
        del WEBHOOKS_DB[key]
        return True
    return False

def evaluate_condition(condition: WebhookCondition, weather_data: Dict[str, Any]) -> bool:
    """Evaluate if a condition is met"""
    field_value = None
    
    # Extract field value from weather data
    if condition.field == "temperature":
        field_value = weather_data["current"]["temperature"]
    elif condition.field == "humidity":
        field_value = weather_data["current"]["humidity"]
    elif condition.field == "wind_speed":
        field_value = weather_data["current"]["wind"]["speed"]
    elif condition.field == "description":
        field_value = weather_data["current"]["description"].lower()
    elif condition.field == "weather_score":
        field_value = weather_data["ai_insights"]["weather_score"]
    else:
        return False
    
    # Evaluate condition
    if condition.operator == ">":
        return float(field_value) > float(condition.value)
    elif condition.operator == "<":
        return float(field_value) < float(condition.value)
    elif condition.operator == ">=":
        return float(field_value) >= float(condition.value)
    elif condition.operator == "<=":
        return float(field_value) <= float(condition.value)
    elif condition.operator == "==":
        return str(field_value) == str(condition.value)
    elif condition.operator == "contains":
        return str(condition.value).lower() in str(field_value).lower()
    
    return False

async def send_webhook(webhook: WebhookConfig, payload: WebhookPayload) -> bool:
    """Send webhook notification"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                str(webhook.callback_url),
                json=payload.dict(),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Weather-Intelligence-API/1.0",
                    "X-Webhook-ID": webhook.id
                }
            )
            return response.status_code == 200
    except Exception as e:
        print(f"Webhook delivery failed: {e}")
        return False

async def check_and_trigger_webhooks(weather_data: Dict[str, Any], api_key: str):
    """Check all webhooks for the city and trigger if conditions are met"""
    city = weather_data["location"]["city"].lower()
    
    # Find matching webhooks for this API key and city
    matching_webhooks = [
        webhook for key, webhook in WEBHOOKS_DB.items() 
        if key.startswith(f"{api_key}:") and 
        webhook.is_active and 
        webhook.city.lower() == city
    ]
    
    for webhook in matching_webhooks:
        for condition in webhook.conditions:
            if evaluate_condition(condition, weather_data):
                # Create payload
                payload = WebhookPayload(
                    webhook_id=webhook.id,
                    webhook_name=webhook.name,
                    triggered_at=datetime.utcnow(),
                    city=weather_data["location"]["city"],
                    country=weather_data["location"]["country"],
                    condition_met=condition,
                    current_weather=weather_data["current"],
                    ai_insights=weather_data["ai_insights"]
                )
                
                # Send webhook asynchronously
                asyncio.create_task(send_webhook(webhook, payload))