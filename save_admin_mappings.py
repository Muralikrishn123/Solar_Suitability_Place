import pandas as pd
import requests
import zipfile
import io
import json

def save_mandal_map():
    url = "https://download.geonames.org/export/dump/IN.zip"
    print("Downloading IN.zip to build Mandal map...")
    r = requests.get(url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    with z.open("IN.txt") as f:
        cols = ['id', 'name', 'asciiname', 'alt', 'lat', 'lon', 'f_class', 'f_code', 'country', 'cc2', 'a1', 'a2', 'a3', 'a4', 'pop', 'elev', 'dem', 'tz', 'mod']
        df = pd.read_csv(f, sep='\t', header=None, names=cols, low_memory=False, usecols=[1, 2, 7, 10, 11, 12])
        
    df['a1'] = df['a1'].fillna(0).astype(int).astype(str).str.zfill(2)
    df['a2'] = df['a2'].astype(str)
    df['a3'] = df['a3'].astype(str)
    
    # 1. Mandal Mapping (ADM3)
    adm3 = df[(df['a1'].isin(['02', '40'])) & (df['f_code'] == 'ADM3')]
    mandal_map = {}
    for _, row in adm3.iterrows():
        # Clean the name (Title Case, ASCII)
        name = str(row['asciiname'] if pd.notna(row['asciiname']) else row['name']).strip().title()
        key = f"{row['a1']}.{row['a2']}.{row['a3']}"
        mandal_map[key] = name
        
    # 2. District Mapping (ADM2)
    adm2 = df[(df['a1'].isin(['02', '40'])) & (df['f_code'] == 'ADM2')]
    district_map = {}
    for _, row in adm2.iterrows():
        name = str(row['asciiname'] if pd.notna(row['asciiname']) else row['name']).strip().title()
        key = f"{row['a1']}.{row['a2']}"
        district_map[key] = name
        
    with open("admin_mappings.json", "w") as f:
        json.dump({"mandal": mandal_map, "district": district_map}, f)
    print(f"Saved {len(mandal_map)} mandals and {len(district_map)} districts to admin_mappings.json")

if __name__ == "__main__":
    save_mandal_map()
