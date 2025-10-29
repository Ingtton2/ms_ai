#!/bin/bash

# Azure App Service에서 Streamlit 앱 실행
streamlit run app.py --server.port=8000 --server.address=0.0.0.0 --server.headless=true

