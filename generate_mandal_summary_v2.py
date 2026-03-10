import pandas as pd
import requests
import zipfile
import io
import os
import numpy as np

def get_full_mapping():
    url = "https://download.geonames.org/export/dump/IN.zip"
    print("Downloading/Reading IN.zip for full mapping...")
    r = requests.get(url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    with z.open("IN.txt") as f:
        cols = ['id', 'name', 'asciiname', 'alt', 'lat', 'lon', 'f_class', 'f_code', 'country', 'cc2', 'a1', 'a2', 'a3', 'a4', 'pop', 'elev', 'dem', 'tz', 'mod']
        # Load only necessary columns to save memory
        df = pd.read_csv(f, sep='\t', header=None, names=cols, low_memory=False, usecols=[1, 7, 10, 11, 12])
        
    df['a1'] = df['a1'].fillna(0).astype(int).astype(str).str.zfill(2)
    # Convert a2, a3 to string for mapping
    df['a2'] = df['a2'].astype(str)
    df['a3'] = df['a3'].astype(str)
    
    # 1. Mandal Mapping (ADM3)
    adm3 = df[(df['a1'].isin(['02', '40'])) & (df['f_code'] == 'ADM3')]
    mandal_map = {}
    for _, row in adm3.iterrows():
        key = f"{row['a1']}.{row['a2']}.{row['a3']}"
        mandal_map[key] = row['name']
        
    # 2. District Mapping (ADM2)
    adm2 = df[(df['a1'].isin(['02', '40'])) & (df['f_code'] == 'ADM2')]
    district_map = {}
    for _, row in adm2.iterrows():
        key = f"{row['a1']}.{row['a2']}"
        district_map[key] = row['name']
        
    # 3. All pop places in AP/TG
    places = df[(df['a1'].isin(['02', '40'])) & (df['f_code'].str.startswith('P'))]
    
    return mandal_map, district_map, places

def main():
    report_csv = "village_suitability_full_12month_temp.csv"
    if not os.path.exists(report_csv):
        print("Error: Suitability data not found.")
        return
        
    print("Loading suitability data...")
    suit_df = pd.read_csv(report_csv)
    
    m_map, d_map, places = get_full_mapping()
    
    # Map villages to Mandals and Districts
    print("Mapping villages to names...")
    places['district_name'] = places.apply(lambda row: d_map.get(f"{row['a1']}.{row['a2']}", f"Dist {row['a2']}"), axis=1)
    places['mandal_name'] = places.apply(lambda row: m_map.get(f"{row['a1']}.{row['a2']}.{row['a3']}", f"Mandal {row['a3']}"), axis=1)
    
    # Linking village names
    mapping = places[['name', 'a1', 'district_name', 'mandal_name']].drop_duplicates(subset=['name'])
    
    print("Joining suitability with Mandal metadata...")
    merged = pd.merge(suit_df, mapping, on='name', how='left')
    
    # State identification for sorting
    merged['state'] = merged['a1'].apply(lambda x: 'Andhra Pradesh' if x == '02' else ('Telangana' if x == '40' else 'Unknown'))
    
    # Handle missing
    merged['mandal_name'] = merged['mandal_name'].fillna('Unknown')
    merged['district_name'] = merged['district_name'].fillna('Unknown')
    
    print("Aggregating Mandal statistics...")
    summary_rows = []
    
    # Group by state, district, mandal, month
    for (state, dist, mandal, month), group in merged.groupby(['state', 'district_name', 'mandal_name', 'month']):
        if mandal == 'Unknown' or state == 'Unknown': continue
        
        group = group.sort_values('cuf_prediction', ascending=False)
        top = group.iloc[0]
        least = group.iloc[-1]
        medium = group.iloc[len(group) // 2]
        
        summary_rows.append({
            'State': state,
            'District': dist,
            'Mandal': mandal,
            'Month': month,
            'Top_Village': top['name'],
            'Top_CUF': round(top['cuf_prediction'], 2),
            'Medium_Village': medium['name'],
            'Medium_CUF': round(medium['cuf_prediction'], 2),
            'Least_Village': least['name'],
            'Least_CUF': round(least['cuf_prediction'], 2)
        })
    
    summary_df = pd.DataFrame(summary_rows)
    
    # CUSTOM SORTING:
    # 1. State (AP first, then TG). "Andhra Pradesh" < "Telangana" alphabetically, so that works.
    # 2. Mandal (Alphabetical)
    # 3. Month (Chronological)
    print("Sorting data...")
    summary_df = summary_df.sort_values(['State', 'Mandal', 'Month'])
    
    output_file = "mandal_suitability_summary_12month_v2.xlsx"
    summary_df.to_excel(output_file, index=False)
    print(f"Refined summary generated: {output_file}")
    print(f"Total rows: {len(summary_df)}")

if __name__ == "__main__":
    main()
