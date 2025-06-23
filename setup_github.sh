#!/bin/bash

echo "🚀 GitHub Repository Setup Script"
echo "================================="
echo ""

# Check if we're in the right directory
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: Please run this script from the APIBuild directory"
    exit 1
fi

echo "✅ Project directory confirmed"
echo ""

# Get GitHub username
echo "📝 Enter your GitHub username:"
read -p "Username: " GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo "❌ Error: GitHub username is required"
    exit 1
fi

echo ""
echo "🔗 Setting up remote repository..."

# Add remote origin
REPO_URL="https://github.com/$GITHUB_USERNAME/weather-intelligence-api.git"
git remote add origin $REPO_URL

echo "✅ Remote origin set to: $REPO_URL"
echo ""

echo "📤 Ready to push to GitHub!"
echo ""
echo "Next steps:"
echo "1. Go to GitHub.com and create a new repository named: weather-intelligence-api"
echo "2. Make it PUBLIC (required for free hosting)"
echo "3. Don't initialize with README (we already have one)"
echo "4. Then run: git push -u origin main"
echo ""
echo "🌐 Your repository will be at: https://github.com/$GITHUB_USERNAME/weather-intelligence-api"