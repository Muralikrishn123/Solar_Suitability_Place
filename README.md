# Solar Farm Suitability Predictor ☀️

A high-performance Streamlit application that uses **Google Earth Engine (GEE)** live satellite data and a **LightGBM** machine learning model to predict the Capacity Utilization Factor (CUF) and investment suitability of solar farm locations.

## Features
- **Interactive UI:** A highly polished, Dark Theme Cyberpunk interface with Glassmorphism and Neon accents.
- **Live Satellite Data:** Integrates with Google Earth Engine to fetch real-time Solar Irradiance, Elevation, Temperature, and NDVI Vegetation index for any coordinate.
- **Machine Learning Engine:** Uses a LightGBM predictor (included in `lgb_final_05.pkl`) trained on multiple solar parks to generate highly accurate CUF percentile predictions.
- **Top Locations Tracker:** Pre-loaded with Top Suitable Locations in India (Rajasthan, Gujarat, Telangana, Andhra Pradesh, etc.).

## Installation
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Authenticate with Google Earth Engine:
   ```bash
   earthengine authenticate
   ```
4. Run the Streamlit Application:
   ```bash
   streamlit run app.py
   ```
"# Solar_Suitability" 
"# Solar_Suitability" 
