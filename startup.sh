#!/bin/bash

# Ensure we're in the app root used by Azure App Service
cd /home/site/wwwroot || exit 1

# Make Python output unbuffered for clearer logs
export PYTHONUNBUFFERED=1

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
python -m pip install --no-cache-dir -r requirements.txt

# Run Streamlit on the App Service port/interface
python -m streamlit run app.py --server.port=8000 --server.address=0.0.0.0 --server.headless=true

