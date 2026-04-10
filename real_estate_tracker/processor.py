
import pandas as pd
import re

def process_data(df):
    """
    원시 데이터프레임을 받아 가공하고 최저가 매물만 추출하여 반환
    """
    if df.empty:
        return pd.DataFrame()

    def select_and_convert_price(row):
        price_str = str(row['dealOrWarrantPrc'])
        if pd.isna(price_str) or not isinstance(price_str, str): 
            return None, 0
            
        numeric_str = price_str.replace(',', '').replace('원', '').strip()
        
        if '억' in numeric_str:
            parts = re.split('억', numeric_str)
            억 = int(parts[0]) if parts[0] else 0
            만 = int(parts[1].replace('만', '')) if len(parts) > 1 and parts[1] else 0
            sort_value = 억 * 10000 + 만
        elif '만' in numeric_str:
            sort_value = int(numeric_str.replace('만', ''))
        else:
            try:
                sort_value = int(numeric_str)
            except (ValueError, TypeError):
                sort_value = 0
        
        return price_str, sort_value

    df[['modifiedPrc', 'sort_price']] = df.apply(lambda row: pd.Series(select_and_convert_price(row)), axis=1)
    
    # 평수 환산 (1평 = 3.305785 제곱미터)
    df['area3'] = (pd.to_numeric(df['area1'], errors='coerce') / 3.305785).round(1) # 공급면적(평수)
    df['area4'] = (pd.to_numeric(df['area2'], errors='coerce') / 3.305785).round(1) # 전용면적(평수)
    
    # Extract minimum prices per group
    # Group by Apartment Name, Trade Type, and Supply Area
    # Get the index of the minimum sort_price
    try:
        idx = df.groupby(['articleName', 'tradeTypeName', 'area1'])['sort_price'].idxmin()
        df_min_prices = df.loc[idx].copy()
    except ValueError:
         return pd.DataFrame()
    
    df_min_prices = df_min_prices.drop(columns=['dealOrWarrantPrc', 'sameAddrMaxPrc'])
    df_min_prices = df_min_prices.rename(columns={'modifiedPrc': '가격'})
    df_min_prices = df_min_prices.sort_values(by=['articleName', 'tradeTypeName', 'area1'])
    
    final_columns = ['articleNo', 'articleName', 'tradeTypeName', 'floorInfo', '가격', 'sort_price',
                     'area1', 'area2', 'area3', 'area4', 'direction']
    
    # Filter columns that exist
    final_columns = [c for c in final_columns if c in df_min_prices.columns]
    
    df_min_prices = df_min_prices[final_columns]
    df_min_prices.columns = ["매물번호", "아파트명", "거래타입", "층", "가격", "정렬용가격", "공급면적", "전용면적", "공급면적(평수)", "전용면적(평수)", "방향"]
    
    return df_min_prices

def detect_price_drops(last_df, current_df):
    """
    이전 데이터와 현재 데이터를 비교하여 가격이 하락한 매물을 반환합니다.
    """
    if last_df.empty or current_df.empty:
        return pd.DataFrame()

    # Merge on identifying columns
    merged_df = pd.merge(last_df, current_df, on=["아파트명", "거래타입", "공급면적"], suffixes=('_이전', '_현재'))
    
    # Filter for price drops
    price_drop_df = merged_df[
        (merged_df['정렬용가격_이전'] > merged_df['정렬용가격_현재'])
    ]
    
    return price_drop_df
