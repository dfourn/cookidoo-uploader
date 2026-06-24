#!/bin/bash

# Script to upload Mushroom Risotto recipe to Cookidoo using cookiput

echo "Mushroom Risotto Recipe Upload to Cookidoo"
echo "============================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3."
    exit 1
fi

# Check if requests library is installed
if ! python3 -c "import requests" &> /dev/null; then
    echo "Installing required Python package: requests"
    pip3 install requests
fi

# Check if JWT token is set
if [ -z "$COOKIDOO_JWT" ]; then
    echo "Error: COOKIDOO_JWT environment variable is not set."
    echo ""
    echo "To get your JWT token:"
    echo "1. Log in to Cookidoo (https://www.cookidoo.de) in your browser"
    echo "2. Open Developer Tools (F12)"
    echo "3. Go to Application tab -> Cookies -> find '_oauth2_proxy' cookie"
    echo "4. Copy the value (starts with 'ey...')"
    echo "5. Set the environment variable:"
    echo "   export COOKIDOO_JWT='your_jwt_token_here'"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Run the Python script
echo "Uploading Mushroom Risotto recipe..."
python3 /Users/dan/recipes/cookiput_mushroom_risotto.py

echo ""
echo "Upload completed."