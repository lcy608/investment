import pandas as pd
import os

def check_history():
    file_path = "real_transaction_history.csv"
    if not os.path.exists(file_path):
        print("File not found")
        return
        
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        target_apt = '대흥태영(마포태영)'
        apt_df = df[df['아파트명'] == target_apt]
        print(f"Target Apt: {target_apt}")
        print(f"Total history records for this apt: {len(apt_df)}")
        if not apt_df.empty:
            print(f"Unique Pyeong values: {apt_df['평형'].unique().tolist()}")
            print(f"Unique Trade Types: {apt_df['거래구분'].unique().tolist()}")
        else:
            print("No records found for this apartment name. Available names:")
            print(df['아파트명'].unique()[:10].tolist())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_history()
