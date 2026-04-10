import pandas as pd
import os

# Define paths relative to d:\python output\real_estate_tracker
files = [
    r"..\naver_land_history.csv",
    r"naver_land_history.csv"
]

print(f"Current Working Directory: {os.getcwd()}")

for f in files:
    print(f"\nChecking {f}...")
    if os.path.exists(f):
        try:
            # Try utf-8-sig first (as in the app)
            try:
                df = pd.read_csv(f, encoding='utf-8-sig')
                print(f"Success with utf-8-sig!")
            except UnicodeDecodeError:
                print(f"utf-8-sig failed. Trying cp949...")
                df = pd.read_csv(f, encoding='cp949')
                print(f"Success with cp949!")
            
            print(f"Shape: {df.shape}")
            print(f"Columns: {df.columns.tolist()}")
            
            required_cols = ['생성일시', '아파트명', '공급면적', '정렬용가격']
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                 print(f"CRITICAL: Missing columns: {missing}")
            else:
                 print("OK: All required columns present.")
                 
        except Exception as e:
            print(f"FAILED to load {f}: {e}")
    else:
        print(f"File not found: {f}")
