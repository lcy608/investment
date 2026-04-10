import requests
import json
import time
import pandas as pd
import os
import tkinter as tk
from tkinter import ttk, messagebox

# --- 데이터 수집 및 처리 함수 ---
def fetch_and_process_data():
    """
    네이버 부동산에서 데이터를 수집하고 정렬 및 가공하는 함수
    """
    complex_numbers = ['1147', '3459', '407', '404']
    
    # API에서 가져올 기본 컬럼: 가격 선택을 위해 dealOrWarrantPrc와 sameAddrMaxPrc 모두 가져옴
    api_columns = ["articleName", "tradeTypeName", "floorInfo", "dealOrWarrantPrc", "area1", "area2", "direction", "sameAddrMaxPrc"]
    
    all_articles_data = []

    # API 요청에 필요한 쿠키와 헤더 (생략: 이전 코드와 동일)
    cookies = {
        'NNB': '3JHC2GQNBUOGQ', 'NAC': 'TB0fCIh1H7ItB', 'NACT': '1', 'SRT30': '1756079544',
        'page_uid': 'j6XDXdqVOZCssDJPACdssssssNR-152480', 'nhn.realestate.article.rlet_type_cd': 'A01', 
        'nhn.realestate.article.trade_type_cd': '""', 'nhn.realestate.article.ipaddress_city': '4100000000',
        '_fwb': '137MlAscdBBCEg8shBPmjnP.1756079548541', 'landHomeFlashUseYn': 'Y', 'SRT5': '1756081996',
        'REALESTATE': 'Mon%20Aug%2025%202025%2009%3A36%3A25%20GMT%2B0900%20(Korean%20Standard%20Time)',
        'PROP_TEST_KEY': '1756082185029.a31effe6c68885c203fb1efc168d7ee53315492c00ae37805661f9bc927d1085',
        'PROP_TEST_ID': '63c8680e92585effaa1a20fda6b479a1e4809d912ba319881f3bd2030a8ad658',
        'BUC': 'LT7DxQZZt00l139_qrXdtU8ua_pVp5WsxW4WYErAuHo=',
    }
    headers = {
        'Accept': '*/*', 'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive', 'Referer': 'https://new.land.naver.com/complexes/3459?ms=37.5379813,126.9556258,17&a=APT:ABYG:JGC:PRE&e=RETAIL&l=1000',
        'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3NTYwODIxODUsImV4cCI6MTc1NjA5Mjk4NX0.PSPWVMFZ1NJpiJHO43Upe9zEgq_UZCBG8VPqSBz3mzA',
        'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"Windows"',
    }
    for complex_no in complex_numbers:
        page = 1
        while True:
            url = f'https://new.land.naver.com/api/articles/complex/{complex_no}?realEstateType=APT%3AABYG%3AJGC%3APRE&tradeType=&tag=%3A%3A%3A%3A%3A%3A%3A%3A&rentPriceMin=0&rentPriceMax=900000000&priceMin=0&priceMax=900000000&areaMin=0&areaMax=900000000&oldBuildYears&recentlyBuildYears&minHouseHoldCount=1000&maxHouseHoldCount&showArticle=false&sameAddressGroup=false&minMaintenanceCost&maxMaintenanceCost&priceType=RETAIL&directions=&page={page}&complexNo={complex_no}&buildingNos=&areaNos=&type=list&order=rank'
            try:
                response = requests.get(url, cookies=cookies, headers=headers, verify=False)
                response.raise_for_status()
                data = response.json()
                if 'articleList' in data and data['articleList']:
                    for article in data['articleList']:
                        extracted_data = {key: article.get(key) for key in api_columns}
                        all_articles_data.append(extracted_data)
                    page += 1
                else:
                    break
            except requests.exceptions.RequestException:
                break
            time.sleep(1)
    
    df = pd.DataFrame(all_articles_data)
    
    # 'tradeTypeName'에 따라 가격 컬럼 선택 및 정렬용 숫자 컬럼 생성
    def select_and_convert_price(row):
        # 월세와 단기임대는 'sameAddrMaxPrc'를 선택
        if row['tradeTypeName'] in ['월세', '단기임대']:
            price_str = str(row['sameAddrMaxPrc'])
        # 나머지는 'dealOrWarrantPrc'를 선택
        else:
            price_str = str(row['dealOrWarrantPrc'])
            
        # 정렬을 위한 숫자 값 변환 로직
        if pd.isna(price_str) or not isinstance(price_str, str): 
            return None, 0
        
        # '억'과 '만'을 숫자로 변환
        numeric_str = price_str.replace('억', '0000').replace('만', '').replace('원', '')
        try:
            sort_value = int(numeric_str.replace(',', '').strip())
        except (ValueError, TypeError):
            sort_value = 0
            
        return price_str, sort_value

    # 'modifiedPrc' 컬럼에 표시할 가격, 'sort_price'에 정렬용 숫자 값 저장
    df[['modifiedPrc', 'sort_price']] = df.apply(lambda row: pd.Series(select_and_convert_price(row)), axis=1)

    df['area3'] = df['area1'] / 3.305785
    df['area4'] = df['area2'] / 3.305785
    
    df_sorted = df.sort_values(by=['articleName', 'tradeTypeName', 'area1', 'sort_price'])
    
    # 불필요한 임시 컬럼 삭제
    df_sorted = df_sorted.drop(columns=['sort_price', 'dealOrWarrantPrc', 'sameAddrMaxPrc'])
    df_sorted = df_sorted.rename(columns={'modifiedPrc': '가격'})
    
    final_columns = ['articleName', 'tradeTypeName', 'floorInfo', '가격', 
                     'area1', 'area2', 'area3', 'area4', 'direction']
    df_sorted = df_sorted[final_columns]
    
    df_sorted.columns = ["아파트명", "거래타입", "층", "가격", "공급면적", "전용면적", "공급면적(평수)", "전용면적(평수)", "방향"]
    
    return df_sorted

# --- GUI 애플리케이션 클래스 ---
class NaverLandApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("네이버 부동산 매물 정보")
        self.geometry("1200x700")
        self.df = pd.DataFrame()
        self.create_widgets()
        self.after(100, self.load_data)

    def create_widgets(self):
        self.tree = ttk.Treeview(self, show="headings")
        self.tree.pack(expand=True, fill='both', padx=10, pady=10)
        
        scrollbar_y = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(self.tree, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        scrollbar_y.pack(side='right', fill='y')
        scrollbar_x.pack(side='bottom', fill='x')

        button_frame = tk.Frame(self)
        button_frame.pack(fill='x', padx=10, pady=5)
        
        self.save_button = tk.Button(button_frame, text="CSV로 저장", command=self.save_to_csv)
        self.save_button.pack(side='right')
        
    def load_data(self):
        try:
            self.status_label = tk.Label(self, text="데이터 수집 중입니다. 잠시만 기다려주세요...", fg="blue")
            self.status_label.pack()
            self.update_idletasks()
            
            self.df = fetch_and_process_data()
            self.update_treeview()
            
            self.status_label.destroy()
            messagebox.showinfo("데이터 수집 완료", f"데이터 수집 및 정렬이 완료되었습니다. 총 {len(self.df)}개의 매물이 있습니다.")
        except Exception as e:
            if hasattr(self, 'status_label'):
                self.status_label.destroy()
            messagebox.showerror("오류 발생", f"데이터를 가져오는 중 오류가 발생했습니다: {e}")

    def update_treeview(self):
        if self.df.empty: return
        for item in self.tree.get_children(): self.tree.delete(item)
        self.tree['columns'] = list(self.df.columns)
        for col in self.df.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        for index, row in self.df.iterrows():
            display_values = list(row)
            display_values[6] = f"{row['공급면적(평수)']:.2f}"
            display_values[7] = f"{row['전용면적(평수)']:.2f}"
            self.tree.insert("", "end", values=display_values)

    def save_to_csv(self):
        if not self.df.empty:
            file_name = 'naver_land_articles.csv'
            self.df.to_csv(file_name, index=False, encoding='utf-8-sig')
            messagebox.showinfo("저장 완료", f"데이터가 '{file_name}' 파일에 성공적으로 저장되었습니다.")
        else:
            messagebox.showwarning("저장 실패", "저장할 데이터가 없습니다.")

if __name__ == "__main__":
    app = NaverLandApp()
    app.mainloop()