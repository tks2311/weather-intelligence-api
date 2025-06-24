# Weather Intelligence API

AI-powered weather data with business insights, webhooks, and advanced analytics.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENWEATHER_API_KEY=your_api_key_here

# Run the API
python main.py
```

API available at: `http://localhost:8000`  
Documentation: `http://localhost:8000/docs`

## 🔑 Authentication

All endpoints require API key authentication:
```
Authorization: Bearer your_api_key_here
```

Demo API key: `demo_key_12345`

## 📡 Endpoints

- `GET /weather/current` - Current weather with AI insights
- `GET /weather/forecast` - Multi-day weather forecasts  
- `POST /weather/historical` - Historical data with trends
- `GET /weather/analytics` - Business intelligence insights
- `POST /weather/batch` - Batch processing (up to 50 locations)
- `POST /webhooks` - Real-time weather alerts

## 🌟 Features

- **AI Business Insights** - Retail, agriculture, events, energy
- **Real-time Webhooks** - Custom weather condition alerts
- **Batch Processing** - Concurrent multi-location requests
- **Historical Analysis** - AI-powered trend analysis
- **Smart Caching** - 5x performance improvement
- **Enterprise Grade** - Professional documentation & monitoring

## 🏗️ Deployment

Deploy to Render using the included `render.yaml` configuration.

## 📊 Monitoring

- Cache stats: `GET /cache/stats`
- Health check: `GET /health`

Built with FastAPI for production-ready performance and scalability.