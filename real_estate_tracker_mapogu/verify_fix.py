import pandas as pd
import os

files = [
    r"..\naver_land_history.csv",
    r"naver_land_history.csv"
]

print(f"Current Working Directory: {os.getcwd()}")

for f in files:
    print(f"\nChecking {f} with new logic...")
    if os.path.exists(f):
        try:
            # Logic from app_visualizer.py
            try:
                df = pd.read_csv(f, encoding='utf-8-sig')
                if '생성일시' not in df.columns:
                    print("  > utf-8-sig read succeeded but column missing. Raising ValueError.")
                    raise ValueError("Encoding mismatch likely")
                print("  > Success with utf-8-sig!")
            except (UnicodeDecodeError, ValueError) as e:
                print(f"  > utf-8-sig failed ({e}). Trying cp949...")
                df = pd.read_csv(f, encoding='cp949')
                print("  > Success with cp949!")
            
            print(f"  > Loaded Shape: {df.shape}")
            if '생성일시' in df.columns:
                print("  > '생성일시' column present.")
            else:
                print("  > CRITICAL: '생성일시' column STILL missing.")

        except Exception as e:
            print(f"  > FAILED ANY LOAD: {e}")
    else:
        print(f"File not found: {f}")
