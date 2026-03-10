import ee
import pandas as pd
import numpy as np
import joblib
import os
import time
from datetime import datetime

# Initialize GEE
def init_gee():
    if os.path.exists("gee_project.txt"):
        with open("gee_project.txt", "r") as f:
            project_id = f.read().strip()
        ee.Initialize(project=project_id)
    else:
        ee.Initialize()

def fetch_batch_gee_data(coords_df, month=6):
    print(f"Batch processing {len(coords_df)} locations for month {month}...")
    
    # Create FeatureCollection from points
    features = []
    for i, row in coords_df.iterrows():
        point = ee.Feature(ee.Geometry.Point([row['longitude'], row['latitude']]), {
            'name': row['name'],
            'original_index': i
        })
        features.append(point)
    
    # Process in chunks to avoid GEE limits
    fc = ee.FeatureCollection(features)
    
    # Environmental Layers
    solar_coll = ee.ImageCollection("IDAHO_EPSCOR/TERRACLIMATE").select(['srad']).filter(ee.Filter.calendarRange(month, month, 'month')).mean()
    elev = ee.Image("USGS/SRTMGL1_003")
    terrain = ee.Algorithms.Terrain(elev)
    temp_coll = ee.ImageCollection("ECMWF/ERA5/MONTHLY").select(['mean_2m_air_temperature']).filter(ee.Filter.calendarRange(month, month, 'month')).mean()
    
    combined_img = solar_coll.addBands(terrain).addBands(temp_coll)
    
    # reduceRegions is much faster than point-by-point
    sampled_fc = combined_img.reduceRegions(
        collection=fc,
        reducer=ee.Reducer.mean(),
        scale=1000 
    )
    
    results = sampled_fc.getInfo()
    
    data = []
    for f in results['features']:
        props = f['properties']
        srad_w_m2 = (props.get('srad') or 0) * 0.1
        solar_val = (srad_w_m2 * 24) / 1000 if srad_w_m2 else 5.5
        
        temp_val = props.get('mean_2m_air_temperature')
        temp_c = temp_val - 273.15 if temp_val is not None else 28.0
        
        data.append({
            'name': props.get('name'),
            'solar_radiation': solar_val,
            'elevation': props.get('elevation') or 200,
            'slope': props.get('slope') or 2.0,
            'aspect': props.get('aspect') or 180.0,
            'temperature_c': temp_c,
            'original_index': props.get('original_index')
        })
    
    return pd.DataFrame(data)

def build_feature_vector(batch_data, month=6):
    df = batch_data.copy()
    df['south_facing'] = df['aspect'].apply(lambda x: 1 if (135 <= x <= 225) else 0)
    df['slope_x_solar'] = df['slope'] * df['solar_radiation']
    df['aspect_sin'] = np.sin(np.radians(df['aspect']))
    df['aspect_cos'] = np.cos(np.radians(df['aspect']))
    df['month'] = month
    
    df['season_monsoon'] = 1 if month in [6, 7, 8, 9] else 0
    df['season_post-monsoon'] = 1 if month in [10, 11, 12] else 0
    df['season_summer'] = 1 if month in [3, 4, 5] else 0
    df['season_winter'] = 1 if month in [1, 2] else 0
    
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
    for s in stations: df[s] = 0
        
    expected_cols = [
        'solar_radiation', 'elevation', 'slope', 'aspect', 'south_facing',
        'slope_x_solar', 'aspect_sin', 'aspect_cos', 'month', 'season_monsoon',
        'season_post-monsoon', 'season_summer', 'season_winter'
    ] + stations
    
    return df[expected_cols]

def main():
    init_gee()
    model_path = 'lgb_final_05.pkl'
    if not os.path.exists(model_path):
        print(f"Error: {model_path} not found.")
        return
    model = joblib.load(model_path)
    
    coords_path = "telugu_villages_coords.csv"
    if not os.path.exists(coords_path):
        print(f"Error: {coords_path} not found.")
        return
    coords = pd.read_csv(coords_path)
    
    # Process ALL villages
    limit = len(coords)
    chunk_size = 500
    coords_subset = coords.head(limit)
    
    print(f"Processing FULL dataset: {len(coords_subset)} villages...")
    all_final_results = []
    
    for start in range(0, len(coords_subset), chunk_size):
        end = min(start + chunk_size, len(coords_subset))
        print(f"\n--- Progress: {start}/{len(coords_subset)} villages ---")
        chunk = coords_subset.iloc[start:end]
        
        batch_df = fetch_batch_gee_data(chunk)
        features = build_feature_vector(batch_df)
        
        if hasattr(model, 'predict'):
            scores = model.predict(features)
        else:
            scores = model.booster_.predict(features.values)
            
        batch_df['cuf_prediction'] = scores
        all_final_results.append(batch_df)
        
    final_df = pd.concat(all_final_results)
    
    def get_verdict(score):
        if score >= 28.0: return "EXCELLENT"
        elif score >= 24.0: return "GOOD"
        elif score >= 20.0: return "MODERATE"
        else: return "LOW"
    
    final_df['verdict'] = final_df['cuf_prediction'].apply(get_verdict)
    
    # Save to Excel with timestamp to avoid permission issues
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_name = f"village_suitability_report_{timestamp}.xlsx"
    final_df.to_excel(report_name, index=False)
    print(f"Report generated: {report_name}")
    
    # Also attempt to update the main one if possible
    try:
        final_df.to_excel("village_suitability_report_full.xlsx", index=False)
        print("Updated village_suitability_report_full.xlsx")
    except:
        pass

if __name__ == "__main__":
    main()
