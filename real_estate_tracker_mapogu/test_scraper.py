import scraper
import pandas as pd
import config
import os

try:
    print("Fetching data using scraper...")
    df = scraper.fetch_all_data()
    if not df.empty:
        print(f"Successfully fetched {len(df)} records.")
        # Create a dummy history file for testing app_visualizer.py
        # We need to add '생성일시' as expected by app_visualizer.py
        current_time = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        df['생성일시'] = current_time
        # app_visualizer expects '아파트명' and '공급면적', '정렬용가격'
        # But wait, scraper returns raw API columns: "articleNo", "articleName", "tradeTypeName", "floorInfo", "dealOrWarrantPrc", "area1", "area2", "direction", "sameAddrMaxPrc"
        # processor.py usually processes this.
        # We need to run processor as well.
        import processor
        processed_df = processor.process_data(df)
        processed_df['생성일시'] = current_time
        
        history_path = os.path.join(config.DATA_DIR, config.HISTORY_FILE_NAME)
        processed_df.to_csv(history_path, index=False, encoding='utf-8-sig')
        print(f"Saved test data to {history_path}")
    else:
        print("Scraper returned empty dataframe. Likely API issue or no data.")
except Exception as e:
    print(f"Scraper failed with error: {e}")
