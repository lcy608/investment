
import pandas as pd

def search_apt(keyword, encoding, column='아파트명'):
    try:
        print(f"\n--- Testing encoding: {encoding} (searching for '{keyword}' in {column}) ---")
        df = pd.read_csv('real_transaction_history.csv', encoding=encoding)
        if column == '단지번호':
             matches = df[df['단지번호'].astype(str).str.contains(str(keyword), na=False)]
             unique_apts = matches['아파트명'].unique().tolist()
             print(f"Matches for ID '{keyword}': {len(unique_apts)} found")
             for apt in unique_apts:
                 print(f"  - {apt}")
             return True
             
        matches = df[df['아파트명'].str.contains(keyword, na=False)]
        unique_apts = matches['아파트명'].unique().tolist()
        print(f"Matches for '{keyword}': {len(unique_apts)} found")
        for apt in unique_apts:
            print(f"  - {apt}")
            example = matches[matches['아파트명'] == apt].iloc[0]
            print(f"    Example: {example['평형']}, {example['거래구분']}")
        return True
    except Exception as e:
        print(f"Error with {encoding}: {e}")
        return False

for enc in ['utf-8-sig', 'cp949', 'euc-kr']:
    search_apt('도화', enc)
    search_apt('태영', enc)
    search_apt('우성', enc)
    search_apt('405', enc, column='단지번호')
