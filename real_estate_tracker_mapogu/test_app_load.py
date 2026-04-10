import app_visualizer
import pandas as pd

try:
    print("Testing load_data()...")
    df = app_visualizer.load_data()
    if not df.empty:
        print(f"Successfully loaded {len(df)} records.")
        print(f"Columns: {df.columns.tolist()}")
        if 'Date' in df.columns:
            print("Date column present.")
        else:
            print("Date column MISSING!")
    else:
        print("load_data() returned empty DataFrame.")
except Exception as e:
    print(f"load_data() failed with error: {e}")
