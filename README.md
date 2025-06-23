# Weather Intelligence API

A comprehensive weather API that provides current weather data, forecasts, and AI-powered business insights. Built for monetization on RapidAPI marketplace.

## 🌟 Features

- **Current Weather Data**: Real-time weather information with AI-enhanced insights
- **Weather Forecasts**: Multi-day forecasts with detailed predictions
- **Business Analytics**: AI-powered insights for retail, agriculture, events, and energy sectors
- **Smart Recommendations**: Activity suggestions based on weather conditions
- **Rate Limiting**: Built-in rate limiting for different subscription tiers
- **API Key Authentication**: Secure access with tiered pricing support

## 🚀 Quick Start

### Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your OpenWeatherMap API key
```

4. Run the server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## 📖 API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

### Authentication

All endpoints require an API key in the Authorization header:
```
Authorization: Bearer your_api_key_here
```

### Endpoints

#### 1. Current Weather
```
GET /weather/current?city=London&country=UK
```

Response includes:
- Current temperature, humidity, pressure
- Weather description and conditions
- Wind information
- AI comfort level assessment
- Activity recommendations
- Weather score (0-100)

#### 2. Weather Forecast
```
GET /weather/forecast?city=London&days=5
```

Multi-day forecast with:
- Temperature predictions
- Precipitation probability
- Weather conditions
- Wind data

#### 3. Weather Analytics
```
GET /weather/analytics?city=London
```

Business insights including:
- Retail impact predictions
- Agriculture conditions
- Event suitability analysis
- Energy demand forecasting
- Business recommendations

## 🏷️ Subscription Tiers

### Basic Tier
- 1,000 requests/day
- 10,000 requests/month  
- 100 requests/minute
- Access to all endpoints

### Premium Tier
- 10,000 requests/day
- 100,000 requests/month
- 500 requests/minute
- Priority support

### Enterprise Tier
- 100,000 requests/day
- 1,000,000 requests/month
- 1,000 requests/minute
- Custom analytics
- Dedicated support

## 💼 Business Use Cases

### Retail & E-commerce
- Optimize inventory based on weather forecasts
- Adjust marketing campaigns for weather conditions
- Predict foot traffic patterns

### Agriculture
- Monitor growing conditions
- Optimize irrigation schedules
- Assess pest risk levels

### Event Management
- Plan outdoor events with confidence
- Implement weather contingency plans
- Optimize venue selection

### Energy & Utilities
- Forecast energy demand
- Optimize grid management
- Plan maintenance schedules

## 🔧 Configuration

### Environment Variables

```env
OPENWEATHER_API_KEY=your_openweather_api_key
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
```

### API Key Management

Demo API key for testing: `demo_key_12345`

## 🧪 Testing

Run the test suite:
```bash
python -m pytest tests/ -v
```

## 📊 Monitoring & Analytics

The API includes built-in monitoring for:
- Request rates and quotas
- API key usage statistics
- Error tracking
- Performance metrics

## 💰 Monetization Ready

This API is designed for sale on RapidAPI marketplace with:
- Multiple subscription tiers
- Rate limiting per tier
- Usage tracking
- Comprehensive documentation
- Business-focused features

## 🔒 Security Features

- API key authentication
- Rate limiting
- Input validation
- Error handling
- CORS configuration

## 🌍 Supported Locations

- Any city worldwide
- Coordinates (latitude/longitude)
- Country-specific queries
- Multiple unit systems (metric, imperial, kelvin)

## 📈 Revenue Potential

Based on RapidAPI marketplace analysis:
- Weather APIs are consistently popular
- Business intelligence features command premium pricing
- Multiple revenue streams through tiered subscriptions
- Recurring monthly revenue model

## 🤝 Support

For API support and business inquiries, contact the development team.

---

Built with FastAPI, designed for scale and monetization on RapidAPI marketplace.