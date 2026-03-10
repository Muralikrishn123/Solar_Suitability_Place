import pandas as pd
import requests
import zipfile
import io
import os
import numpy as np

def download_file(url):
    print(f"Downloading {url}...")
    r = requests.get(url)
    return r.content

def get_mandal_mapping():
    # 1. Get Administrative Names
    print("Fetching Admin names...")
    # Admin2 (Districts)
    a2_content = download_file("https://download.geonames.org/export/dump/admin2Codes.txt")
    a2_df = pd.read_csv(io.BytesIO(a2_content), sep='\t', header=None, names=['full_code', 'name', 'asciiname', 'id'])
    # Admin3 (Mandals)
    a3_content = download_file("https://download.geonames.org/export/dump/admin3Codes.txt")
    a3_df = pd.read_csv(io.BytesIO(a3_content), sep='\t', header=None, names=['full_code', 'name', 'asciiname', 'id'])
    
    # Create maps for quick lookup: { "IN.02.123": "Mandal Name" }
    mandal_map = a3_df.set_index('full_code')['name'].to_dict()
    district_map = a2_df.set_index('full_code')['name'].to_dict()
    
    # 2. Extract Villages with codes
    # Re-reading the big file but just the columns we need
    zip_content = download_file("https://download.geonames.org/export/dump/IN.zip")
    z = zipfile.ZipFile(io.BytesIO(zip_content))
    with z.open("IN.txt") as f:
        cols = ['name', 'latitude', 'longitude', 'admin1_code', 'admin2_code', 'admin3_code']
        # use indices: name(1), lat(4), lon(5), admin1(10), admin2(11), admin3(12)
        df = pd.read_csv(f, sep='\t', header=None, usecols=[1, 4, 5, 10, 11, 12], names=cols, low_memory=False)
        
    # Filter for AP (2) and TG (40)
    # Convert admin codes to string for consistent mapping
    df['admin1_code'] = df['admin1_code'].fillna(0).astype(int).astype(str).str.zfill(2)
    # Some might be nan, we'll handle that
    df = df[df['admin1_code'].isin(['02', '40'])]
    
    # Map to names
    def map_dist(row):
        code = f"IN.{row['admin1_code']}.{row['admin2_code']}"
        return district_map.get(code, f"District {row['admin2_code']}")
        
    def map_mandal(row):
        code = f"IN.{row['admin1_code']}.{row['admin2_code']}.{row['admin3_code']}"
        return mandal_map.get(code, f"Mandal {row['admin3_code']}")

    print("Mapping District and Mandal names...")
    df['district'] = df.apply(map_dist, axis=1)
    df['mandal'] = df.apply(map_mandal, axis=1)
    
    return df[['name', 'latitude', 'longitude', 'district', 'mandal']]

def main():
    # Change it to read the CSV if Excel is too large or not available
    # We generated village_suitability_full_12month_temp.csv earlier 
    report_csv = "village_suitability_full_12month_temp.csv"
    if not os.path.exists(report_csv):
        print("Error: Suitability data not found.")
        return
        
    print("Loading suitability data...")
    suit_df = pd.read_csv(report_csv)
    
    # The suitability data has 'name', 'latitude', 'longitude' columns
    # Actually wait, let me check the headers of report_csv again.
    # From my generate_village_excel_12month.py, it has 'name', 'elevation', 'slope', 'aspect', 'month', 'solar_radiation', 'temperature_c', 'cuf_prediction', 'verdict'
    # BUT IT DOES NOT HAVE LAT/LON.
    # We need to link by name from telugu_villages_coords.csv
    
    coords_df = pd.read_csv("telugu_villages_coords.csv")
    
    # 1. Get basic info
    mandal_meta = get_mandal_mapping()
    
    # Merge coords with mandal_meta on lat/lon to be safe
    # We might have slight float differences, so rounding or approximate join
    coords_df['lat_r'] = coords_df['latitude'].round(4)
    coords_df['lon_r'] = coords_df['longitude'].round(4)
    mandal_meta['lat_r'] = mandal_meta['latitude'].round(4)
    mandal_meta['lon_r'] = mandal_meta['longitude'].round(4)
    
    print("Joining metadata...")
    # Linking village names to mandals
    village_mandal = pd.merge(coords_df, mandal_meta, on=['lat_r', 'lon_r'], how='left', suffixes=('', '_m'))
    # Keep name, district, mandal
    mapping = village_mandal[['name', 'district', 'mandal']].drop_duplicates()
    
    # 2. Join with suitability data
    print("Joining suitability with Mandals...")
    merged = pd.merge(suit_df, mapping, on='name', how='left')
    
    # Handle missing mandals
    merged['mandal'] = merged['mandal'].fillna('Unknown')
    merged['district'] = merged['district'].fillna('Unknown')
    
    # 3. Find Top, Medium, Least for each (Mandal, Month)
    print("Aggregating Mandal statistics...")
    summary_rows = []
    
    for (mandal, month), group in merged.groupby(['mandal', 'month']):
        if mandal == 'Unknown': continue
        
        # Sort by CUF
        group = group.sort_values('cuf_prediction', ascending=False)
        
        top = group.iloc[0]
        least = group.iloc[-1]
        
        # Medium (Median location)
        mid_idx = len(group) // 2
        medium = group.iloc[mid_idx]
        
        district = top.get('district', 'Unknown')
        
        summary_rows.append({
            'District': district,
            'Mandal': mandal,
            'Month': month,
            'Top_Village': top['name'],
            'Top_CUF': top['cuf_prediction'],
            'Medium_Village': medium['name'],
            'Medium_CUF': medium['cuf_prediction'],
            'Least_Village': least['name'],
            'Least_CUF': least['cuf_prediction']
        })
    
    summary_df = pd.DataFrame(summary_rows)
    
    # 4. Save to Excel
    output_file = "mandal_suitability_summary_12month.xlsx"
    summary_df.to_excel(output_file, index=False)
    print(f"Summary generated: {output_file}")

if __name__ == "__main__":
    main()
