import pandas as pd
import os

def debug_match():
    history_file = "real_transaction_history.csv"
    if not os.path.exists(history_file):
        print(f"❌ {history_file} not found")
        return

    try:
        df = pd.read_csv(history_file, encoding='utf-8-sig')
        df['날짜'] = pd.to_datetime(df['날짜'])
        print(f"Loaded {len(df)} records from history")
    except Exception as e:
        print(f"Load failed: {e}")
        return

    # Sample row data from user report
    sample_row = {
        '아파트명': '대흥태영(마포태영)',
        '거래타입': '매매',
        '공급면적(평수)_현재': 43.0,
        '정렬용가격_현재': 238000
    }

    pyeong_val = int(round(sample_row['공급면적(평수)_현재']))
    pyeong_str = f"{pyeong_val}평"
    print(f"Searching for: Apt='{sample_row['아파트명']}', Type='{sample_row['거래타입']}', Pyeong='{pyeong_str}'")

    # Debugging exact values in the dataframe
    apt_records = df[df['아파트명'] == sample_row['아파트명']]
    print(f"Records found for apt '{sample_row['아파트명']}': {len(apt_records)}")
    
    if not apt_records.empty:
        print(f"Unique types for this apt: {apt_records['거래구분'].unique()}")
        print(f"Unique pyeong for this apt: {apt_records['평형'].unique()}")
        
        type_mask = (apt_records['거래구분'] == sample_row['거래타입'])
        type_records = apt_records[type_mask]
        print(f"Records after trade type filter: {len(type_records)}")
        
        if not type_records.empty:
            pyeong_mask = type_records['평형'].str.contains(pyeong_str, na=False)
            final_match = type_records[pyeong_mask]
            print(f"Final matches after pyeong filter: {len(final_match)}")

    if match_count > 0:
        prop_history = df[mask].sort_values('날짜', ascending=False)
        latest = prop_history.iloc[0]
        print(f"Latest Transaction: {latest['날짜'].strftime('%Y-%m-%d')}, {latest['정렬용가격']}")
        
        one_year_ago = pd.Timestamp.now() - pd.Timedelta(days=365)
        last_1y = prop_history[prop_history['날짜'] >= one_year_ago]
        print(f"Transactions in last 1y: {len(last_1y)}")
        if not last_1y.empty:
            print(f"Avg 1y: {int(last_1y['정렬용가격'].mean())}")
    else:
        # Check available names/types to see why it failed
        print("Debugging why no match was found...")
        available_names = df['아파트명'].unique()
        print(f"Sample available names: {available_names[:5]}")
        if sample_row['아파트명'] not in available_names:
            print(f"❌ Apartment name mismatch! '{sample_row['아파트명']}' not found in {available_names}")
        
        available_types = df['거래구분'].unique()
        if sample_row['거래타입'] not in available_types:
            print(f"❌ Trade type mismatch! '{sample_row['거래타입']}' not found in {available_types}")

        # Check pyeong for the apartment
        apt_hist = df[df['아파트명'] == sample_row['아파트명']]
        if not apt_hist.empty:
            print(f"Pyeong for this apt: {apt_hist['평형'].unique()}")

if __name__ == "__main__":
    debug_match()
