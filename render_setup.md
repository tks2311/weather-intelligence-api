# 🌐 Render Deployment - Step by Step

## Quick Deploy (2 minutes)

### 1. Create Render Account
- Go to: https://render.com
- Click "Get Started for Free"
- Sign up with GitHub (easiest option)

### 2. Create Web Service
- Click "New +" → "Web Service"
- Click "Connect" next to your `weather-intelligence-api` repository
- Render will auto-detect the `render.yaml` file

### 3. Configure Service
**Auto-filled from render.yaml:**
- Name: `weather-intelligence-api`
- Environment: `Python`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 4. Add Environment Variables
In the "Environment" section:
```
OPENWEATHER_API_KEY = your_api_key_from_step_1
SECRET_KEY = auto-generated-by-render
```

### 5. Deploy
- Click "Create Web Service"
- Wait 2-3 minutes for deployment
- Your API will be live at: `https://weather-intelligence-api-xxxx.onrender.com`

## ✅ Test Your Deployment

Once deployed, test these URLs:
```
https://your-app.onrender.com/
https://your-app.onrender.com/docs
```

With demo API key:
```
curl -H "Authorization: Bearer demo_key_12345" \
     "https://your-app.onrender.com/weather/current?city=London"
```

## 🚨 Important Notes

- **Free Tier**: Perfect for starting out
- **Cold Start**: May take 30 seconds to wake up if inactive
- **Custom Domain**: Available on paid plans
- **SSL**: Automatically included

## 💡 Pro Tips

1. **Keep it warm**: Set up a simple uptime monitor
2. **Monitor logs**: Use Render's log viewer for debugging
3. **Environment vars**: Never commit API keys to Git
4. **Scaling**: Easy to upgrade to paid plans later

Your API will be production-ready and accessible worldwide!