import pandas as pd
import json
import os

def main():
    report_csv = "village_suitability_high_precision_with_coords.csv"
    mapping_file = "admin_mappings.json"
    
    if not os.path.exists(report_csv):
        # Check for the Excel if CSV isn't finished but it was re-run
        report_csv = "village_suitability_precision_report.xlsx"
        if not os.path.exists(report_csv):
            print("Error: Suitability data not found.")
            return

    if not os.path.exists(mapping_file):
        print("Error: admin_mappings.json not found.")
        return

    print("Loading data and mappings...")
    if report_csv.endswith('.csv'):
        suit_df = pd.read_csv(report_csv)
    else:
        suit_df = pd.read_excel(report_csv)
        
    with open(mapping_file, "r") as f:
        maps = json.load(f)
    
    m_map = maps["mandal"]
    d_map = maps["district"]

    print("Applying administrative name mapping...")
    # Convert codes to consistent format (handle floats from CSV)
    def clean_code(val, length=0):
        if pd.isna(val) or val == '': 
            return "00" if length else "0"
        try:
            # Handle float strings like '550.0'
            ival = int(float(val))
            sval = str(ival)
            return sval.zfill(length) if length else sval
        except:
            return str(val)

    suit_df['a1'] = suit_df['a1'].apply(lambda x: clean_code(x, 2))
    suit_df['a2'] = suit_df['a2'].apply(lambda x: clean_code(x))
    suit_df['a3'] = suit_df['a3'].apply(lambda x: clean_code(x))
    
    suit_df['state'] = suit_df['a1'].apply(lambda x: 'Andhra Pradesh' if x == '02' else ('Telangana' if x == '40' else 'Unknown'))
    
    def get_district(row):
        return d_map.get(f"{row['a1']}.{row['a2']}", f"District {row['a2']}")
        
    def get_mandal(row):
        return m_map.get(f"{row['a1']}.{row['a2']}.{row['a3']}", f"Mandal {row['a3']}")

    suit_df['district_name'] = suit_df.apply(get_district, axis=1)
    suit_df['mandal_name'] = suit_df.apply(get_mandal, axis=1)

    print("Aggregating Mandal statistics...")
    summary_rows = []
    
    for (state, dist, mandal, month), group in suit_df.groupby(['state', 'district_name', 'mandal_name', 'month']):
        if state == 'Unknown': continue
        
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
            'Top_Lat': top['latitude'],
            'Top_Lon': top['longitude'],
            'Top_CUF': round(top['cuf_prediction'], 2),
            'Medium_Village': medium['name'],
            'Medium_Lat': medium['latitude'],
            'Medium_Lon': medium['longitude'],
            'Medium_CUF': round(medium['cuf_prediction'], 2),
            'Least_Village': least['name'],
            'Least_Lat': least['latitude'],
            'Least_Lon': least['longitude'],
            'Least_CUF': round(least['cuf_prediction'], 2)
        })
    
    summary_df = pd.DataFrame(summary_rows)
    
    print("Sorting (AP first, then TG, alphabetical by Mandal)...")
    # Andhra Pradesh < Telangana alphabetically
    summary_df = summary_df.sort_values(['State', 'Mandal', 'Month'])
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"mandal_suitability_summary_coords_{timestamp}.xlsx"
    summary_df.to_excel(output_file, index=False)
    print(f"Final summary generated: {output_file}")
    print(f"Total rows: {len(summary_df)}")

if __name__ == "__main__":
    main()
