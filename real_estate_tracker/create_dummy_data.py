import pandas as pd
import os
import config
from datetime import datetime

# Define columns as expected by processor/app_visualizer
columns = ["매물번호", "아파트명", "거래타입", "층", "가격", "정렬용가격", "공급면적", "전용면적", "공급면적(평수)", "전용면적(평수)", "방향", "생성일시"]

# Create dummy data
data = [
    ["1001", "Test Apt 1", "매매", "10/20", "10억", 100000, "84.00", "59.00", "25.4", "17.8", "South", datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
    ["1002", "Test Apt 1", "매매", "5/20", "9억 5000", 95000, "84.00", "59.00", "25.4", "17.8", "South", datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
    ["1003", "Test Apt 2", "매매", "15/30", "15억", 150000, "114.00", "84.00", "34.5", "25.4", "East", datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
]

df = pd.DataFrame(data, columns=columns)

# Save to config path
file_path = os.path.join(config.DATA_DIR, config.HISTORY_FILE_NAME)
df.to_csv(file_path, index=False, encoding='utf-8-sig')

print(f"Dummy data created at {file_path}")
print("Run 'streamlit run app_visualizer.py' to test.")
