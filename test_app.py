import streamlit as st
import os
import joblib

st.set_page_config(page_title="Setup Test", page_icon="✅", layout="centered")
st.title("✅ Solar Suitability App — Setup Test")
st.divider()

# Test 1: Streamlit
st.success("✅ Streamlit is working!")

# Test 2: Model file
model_path = "lgb_final_05.pkl"
if os.path.exists(model_path):
    size_mb = os.path.getsize(model_path) / 1e6
    st.success(f"✅ Model file found! ({size_mb:.1f} MB)")
    try:
        model = joblib.load(model_path)
        st.success(f"✅ Model loaded successfully — type: `{type(model).__name__}`")
    except Exception as e:
        st.error(f"❌ Could not load model: {e}")
else:
    st.error(f"❌ Model file `{model_path}` NOT found. Place it in: `{os.getcwd()}`")

# Test 3: Imports
st.divider()
st.subheader("📦 Package Import Tests")
packages = {
    "pandas": "import pandas",
    "numpy": "import numpy",
    "plotly": "import plotly",
    "joblib": "import joblib",
    "PIL (Pillow)": "from PIL import Image",
    "geemap": "import geemap",
    "earthengine-api (ee)": "import ee",
}
for name, stmt in packages.items():
    try:
        exec(stmt)
        st.success(f"✅ {name}")
    except ImportError as e:
        st.error(f"❌ {name}: {e}")

# Test 4: GEE Auth
st.divider()
st.subheader("🌍 Google Earth Engine")
try:
    import ee
    
    st.markdown("**Earth Engine requires a Cloud Project ID to initialize.**")
    
    # Try loading saved project
    saved_project = ""
    if os.path.exists("gee_project.txt"):
        with open("gee_project.txt", "r") as f:
            saved_project = f.read().strip()
            
    project_id = st.text_input("Google Cloud Project ID:", value=saved_project,
                               help="e.g. ee-yourusername, or a Google Cloud Project you selected during auth")
                               
    if project_id:
        try:
            ee.Initialize(project=project_id)
            with open("gee_project.txt", "w") as f:
                f.write(project_id)
            st.success(f"✅ GEE authenticated and initialized using project: `{project_id}`")
        except Exception as e:
            st.warning(f"⚠️ GEE failing to initialize with project '{project_id}'.\n\nRun in terminal:\n```\nearthengine authenticate\n```\nError: {e}")
    else:
        st.info("ℹ️ Please enter your Google Cloud Project ID above to initialize Earth Engine.")
except ImportError:
    st.error("❌ earthengine-api not installed")

st.divider()
st.info("If all checks pass, run: `streamlit run app.py`")

