import pandas as pd
import os

def add_coordinates():
    suit_csv = 'village_suitability_high_precision_temp.csv'
    coords_csv = 'telugu_villages_coords.csv'
    
    if not os.path.exists(suit_csv) or not os.path.exists(coords_csv):
        print("Missing files.")
        return

    print("Loading data...")
    suit_df = pd.read_csv(suit_csv)
    coords_df = pd.read_csv(coords_csv)

    print("Standardizing keys for join...")
    # Standardize admin codes to strings
    def clean_code(val, length=0):
        if pd.isna(val) or val == '': return "0"
        try:
            return str(int(float(val))).zfill(length) if length else str(int(float(val)))
        except:
            return str(val)

    suit_df['a1'] = suit_df['a1'].apply(lambda x: clean_code(x, 2))
    suit_df['a2'] = suit_df['a2'].apply(lambda x: clean_code(x))
    suit_df['a3'] = suit_df['a3'].apply(lambda x: clean_code(x))
    
    coords_df['admin1_code'] = coords_df['admin1_code'].apply(lambda x: clean_code(x, 2))
    coords_df['admin2_code'] = coords_df['admin2_code'].apply(lambda x: clean_code(x))
    coords_df['admin3_code'] = coords_df['admin3_code'].apply(lambda x: clean_code(x))

    print("Merging coordinates...")
    # Select only name, lat, lon and keys from coords_df
    coords_subset = coords_df[['name', 'latitude', 'longitude', 'admin1_code', 'admin2_code', 'admin3_code']]
    
    # Merge
    merged_df = suit_df.merge(
        coords_subset,
        left_on=['name', 'a1', 'a2', 'a3'],
        right_on=['name', 'admin1_code', 'admin2_code', 'admin3_code'],
        how='left'
    )

    # Clean up redundant columns
    merged_df = merged_df.drop(columns=['admin1_code', 'admin2_code', 'admin3_code'])
    
    # Save the updated detailed report
    report_name = "village_suitability_precision_report.xlsx"
    merged_df.to_excel(report_name, index=False)
    print(f"Updated {report_name} with Latitude/Longitude.")
    
    # Also save temp CSV for summary script
    merged_df.to_csv("village_suitability_high_precision_with_coords.csv", index=False)

if __name__ == "__main__":
    add_coordinates()
