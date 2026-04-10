import pandas as pd
import os

def test_matching_exactly_like_main():
    history_file = "real_transaction_history.csv"
    if not os.path.exists(history_file):
        print(f"Error: {history_file} not found")
        return

    try:
        df = pd.read_csv(history_file, encoding='utf-8-sig')
        df['날짜'] = pd.to_datetime(df['날짜'])
        print(f"Loaded {len(df)} records")
    except Exception as e:
        print(f"Load failed: {e}")
        return

    # User's test case
    target_apt = "대흥태영(마포태영)"
    target_trade = "매매"
    target_pyeong_val = 43.0
    
    # Logic from main.py
    apt_name = str(target_apt).replace(' ', '').strip()
    trade_type = str(target_trade).replace(' ', '').strip()
    pyeong_val = int(round(target_pyeong_val))
    pyeong_str = f"{pyeong_val}평"
    
    print(f"Searching for: Apt='{apt_name}', Type='{trade_type}', Pyeong='{pyeong_str}'")
    
    mask = (
        (df['아파트명'].str.replace(' ', '', regex=False) == apt_name) &
        (df['거래구분'].str.replace(' ', '', regex=False) == trade_type) &
        (df['평형'].str.contains(pyeong_str, na=False))
    )
    
    prop_history = df[mask].sort_values('날짜', ascending=False)
    
    if not prop_history.empty:
        print(f"SUCCESS! Found {len(prop_history)} records.")
        latest = prop_history.iloc[0]
        print(f"Latest: {latest['날짜'].strftime('%Y-%m-%d')}, {latest['정렬용가격']}")
    else:
        print("MATCH FAILED.")
        # Diagnostics
        print("\nChecking Apartment Name:")
        # Let's see what names are actually in the DB
        unique_names = df['아파트명'].unique().tolist()
        print(f"  First 5 names in DB: {unique_names[:5]}")
        
        apt_only = df[df['아파트명'].str.replace(' ', '', regex=False) == apt_name]
        print(f"  Apt name search: '{apt_name}'")
        print(f"  Apt name match count: {len(apt_only)}")
        
        if not apt_only.empty:
            print(f"  Available trade types: {apt_only['거래구분'].unique().tolist()}")
            print(f"  Available pyeong values: {apt_only['평형'].unique().tolist()}")
            
            print("\nChecking Trade Type match:")
            print(f"  Searching for type: '{trade_type}'")
            trade_only = apt_only[apt_only['거래구분'].str.replace(' ', '', regex=False) == trade_type]
            print(f"  Trade type match count: {len(trade_only)}")
            
            if not trade_only.empty:
                print("\nChecking Pyeong string match:")
                print(f"  Searching for pyeong string: '{pyeong_str}'")
                for p in trade_only['평형'].unique():
                    print(f"  - Does '{p}' contain '{pyeong_str}'? {pyeong_str in str(p)}")
        else:
            print("  Apartment not found. Checking if any name contains part of it...")
            partial_matches = [n for n in unique_names if "태영" in str(n)]
            print(f"  Names containing '태영': {partial_matches}")

if __name__ == "__main__":
    test_matching_exactly_like_main()
