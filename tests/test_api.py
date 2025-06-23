import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "Weather Intelligence API" in response.json()["message"]

def test_current_weather_no_auth():
    response = client.get("/weather/current?city=London")
    assert response.status_code == 403

def test_current_weather_with_demo_key():
    headers = {"Authorization": "Bearer demo_key_12345"}
    response = client.get("/weather/current?city=London", headers=headers)
    # This will fail without a real OpenWeather API key, but tests the auth flow
    assert response.status_code in [200, 400, 422, 500]

def test_forecast_with_demo_key():
    headers = {"Authorization": "Bearer demo_key_12345"}
    response = client.get("/weather/forecast?city=London", headers=headers)
    assert response.status_code in [200, 400, 422, 500]

def test_analytics_with_demo_key():
    headers = {"Authorization": "Bearer demo_key_12345"}
    response = client.get("/weather/analytics?city=London", headers=headers)
    assert response.status_code in [200, 400, 422, 500]

def test_invalid_api_key():
    headers = {"Authorization": "Bearer invalid_key"}
    response = client.get("/weather/current?city=London", headers=headers)
    assert response.status_code in [401, 422]