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

def fetch_precision_gee_data(coords_df):
    """
    Fetches terrain at 30m and climate at native resolutions (1km/10km).
    """
    features = []
    for i, row in coords_df.iterrows():
        point = ee.Feature(ee.Geometry.Point([row['longitude'], row['latitude']]), {
            'name': row['name'],
            'a1': str(row['admin1_code']),
            'a2': str(row['admin2_code']),
            'a3': str(row['admin3_code']),
            'original_index': i
        })
        features.append(point)
    
    fc = ee.FeatureCollection(features)
    
    # 1. Terrain (30m)
    elev = ee.Image("USGS/SRTMGL1_003")
    terrain = ee.Algorithms.Terrain(elev).select(['elevation', 'slope', 'aspect'])
    
    # 2. Climate Layers (Multi-band)
    climate_img = ee.Image()
    for m in range(1, 13):
        # Solar (1km)
        srad = ee.ImageCollection("IDAHO_EPSCOR/TERRACLIMATE").select(['srad']) \
               .filter(ee.Filter.calendarRange(m, m, 'month')).mean() \
               .rename(f'srad_{m}')
        # Temp (10km)
        temp = ee.ImageCollection("ECMWF/ERA5/MONTHLY").select(['mean_2m_air_temperature']) \
               .filter(ee.Filter.calendarRange(m, m, 'month')).mean() \
               .rename(f'temp_{m}')
        climate_img = climate_img.addBands(srad).addBands(temp)
    
    # Sample Terrain at 30m
    terrain_fc = terrain.reduceRegions(collection=fc, reducer=ee.Reducer.mean(), scale=30)
    
    # Sample Climate at 1000m
    climate_fc = climate_img.reduceRegions(collection=fc, reducer=ee.Reducer.mean(), scale=1000)
    
    # Combine results locally (getInfo is costly but necessary for batch processing)
    t_results = terrain_fc.getInfo()['features']
    c_results = climate_fc.getInfo()['features']
    
    rows = []
    for tf, cf in zip(t_results, c_results):
        t_props = tf['properties']
        c_props = cf['properties']
        
        static_data = {
            'name': t_props.get('name'),
            'elevation': t_props.get('elevation') or 200,
            'slope': t_props.get('slope') or 2.0,
            'aspect': t_props.get('aspect') or 180.0,
            'a1': t_props.get('a1'),
            'a2': t_props.get('a2'),
            'a3': t_props.get('a3')
        }
        
        for m in range(1, 13):
            srad_raw = c_props.get(f'srad_{m}') or 0
            srad_w_m2 = srad_raw * 0.1
            solar_val = (srad_w_m2 * 24) / 1000 if srad_w_m2 else 5.5
            
            temp_raw = c_props.get(f'temp_{m}')
            temp_c = temp_raw - 273.15 if temp_raw is not None else 28.0
            
            month_row = static_data.copy()
            month_row.update({
                'month': m,
                'solar_radiation': solar_val,
                'temperature_c': temp_c
            })
            rows.append(month_row)
            
    return pd.DataFrame(rows)

def build_feature_vector(batch_df):
    df = batch_df.copy()
    df['south_facing'] = df['aspect'].apply(lambda x: 1 if (135 <= x <= 225) else 0)
    df['slope_x_solar'] = df['slope'] * df['solar_radiation']
    df['aspect_sin'] = np.sin(np.radians(df['aspect']))
    df['aspect_cos'] = np.cos(np.radians(df['aspect']))
    
    df['season_monsoon'] = df['month'].apply(lambda m: 1 if m in [6, 7, 8, 9] else 0)
    df['season_post-monsoon'] = df['month'].apply(lambda m: 1 if m in [10, 11, 12] else 0)
    df['season_summer'] = df['month'].apply(lambda m: 1 if m in [3, 4, 5] else 0)
    df['season_winter'] = df['month'].apply(lambda m: 1 if m in [1, 2] else 0)
    
    stations = ['station_Acme_(Biwadi)', 'station_Acme_(Hisar)', 'station_Acme_(Karnal)', 'station_Acme_Chittorgarh_Energy_Pvt_Ltd.', 'station_Adani_Renewable_Energy_Four_Pvt_Ltd', 'station_Arinsun_Solar_(Barsaitadesh)', 'station_Avaada_Solar', 'station_Avaada_Solarise', 'station_Ayana', 'station_Azure', 'station_Azure_Power_Earth', 'station_Azure_Power_Forty_Three_Private_Ltd', 'station_Azure_Power_India_Pvt_Ltd', 'station_Azure_Power_Thirty_Four_Private_Ltd', 'station_Clean_Solar_Power_(Bhadla)_Pvt_Ldt', 'station_Dadri_Solar', 'station_Fortum_Fin_Surya', 'station_Fortum_Solar', 'station_Kredl', 'station_M/S_Adani_Solar_Energy_Jodhpur_Two_Ltd', 'station_Mahindra_Solar_(Badwar)', 'station_Ntpc', 'station_Parampujya', 'station_Renew_Solar_Power_Pvt_Ltd', 'station_Renew_Solar_Power_Pvt_Ltd._Bikaner', 'station_Renew_Tn2', 'station_Sb_Energy_Four_Pvt_Ltd', 'station_Sbg_Energy', 'station_Singrauli_Solar', 'station_Spring_Angitra', 'station_Tata_Power', 'station_Tata_Power_Renewable_Energy_Ltd', 'station_Tata_Renewables', 'station_Unchahar_Solar', 'station_Yarrow']
    for s in stations: df[s] = 0
        
    expected_cols = ['solar_radiation', 'elevation', 'slope', 'aspect', 'south_facing', 'slope_x_solar', 'aspect_sin', 'aspect_cos', 'month', 'season_monsoon', 'season_post-monsoon', 'season_summer', 'season_winter'] + stations
    return df[expected_cols]

def main():
    init_gee()
    model = joblib.load('lgb_final_05.pkl')
    coords = pd.read_csv("telugu_villages_coords.csv")
    
    chunk_size = 150 # Reduced slightly for precision processing
    limit = len(coords)
    coords_subset = coords.head(limit)
    
    print(f"Starting High-Precision 12-Month Analysis for {len(coords_subset)} villages...")
    csv_temp = "village_suitability_high_precision_temp.csv"
    
    for start in range(0, len(coords_subset), chunk_size):
        end = min(start + chunk_size, len(coords_subset))
        print(f"\n[High-Precision] Progress: {start}/{len(coords_subset)} villages...")
        chunk = coords_subset.iloc[start:end]
        
        try:
            batch_df = fetch_precision_gee_data(chunk)
            features = build_feature_vector(batch_df)
            
            if hasattr(model, 'predict'):
                scores = model.predict(features)
            else:
                scores = model.booster_.predict(features.values)
                
            batch_df['cuf_prediction'] = scores
            batch_df['verdict'] = batch_df['cuf_prediction'].apply(lambda s: "EXCELLENT" if s>=28 else ("GOOD" if s>=24 else ("MODERATE" if s>=20 else "LOW")))
            
            mode = 'w' if start == 0 else 'a'
            header = True if start == 0 else False
            batch_df.to_csv(csv_temp, index=False, mode=mode, header=header)
            
        except Exception as e:
            print(f"Error in batch {start}-{end}: {e}")
            time.sleep(5)
            continue
            
    print("\n--- Processing Complete ---")
    final_df = pd.read_csv(csv_temp)
    report_name = f"village_suitability_precision_report.xlsx"
    final_df.to_excel(report_name, index=False)
    print(f"Final high-precision report generated: {report_name}")

if __name__ == "__main__":
    main()
