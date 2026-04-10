import requests
import json
import time
import pandas as pd
import os
import schedule
from datetime import datetime
import re

# --- 1. 원시 데이터 수집 함수 ---
def fetch_all_data():
    """
    네이버 부동산에서 모든 매물 데이터를 수집하여 원시 데이터프레임을 반환
    """
    complex_numbers = ['1147', '3459', '407', '404']
    api_columns = ["articleNo", "articleName", "tradeTypeName", "floorInfo", "dealOrWarrantPrc", "area1", "area2", "direction", "sameAddrMaxPrc"]
    all_articles_data = []

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

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 네이버 부동산 데이터 수집 시작...")
    
    for complex_no in complex_numbers:
        page = 1
        print(f"\n- 단지 번호 {complex_no} 데이터 수집 중...")
        while True:
            url = f'https://new.land.naver.com/api/articles/complex/{complex_no}?realEstateType=APT%3AABYG%3AJGC%3APRE&tradeType=A1%3AB1&tag=%3A%3A%3A%3A%3A%3A%3A%3A&rentPriceMin=0&rentPriceMax=900000000&priceMin=0&priceMax=900000000&areaMin=0&areaMax=900000000&oldBuildYears&recentlyBuildYears&minHouseHoldCount=1000&maxHouseHoldCount&showArticle=false&sameAddressGroup=false&minMaintenanceCost&maxMaintenanceCost&priceType=RETAIL&directions=&page={page}&complexNo={complex_no}&buildingNos=&areaNos=&type=list&order=rank'
            try:
                response = requests.get(url, cookies=cookies, headers=headers, verify=False)
                response.raise_for_status()
                data = response.json()
                
                if 'articleList' in data and data['articleList']:
                    num_articles_on_page = len(data['articleList'])
                    print(f"  - 단지 {complex_no}, 페이지 {page}: {num_articles_on_page}개 매물 수집 완료.")
                    for article in data['articleList']:
                        extracted_data = {key: article.get(key) for key in api_columns}
                        all_articles_data.append(extracted_data)
                    page += 1
                else:
                    print(f"  - 단지 {complex_no}, 페이지 {page}: 더 이상 매물이 없습니다.")
                    break
            except requests.exceptions.RequestException as e:
                print(f"❌ API 요청 오류 발생: {e}")
                break
            time.sleep(1)
    
    print(f"\n✅ 전체 데이터 수집 완료! 총 {len(all_articles_data)}개 매물 수집.")
    return pd.DataFrame(all_articles_data)

# --- 2. 데이터 가공 함수 ---
def process_data(df):
    """
    원시 데이터프레임을 받아 가공하고 최저가 매물만 추출하여 반환
    """
    def select_and_convert_price(row):
        price_str = str(row['dealOrWarrantPrc'])
        if pd.isna(price_str) or not isinstance(price_str, str): 
            return None, 0
            
        numeric_str = price_str.replace(',', '').replace('원', '').strip()
        
        if '억' in numeric_str:
            parts = re.split('억', numeric_str)
            억 = int(parts[0]) if parts[0] else 0
            만 = int(parts[1].replace('만', '')) if parts[1] else 0
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
    df['area3'] = df['area1'] / 3.305785
    df['area4'] = df['area2'] / 3.305785
    
    df_min_prices = df.loc[df.groupby(['articleName', 'tradeTypeName', 'area1'])['sort_price'].idxmin()]
    
    df_min_prices = df_min_prices.drop(columns=['dealOrWarrantPrc', 'sameAddrMaxPrc'])
    df_min_prices = df_min_prices.rename(columns={'modifiedPrc': '가격'})
    df_min_prices = df_min_prices.sort_values(by=['articleName', 'tradeTypeName', 'area1'])
    
    final_columns = ['articleNo', 'articleName', 'tradeTypeName', 'floorInfo', '가격', 'sort_price',
                     'area1', 'area2', 'area3', 'area4', 'direction']
    df_min_prices = df_min_prices[final_columns]
    df_min_prices.columns = ["매물번호", "아파트명", "거래타입", "층", "가격", "정렬용가격", "공급면적", "전용면적", "공급면적(평수)", "전용면적(평수)", "방향"]
    
    return df_min_prices

# --- 메인 작업 함수: 가격 비교 및 CSV 저장 ---
def job():
    current_time = datetime.now()
    new_raw_file_name = f"{current_time.strftime('%Y%m%d_%H%M')}_raw.csv"
    new_min_file_name = f"{current_time.strftime('%Y%m%d_%H%M')}.csv"
    previous_file_name = 'last_min_prices.csv'
    
    print(f"\n[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] 최저가 매물 데이터 수집 및 비교 시작...")
    
    try:
        if os.path.exists(previous_file_name):
            last_df = pd.read_csv(previous_file_name, encoding='utf-8-sig')
        else:
            last_df = pd.DataFrame()
            
        raw_df = fetch_all_data()

        raw_df.to_csv(new_raw_file_name, index=False, encoding='utf-8-sig')
        print(f"✅ 원시 데이터가 '{new_raw_file_name}' 파일에 저장되었습니다.")

        current_df = process_data(raw_df)

        current_df_no_sort_price = current_df.drop(columns=['정렬용가격'])
        current_df_no_sort_price.to_csv(new_min_file_name, index=False, encoding='utf-8-sig')
        print(f"🎉 최저가 데이터가 '{new_min_file_name}' 파일에 저장되었습니다.")
        
        current_df.to_csv(previous_file_name, index=False, encoding='utf-8-sig')

        if not last_df.empty:
            merged_df = pd.merge(last_df, current_df, on=["아파트명", "거래타입", "공급면적"], suffixes=('_이전', '_현재'))
            
            price_drop_df = merged_df[
                (merged_df['정렬용가격_현재'] < merged_df['정렬용가격_이전'])
            ]
            
            if not price_drop_df.empty:
                print("👍 가격이 하락한 매물이 발견되었습니다!")
                
                # 텍스트 파일에 기록
                with open('price_drops.txt', 'a', encoding='utf-8') as f:
                    f.write(f"\n======== 가격 하락 발견: {current_time.strftime('%Y-%m-%d %H:%M:%S')} ========\n")
                    for _, row in price_drop_df.iterrows():
                        record = (
                            f"  아파트: {row['아파트명']}\n"
                            f"  거래타입: {row['거래타입']}\n"
                            f"  공급면적: {row['공급면적']}\n"
                            f"  이전 가격: {row['가격_이전']}\n"
                            f"  현재 가격: {row['가격_현재']}\n"
                            f"  ---------------------\n"
                        )
                        print(record, end='') # 콘솔에도 출력
                        f.write(record)
            else:
                print("👍 가격이 하락한 매물이 없습니다.")
        else:
            print("ℹ️ 이전 데이터가 없어 가격 비교를 할 수 없습니다. 다음 실행부터 비교가 시작됩니다.")
            
    except Exception as e:
        print(f"❌ 작업 중 치명적인 오류 발생: {e}")

# --- 메인 실행부 ---
if __name__ == "__main__":
    schedule.every(1).minutes.do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)