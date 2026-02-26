import streamlit as st
import folium
import ee
import pandas as pd
import numpy as np
import joblib
import plotly.graph_objects as go
import os
import time
from streamlit_folium import st_folium

# Page config
st.set_page_config(
    page_title="Solar Farm Suitability Predictor",
    page_icon="☀️",
    layout="wide"
)

# Custom CSS for Premium UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    /* Global Dark Theme Overrides */
    [data-testid="stAppViewContainer"] {
        background-color: #0d0f14 !important;
        color: #f1f5f9;
    }
    [data-testid="stSidebar"] {
        background-color: #171923 !important;
        border-right: 1px solid #2d3748;
    }
    [data-testid="stHeader"] {
        background-color: transparent !important;
    }
    p, span, div {
        color: #e2e8f0;
    }
    h1, h2, h3, h4, h5 {
        color: #ffffff !important;
    }

    /* Elite Animations */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(30px) scale(0.98); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes pulseGlow {
        0% { box-shadow: 0 0 15px rgba(255, 140, 0, 0.4), inset 0 0 10px rgba(255,255,255,0.05); border-color: rgba(255,140,0,0.3); }
        50% { box-shadow: 0 0 35px rgba(255, 0, 128, 0.6), inset 0 0 20px rgba(255,255,255,0.1); border-color: rgba(255,0,128,0.6); }
        100% { box-shadow: 0 0 15px rgba(255, 140, 0, 0.4), inset 0 0 10px rgba(255,255,255,0.05); border-color: rgba(255,140,0,0.3); }
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header { 
        font-size: 3.5rem; 
        background: -webkit-linear-gradient(135deg, #00C9FF 0%, #92FE9D 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center; 
        font-weight: 800;
        margin-bottom: 0px;
        animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1);
        text-shadow: 0px 10px 30px rgba(0, 201, 255, 0.2);
    }
    .sub-header {
        text-align: center; 
        color: #94a3b8 !important; 
        font-size: 1.15rem; 
        margin-top: -10px; 
        margin-bottom: 30px;
        animation: fadeInUp 1s cubic-bezier(0.16, 1, 0.3, 1);
    }
    
    /* Result Box Glassmorphism */
    .result-box { 
        padding: 30px; 
        border-radius: 16px; 
        background: rgba(30, 33, 43, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.1);
        animation: pulseGlow 4s infinite alternate, fadeInUp 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        position: relative;
    }
    
    /* Glowing Tiers */
    .excellent { color: #00FF66 !important; font-weight: 800; font-size: 1.6rem; text-shadow: 0 0 15px rgba(0,255,102,0.6);}
    .good { color: #B4FF00 !important; font-weight: 800; font-size: 1.6rem; text-shadow: 0 0 15px rgba(180,255,0,0.4);}
    .moderate { color: #FFB300 !important; font-weight: 800; font-size: 1.6rem; text-shadow: 0 0 15px rgba(255,179,0,0.4);}
    .poor { color: #FF0055 !important; font-weight: 800; font-size: 1.6rem; text-shadow: 0 0 15px rgba(255,0,85,0.4);}
    
    /* Buttons */
    .stButton>button {
        background: rgba(255,255,255,0.05) !important;
        border-radius: 10px;
        font-weight: 600;
        color: #e2e8f0 !important;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        border: 1px solid rgba(255,255,255,0.1) !important;
    }
    .stButton>button:hover {
        transform: translateY(-4px) scale(1.03);
        box-shadow: 0 10px 25px rgba(0, 201, 255, 0.25) !important;
        border-color: #00C9FF !important;
        color: #00C9FF !important;
        background: rgba(0,201,255,0.05) !important;
    }
    
    /* Neon Metric Cards */
    [data-testid="stMetric"] {
        animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) backwards;
        background: rgba(20, 24, 33, 0.8) !important;
        backdrop-filter: blur(10px);
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.2) !important;
        border: 1px solid rgba(255,255,255,0.05);
        transition: all 0.4s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        border-color: rgba(0, 201, 255, 0.4);
        box-shadow: 0 12px 40px rgba(0, 201, 255, 0.15) !important;
    }
    [data-testid="stMetricValue"] {
        color: #00C9FF !important;
        font-weight: 800;
        text-shadow: 0 0 10px rgba(0,201,255,0.3);
    }
    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-weight: 600;
    }
    [data-testid="stMetric"]:nth-child(1) { animation-delay: 0.1s; }
    [data-testid="stMetric"]:nth-child(2) { animation-delay: 0.2s; }
    [data-testid="stMetric"]:nth-child(3) { animation-delay: 0.3s; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'lat' not in st.session_state:
    st.session_state.lat = 17.55
if 'lon' not in st.session_state:
    st.session_state.lon = 78.38
if 'run_prediction' not in st.session_state:
    st.session_state.run_prediction = False

# Load model
@st.cache_resource
def load_model():
    model_path = 'lgb_final_05.pkl'
    if not os.path.exists(model_path):
        return None
    return joblib.load(model_path)

# Initialize GEE
@st.cache_resource
def init_gee():
    try:
        # ── Streamlit Cloud: read credentials from secrets ──
        if "gee" in st.secrets:
            import json
            gee_cfg = st.secrets["gee"]
            creds = {
                "refresh_token": gee_cfg["refresh_token"],
                "redirect_uri":  gee_cfg.get("redirect_uri", "http://localhost:8085"),
                "scopes": [
                    "https://www.googleapis.com/auth/earthengine",
                    "https://www.googleapis.com/auth/cloud-platform",
                    "https://www.googleapis.com/auth/drive",
                    "https://www.googleapis.com/auth/devstorage.full_control",
                ],
            }
            # Write creds to the standard location earthengine-api reads on Linux
            home = os.path.expanduser("~")
            cred_dir = os.path.join(home, ".config", "earthengine")
            os.makedirs(cred_dir, exist_ok=True)
            cred_path = os.path.join(cred_dir, "credentials")
            with open(cred_path, "w") as f:
                json.dump(creds, f)
            ee.Initialize(project=gee_cfg.get("project_id", ""))
            return True, ""

        # ── Local dev: read project ID from gee_project.txt ──
        if os.path.exists("gee_project.txt"):
            with open("gee_project.txt", "r") as f:
                project_id = f.read().strip()
            if project_id:
                ee.Initialize(project=project_id)
                return True, ""

        # Fallback
        ee.Initialize()
        return True, ""
    except Exception as e:
        return False, str(e)


# Fetch GEE data for a point using reduceRegion for robust extraction
def fetch_gee_data(lat, lon, month):
    try:
        point = ee.Geometry.Point([lon, lat])
        
        # Solar irradiance from TerraClimate (srad is W/m^2 * 0.1)
        # Convert to kWh/m^2/day: W/m^2 * 24 / 1000
        solar = ee.ImageCollection("IDAHO_EPSCOR/TERRACLIMATE") \
            .select(['srad']) \
            .filter(ee.Filter.calendarRange(month, month, 'month')) \
            .mean()
        solar_data = solar.reduceRegion(ee.Reducer.mean(), point, 10000).getInfo()
        srad_w_m2 = (solar_data.get('srad') or 0) * 0.1
        solar_val = (srad_w_m2 * 24) / 1000 if srad_w_m2 else 5.5
        
        # Land cover
        lc = ee.Image("ESA/WorldCover/v200/2021")
        lc_data = lc.reduceRegion(ee.Reducer.mode(), point, 100).getInfo()
        lc_val = lc_data.get('Map')
        
        # Elevation & Terrain
        elev = ee.Image("USGS/SRTMGL1_003")
        terrain = ee.Algorithms.Terrain(elev)
        terrain_data = terrain.reduceRegion(ee.Reducer.mean(), point, 30).getInfo()
        elev_val = terrain_data.get('elevation')
        slope_val = terrain_data.get('slope')
        aspect_val = terrain_data.get('aspect')
        
        # Temperature (ERA5)
        temp = ee.ImageCollection("ECMWF/ERA5/MONTHLY") \
            .select(['mean_2m_air_temperature']) \
            .filter(ee.Filter.calendarRange(month, month, 'month')) \
            .mean()
        temp_data = temp.reduceRegion(ee.Reducer.mean(), point, 11132).getInfo()
        temp_val = temp_data.get('mean_2m_air_temperature')
        temp_c = temp_val - 273.15 if temp_val is not None else 28.0
        
        # NDVI from MODIS
        ndvi_img = ee.ImageCollection("MODIS/061/MOD13A2") \
            .select(['NDVI']).filter(ee.Filter.calendarRange(month, month, 'month')).mean()
        ndvi_data = ndvi_img.reduceRegion(ee.Reducer.mean(), point, 1000).getInfo().get('NDVI')
        ndvi = (ndvi_data * 0.0001) if ndvi_data else None
        
        return {
            'solar_irradiance': solar_val,
            'land_cover': lc_val,
            'elevation': elev_val,
            'slope': slope_val,
            'aspect': aspect_val,
            'temperature_c': temp_c,
            'ndvi': ndvi,
            'lat': lat,
            'lon': lon,
            'month': month
        }
    except Exception as e:
        print("GEE Fetch Error:", e)
        return {
            'solar_irradiance': 5.5, 'land_cover': 40, 'elevation': 200,
            'slope': 2.0, 'aspect': 180.0, 'temperature_c': 28.0, 'ndvi': 0.2,
            'lat': lat, 'lon': lon, 'month': month
        }

# Build feature vector for model
def build_features(data):
    # Base extracted variables
    solar_rad = data.get('solar_irradiance') or 5.5
    elev = data.get('elevation') or 200
    month = data.get('month', 6)
    
    # Derived topographic and solar features
    slope = data.get('slope')
    if slope is None: slope = 2.0
    aspect = data.get('aspect')
    if aspect is None: aspect = 180.0
    south_facing = 1 if (135 <= aspect <= 225) else 0
    
    # Derived seasons matching Indian subcontinent
    season_monsoon = 1 if month in [6, 7, 8, 9] else 0
    season_post_monsoon = 1 if month in [10, 11, 12] else 0
    season_summer = 1 if month in [3, 4, 5] else 0
    season_winter = 1 if month in [1, 2] else 0
    
    stations = [
        'station_Acme_(Biwadi)', 'station_Acme_(Hisar)', 'station_Acme_(Karnal)',
        'station_Acme_Chittorgarh_Energy_Pvt_Ltd.', 'station_Adani_Renewable_Energy_Four_Pvt_Ltd',
        'station_Arinsun_Solar_(Barsaitadesh)', 'station_Avaada_Solar', 'station_Avaada_Solarise',
        'station_Ayana', 'station_Azure', 'station_Azure_Power_Earth',
        'station_Azure_Power_Forty_Three_Private_Ltd', 'station_Azure_Power_India_Pvt_Ltd',
        'station_Azure_Power_Thirty_Four_Private_Ltd', 'station_Clean_Solar_Power_(Bhadla)_Pvt_Ldt',
        'station_Dadri_Solar', 'station_Fortum_Fin_Surya', 'station_Fortum_Solar', 'station_Kredl',
        'station_M/S_Adani_Solar_Energy_Jodhpur_Two_Ltd', 'station_Mahindra_Solar_(Badwar)',
        'station_Ntpc', 'station_Parampujya', 'station_Renew_Solar_Power_Pvt_Ltd',
        'station_Renew_Solar_Power_Pvt_Ltd._Bikaner', 'station_Renew_Tn2',
        'station_Sb_Energy_Four_Pvt_Ltd', 'station_Sbg_Energy', 'station_Singrauli_Solar',
        'station_Spring_Angitra', 'station_Tata_Power', 'station_Tata_Power_Renewable_Energy_Ltd',
        'station_Tata_Renewables', 'station_Unchahar_Solar', 'station_Yarrow'
    ]
    
    row = {
        'solar_radiation': solar_rad,
        'elevation': elev,
        'slope': slope,
        'aspect': aspect,
        'south_facing': south_facing,
        'slope_x_solar': slope * solar_rad,
        'aspect_sin': np.sin(np.radians(aspect)),
        'aspect_cos': np.cos(np.radians(aspect)),
        'month': month,
        'season_monsoon': season_monsoon,
        'season_post-monsoon': season_post_monsoon,
        'season_summer': season_summer,
        'season_winter': season_winter
    }
    
    for s in stations:
        row[s] = 0
        
    expected_cols = [
        'solar_radiation', 'elevation', 'slope', 'aspect', 'south_facing',
        'slope_x_solar', 'aspect_sin', 'aspect_cos', 'month', 'season_monsoon',
        'season_post-monsoon', 'season_summer', 'season_winter'
    ] + stations
    
    return pd.DataFrame([row], columns=expected_cols)

# Suitability label (CUF based)
def get_label(score):
    if score >= 28.0:
        return "🟢 EXCELLENT", "excellent", "linear-gradient(90deg, #00f2fe 0%, #4facfe 100%)"
    elif score >= 24.0:
        return "🟡 GOOD", "good", "linear-gradient(90deg, #a8ff78 0%, #78ffd6 100%)"
    elif score >= 20.0:
        return "🟠 MODERATE", "moderate", "linear-gradient(90deg, #f6d365 0%, #fda085 100%)"
    else:
        return "🔴 LOW", "poor", "linear-gradient(90deg, #ff0844 0%, #ffb199 100%)"

# Premium Animated HTML Progress Bar (Dark Theme)
def render_animated_bar(score, gradient):
    clamped_score = max(10, min(35, score))
    fill_percentage = ((clamped_score - 10) / 25) * 100
    
    # Generate a unique CSS animation name based on the score to prevent caching conflicts
    anim_name = f"fillBar_{str(score).replace('.', '_')}"
    
    return f"""
    <style>
        @keyframes {anim_name} {{
            0%   {{ width: 0%; }}
            100% {{ width: {fill_percentage}%; }}
        }}
        .bar-fill-{anim_name} {{
            animation: {anim_name} 1.5s cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }}
    </style>
    <div style="margin: 25px 0 10px 0;">
        <div style="display: flex; justify-content: space-between; font-weight: 600; color: #94a3b8; margin-bottom: 12px; padding: 0 5px;">
            <span>10% CUF</span>
            <span style="font-size: 1.3rem; font-weight: 800; color: #f1f5f9; text-shadow: 0 0 8px rgba(255,255,255,0.3);">Predicted: {score:.1f}%</span>
            <span>35% CUF</span>
        </div>
        <div style="width: 100%; background-color: rgba(0,0,0,0.5); border-radius: 20px; height: 28px; overflow: hidden; box-shadow: inset 0 3px 8px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.05);">
            <div class="bar-fill-{anim_name}" style="background: {gradient}; height: 100%; border-radius: 20px; box-shadow: 0 0 20px rgba(255,255,255,0.2) inset;"></div>
        </div>
    </div>
    """

# Main app
def main():
    st.markdown("<h1 class='main-header'>☀️ Solar Farm Suitability Predictor</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Powered by Google Earth Engine & LightGBM</p>", unsafe_allow_html=True)
    st.divider()

    # Load model and GEE
    model = load_model()
    gee_ok, gee_err = init_gee()

    # Status indicators
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        if model:
            st.success("✅ Model loaded")
        else:
            st.error("❌ Model not found (lgb_final_05.pkl)")
    with col_s2:
        if gee_ok:
            st.success("✅ GEE connected")
        else:
            st.warning(f"⚠️ GEE not authenticated{(': ' + gee_err[:80]) if gee_err else ''}")
    with col_s3:
        st.info("📅 Feb 24, 2026")


    st.divider()

    # Sidebar
    with st.sidebar:
        st.header("🎛️ Controls")
        lat = st.number_input("Latitude", value=st.session_state.lat, min_value=-90.0, max_value=90.0, format="%.4f", step=0.01)
        lon = st.number_input("Longitude", value=st.session_state.lon, min_value=-180.0, max_value=180.0, format="%.4f", step=0.01)
        month = st.slider("Month", 1, 12, 6, help="Month for seasonal analysis")
        month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        st.caption(f"Selected: **{month_names[month]}**")

        st.divider()
        use_gee = st.checkbox("Fetch live GEE data", value=gee_ok, disabled=not gee_ok,
                              help="Fetch real satellite data. Requires GEE authentication.")
        st.divider()

        if st.button("🔍 Predict Suitability", type="primary", use_container_width=True):
            st.session_state.lat = lat
            st.session_state.lon = lon
            st.session_state.month = month
            st.session_state.use_gee = use_gee
            st.session_state.run_prediction = True

        st.divider()
        st.markdown("🏆 **Top Suitable Places in India 2026**")
        
        major_states = {
            "Bhadla, Rajasthan (Est. 34% CUF)": (27.53, 71.91),
            "Jodhpur, Rajasthan (Est. 33% CUF)": (26.23, 73.02),
            "Charanka, Gujarat (Est. 31% CUF)": (23.90, 71.01),
            "Kutch, Gujarat (Est. 32% CUF)": (23.73, 69.85),
            "Pavagada, Karnataka (Est. 29% CUF)": (14.28, 77.27),
            "Koppal, Karnataka (Est. 28% CUF)": (15.35, 76.15),
            "Kamuthi, Tamil Nadu (Est. 28% CUF)": (9.34, 78.39),
            "Tirunelveli, Tamil Nadu (Est. 29% CUF)": (8.71, 77.75),
            "Rewa, Madhya Pradesh (Est. 30% CUF)": (24.48, 81.56),
            "Neemuch, Madhya Pradesh (Est. 29% CUF)": (24.46, 74.87)
        }
        
        tg_places = {
            "Ramagundam Floating Solar (Est. 27% CUF)": (18.76, 79.48),
            "Hyderabad Pharma City (Est. 26% CUF)": (17.06, 78.60),
            "Mahabubnagar (Est. 28% CUF)": (16.74, 77.98),
            "Nalgonda (Est. 27% CUF)": (17.05, 79.26),
            "Khammam (Est. 26% CUF)": (17.24, 80.14),
            "Warangal (Est. 26% CUF)": (17.96, 79.59),
            "Nizamabad (Est. 28% CUF)": (18.67, 78.09),
            "Karimnagar (Est. 27% CUF)": (18.43, 79.12),
            "Adilabad (Est. 29% CUF)": (19.67, 78.53),
            "Medak (Est. 27% CUF)": (18.04, 78.26)
        }
        
        ap_places = {
            "Kurnool Ultra Mega (Est. 31% CUF)": (15.68, 78.27),
            "Anantapur N.P. Kunta (Est. 30% CUF)": (14.05, 78.30),
            "Kadapa (Est. 29% CUF)": (14.46, 78.82),
            "Tadipatri (Est. 30% CUF)": (14.91, 78.01),
            "Tirupati (Est. 27% CUF)": (13.62, 79.41),
            "Nellore (Est. 26% CUF)": (14.44, 79.98),
            "Prakasam (Est. 28% CUF)": (15.50, 79.96),
            "Guntur (Est. 26% CUF)": (16.30, 80.43),
            "Krishna (Est. 25% CUF)": (16.18, 81.13),
            "Visakhapatnam (Est. 24% CUF)": (17.68, 83.21)
        }
        
        def render_location_buttons(loc_dict):
            for name, (qlat, qlon) in loc_dict.items():
                if st.button(name, use_container_width=True, key=name):
                    st.session_state.lat = qlat
                    st.session_state.lon = qlon
                    st.rerun()

        with st.expander("🌟 Major States (2 each)"):
            render_location_buttons(major_states)
            
        with st.expander("📍 Telangana (10 places)"):
            render_location_buttons(tg_places)
            
        with st.expander("📍 Andhra Pradesh (10 places)"):
            render_location_buttons(ap_places)

    # Map + results layout
    col_map, col_result = st.columns([3, 2])

    with col_map:
        st.subheader("🗺️ Location Map")
        st.caption("🖱️ **Click anywhere on the map** to select coordinates!")
        m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=9)
        folium.Marker(
            location=[st.session_state.lat, st.session_state.lon],
            popup=f"{st.session_state.lat:.4f}°N, {st.session_state.lon:.4f}°E"
        ).add_to(m)
        
        # Render map using st_folium to capture click events
        map_data = st_folium(m, width=650, height=450, key="interactive_map")
        
        # Update coordinates on click
        if map_data and map_data.get('last_clicked'):
            clicked = map_data['last_clicked']
            if clicked['lat'] != st.session_state.lat or clicked['lng'] != st.session_state.lon:
                st.session_state.lat = clicked['lat']
                st.session_state.lon = clicked['lng']
                st.rerun()

    with col_result:
        st.subheader("📊 Analysis Results")

        if st.session_state.run_prediction:
            st.session_state.run_prediction = False

            if not model:
                st.error("Model file `lgb_final_05.pkl` not found in the app directory.")
            else:
                with st.spinner("Fetching data & running prediction..."):
                    # Fetch GEE data or use dummy
                    if st.session_state.get('use_gee') and gee_ok:
                        data = fetch_gee_data(
                            st.session_state.lat,
                            st.session_state.lon,
                            st.session_state.get('month', 6)
                        )
                    else:
                        # Fallback: approximate values without GEE
                        data = {
                            'lat': st.session_state.lat,
                            'lon': st.session_state.lon,
                            'month': st.session_state.get('month', 6),
                            'solar_irradiance': 5.5,
                            'elevation': 200,
                            'temperature_c': 28,
                            'land_cover': 40,
                        }
                        if not st.session_state.get('use_gee'):
                            st.caption("ℹ️ Using estimated values (GEE not used).")

                    features = build_features(data)

                    try:
                        if hasattr(model, 'booster_'):
                            score = float(model.booster_.predict(features.values)[0])
                        elif hasattr(model, '_Booster'):
                            score = float(model._Booster.predict(features.values)[0])
                        else:
                            score = float(model.predict(features)[0])
                        # The raw output is CUF percentage, no clamping needed.
                    except Exception as e:
                        st.error(f"Prediction error: {e}")
                        return

                label, css_class, gradient = get_label(score)
                bar_html = render_animated_bar(score, gradient)
                
                st.markdown(f"<div class='result-box'>"
                            f"<h3 style='margin-bottom: 5px; color: #444;'>Investment Verdict:</h3>"
                            f"<div class='{css_class}' style='margin-bottom: 20px;'>{label}</div>"
                            f"{bar_html}"
                            f"</div>", unsafe_allow_html=True)

                st.divider()
                st.markdown("<h4 style='text-align:center;'>📡 Live Satellite Data (GEE)</h4>", unsafe_allow_html=True)
                
                # Render beautifully in pure Streamlit metric cards
                m1, m2, m3 = st.columns(3)
                m1.metric("☀️ Solar Irradiance", f"{data.get('solar_irradiance', 0):.2f}", "kWh/m²/day", delta_color="off")
                m2.metric("⛰️ Elevation", f"{data.get('elevation', 0):.0f}", "meters", delta_color="off")
                m3.metric("🌡️ Temperature", f"{data.get('temperature_c', 0):.1f}", "°C", delta_color="off")
                
                st.write("") # Spacer
                
                m4, m5, m6 = st.columns(3)
                m4.metric("🌿 NDVI (Vegetation)", f"{data.get('ndvi', 0):.2f}", "Index", delta_color="off")
                m5.metric("📐 Terrain Slope", f"{data.get('slope', 0):.1f}", "°", delta_color="off")
                m6.metric("🧭 Coordinates", f"{data.get('lat', 0):.2f}°", f"{data.get('lon', 0):.2f}°", delta_color="off")

        else:
            st.info("👈 Select a location in the Sidebar or Map, then click **Predict Suitability**.")
            st.markdown("""
**How it works:**
1. Select a location on the map (or enter coordinates)
2. Choose a month for seasonal analysis
3. Optionally enable live GEE data fetching
4. Click **Predict** to run the LightGBM model

**Data sources:**
- 🛰️ NASA POWER (Solar irradiance)
- 🏔️ SRTM (Elevation)
- 🌡️ ERA5 (Temperature)
- 🌍 ESA WorldCover (Land use)
""")

if __name__ == "__main__":
    main()
