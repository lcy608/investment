import requests
import json
import time
import pandas as pd
import os
import schedule
from datetime import datetime
import re

# --- 알림 설정 ---
# 구글챗 웹훅 URL을 여기에 입력하세요. (필수)
# 예: GOOGLE_CHAT_WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAAA12345/messages?key=..."
GOOGLE_CHAT_WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAQAcDkeJSk/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=sBgQytan3_5KMuaP3xUyCSzAIw0LkfjIesu0JVx9bxY" # 여기에 실제 웹훅 URL을 붙여넣으세요.

# --- 1. 원시 데이터 수집 함수 ---
def fetch_all_data():
    """s
    네이버 부동산에서 모든 매물 데이터를 수집하여 원시 데이터프레임을 반환
    """
    complex_numbers = ['1147', '407', '404','8177','3310','841','105738','3459','403','2992'] #'155817','111515'
    api_columns = ["articleNo", "articleName", "tradeTypeName", "floorInfo", "dealOrWarrantPrc", "area1", "area2", "direction", "sameAddrMaxPrc"]
    all_articles_data = []

    cookies = {
    'NAC': 'Do9FBwgVCd42',
    'NACT': '1',
    'SRT30': '1757054011',
    'SRT5': '1757054011',
    'NNB': '4HBI2YZ3QS5GQ',
    'nhn.realestate.article.rlet_type_cd': 'A01',
    'nhn.realestate.article.trade_type_cd': '""',
    'nhn.realestate.article.ipaddress_city': '4100000000',
    '_fwb': '198nbE3QIDZiWoQsPljddvV.1757054013650',
    'landHomeFlashUseYn': 'Y',
    '_fwb': '198nbE3QIDZiWoQsPljddvV.1757054013650',
    'REALESTATE': 'Fri%20Sep%2005%202025%2015%3A33%3A50%20GMT%2B0900%20(Korean%20Standard%20Time)',
    'PROP_TEST_KEY': '1757054030203.54baba91d82960c4d44318f5edad95e82acdd146e84fb9f7e0b789102b2c437e',
    'PROP_TEST_ID': 'b099bd668153ad727e7ff271dc0643726abf4534ddb414cc58f4776eb29ea9d6',
    'BUC': 'z3DHHZyGgVD9WtszDb-BGPSopF1gT_BigAhSajqEmrs=',
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'ko',
        'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3NTcwNTQwMzAsImV4cCI6MTc1NzA2NDgzMH0.a87rlDcovHbsh-bOYkiO26yHY72mq4hku-5LYCpgGNM',
        'priority': 'u=1, i',
        'referer': 'https://new.land.naver.com/complexes?ms=37.3595704,127.105399,16&a=APT:ABYG:JGC:PRE&e=RETAIL',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        # 'cookie': 'NAC=Do9FBwgVCd42; NACT=1; SRT30=1757054011; SRT5=1757054011; NNB=4HBI2YZ3QS5GQ; nhn.realestate.article.rlet_type_cd=A01; nhn.realestate.article.trade_type_cd=""; nhn.realestate.article.ipaddress_city=4100000000; _fwb=198nbE3QIDZiWoQsPljddvV.1757054013650; landHomeFlashUseYn=Y; _fwb=198nbE3QIDZiWoQsPljddvV.1757054013650; REALESTATE=Fri%20Sep%2005%202025%2015%3A33%3A50%20GMT%2B0900%20(Korean%20Standard%20Time); PROP_TEST_KEY=1757054030203.54baba91d82960c4d44318f5edad95e82acdd146e84fb9f7e0b789102b2c437e; PROP_TEST_ID=b099bd668153ad727e7ff271dc0643726abf4534ddb414cc58f4776eb29ea9d6; BUC=z3DHHZyGgVD9WtszDb-BGPSopF1gT_BigAhSajqEmrs=',
    }

    for complex_no in complex_numbers:
        page = 1
        while True:
            url = f'https://new.land.naver.com/api/articles/complex/{complex_no}?realEstateType=APT%3AABYG%3AJGC%3APRE&tradeType=A1%3AB1&tag=%3A%3A%3A%3A%3A%3A%3A%3A&rentPriceMin=0&rentPriceMax=900000000&priceMin=0&priceMax=900000000&areaMin=0&areaMax=900000000&oldBuildYears&recentlyBuildYears&minHouseHoldCount=1000&maxHouseHoldCount&showArticle=false&sameAddressGroup=false&minMaintenanceCost&maxMaintenanceCost&priceType=RETAIL&directions=&page={page}&complexNo={complex_no}&buildingNos=&areaNos=&type=list&order=rank'
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
    # 평수 환산 (1평 = 3.305785 제곱미터)
    df['area3'] = (df['area1'] / 3.305785).round(1) # 공급면적(평수)
    df['area4'] = (df['area2'] / 3.305785).round(1) # 전용면적(평수)
    
    df_min_prices = df.loc[df.groupby(['articleName', 'tradeTypeName', 'area1'])['sort_price'].idxmin()]
    
    df_min_prices = df_min_prices.drop(columns=['dealOrWarrantPrc', 'sameAddrMaxPrc'])
    df_min_prices = df_min_prices.rename(columns={'modifiedPrc': '가격'})
    df_min_prices = df_min_prices.sort_values(by=['articleName', 'tradeTypeName', 'area1'])
    
    final_columns = ['articleNo', 'articleName', 'tradeTypeName', 'floorInfo', '가격', 'sort_price',
                     'area1', 'area2', 'area3', 'area4', 'direction']
    df_min_prices = df_min_prices[final_columns]
    df_min_prices.columns = ["매물번호", "아파트명", "거래타입", "층", "가격", "정렬용가격", "공급면적", "전용면적", "공급면적(평수)", "전용면적(평수)", "방향"]
    
    return df_min_prices

# --- 알림 전송 함수 ---
def send_google_chat_notification(message):
    """
    구글챗 웹훅을 통해 메시지를 전송하는 함수
    """
    try:
        # NOTE: 이 코드는 디버깅용으로, 실제 URL이 아닌 경우 알림 전송을 막습니다.
        # 실제 사용 시에는 URL을 유효하게 설정해주세요.
        if GOOGLE_CHAT_WEBHOOK_URL.startswith("YOUR_GOOGLE_CHAT_WEBHOOK_URL") or not GOOGLE_CHAT_WEBHOOK_URL:
            print("❌ 구글챗 웹훅 URL이 설정되지 않았거나 유효하지 않습니다. 알림을 보낼 수 없습니다.")
            return

        headers = {'Content-Type': 'application/json; charset=UTF-8'}
        data = {'text': message}
        response = requests.post(GOOGLE_CHAT_WEBHOOK_URL, data=json.dumps(data), headers=headers)
        response.raise_for_status()
        print("✅ 구글챗 알림 전송 성공!")
    except requests.exceptions.RequestException as e:
        print(f"❌ 구글챗 알림 전송 실패: {e}")
    except Exception as e:
        print(f"❌ 구글챗 알림 전송 중 알 수 없는 오류 발생: {e}")

# --- 메인 작업 함수: 가격 비교 및 CSV 저장 ---
def job():
    current_time = datetime.now()
    current_date = current_time.strftime('%Y-%m-%d')
    new_raw_file_name = f"{current_time.strftime('%Y%m%d_%H%M')}_raw.csv"
    new_min_file_name = f"{current_time.strftime('%Y%m%d_%H%M')}.csv"
    previous_file_name = 'last_min_prices.csv'
    history_file_name = 'naver_land_history.csv'
    
    print(f"\n[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] 최저가 매물 데이터 수집 및 비교 시작...")
    
    try:
        if os.path.exists(previous_file_name):
            # dtype={'매물번호': str} 추가하여 데이터 타입 일관성 유지
            last_df = pd.read_csv(previous_file_name, encoding='utf-8-sig', dtype={'매물번호': str}) 
        else:
            last_df = pd.DataFrame()
            
        raw_df = fetch_all_data()

        raw_df.to_csv(new_raw_file_name, index=False, encoding='utf-8-sig')
        print(f"✅ 원시 데이터가 '{new_raw_file_name}' 파일에 저장되었습니다.")

        current_df = process_data(raw_df) 
        current_df.to_csv(new_min_file_name, index=False, encoding='utf-8-sig')
        print(f"🎉 최저가 데이터가 '{new_min_file_name}' 파일에 저장되었습니다.")
        
        # 다음 비교를 위해 현재 데이터를 last 파일에 저장
        current_df.to_csv(previous_file_name, index=False, encoding='utf-8-sig')
        
        # '생성일시' 컬럼 추가
        current_df['생성일시'] = current_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # --- 누적 파일에 데이터 추가 (날짜 기반 덮어쓰기 로직) ---
        if os.path.exists(history_file_name):
            # 기존 누적 파일 불러오기
            history_df = pd.read_csv(history_file_name, encoding='utf-8-sig', dtype={'매물번호': str})
            
            # '생성일시' 컬럼에서 날짜만 추출
            history_df['날짜'] = pd.to_datetime(history_df['생성일시']).dt.strftime('%Y-%m-%d')
            
            # 오늘 날짜와 일치하는 데이터는 제외하고 병합
            history_df = history_df[history_df['날짜'] != current_date]
            history_df = pd.concat([history_df, current_df], ignore_index=True)
            history_df = history_df.drop(columns=['날짜']) # 임시로 만든 '날짜' 컬럼 제거
            
            history_df.to_csv(history_file_name, index=False, encoding='utf-8-sig')
            print(f"🎉 누적 파일 '{history_file_name}'에 오늘 데이터로 대체 완료.")
        else:
            # 누적 파일이 없으면 새로 생성
            current_df.to_csv(history_file_name, index=False, encoding='utf-8-sig')
            print(f"🎉 누적 파일 '{history_file_name}' 생성 완료.")


        if not last_df.empty:
            merged_df = pd.merge(last_df, current_df, on=["아파트명", "거래타입", "공급면적"], suffixes=('_이전', '_현재'))
            
            # 정렬용가격이 감소한 경우 (가격 하락)
            price_drop_df = merged_df[
                (merged_df['정렬용가격_이전'] > merged_df['정렬용가격_현재'])
            ]
            
            print(price_drop_df)
            
            # --- job() 함수 내의 price_drop_df 생성 후 (약 323번째 줄 근처) ---

            # 💡 [임시 디버깅 코드] merged_df의 모든 컬럼 이름 확인
            print("\n[DEBUG] merged_df 컬럼 목록:")
            print(merged_df.columns.tolist())
            print("-" * 40)
            # ---------------------------------------------
            
            if not price_drop_df.empty:
                print("👍 가격이 하락한 매물이 발견되었습니다!")
                
                notification_message = f"🏠 네이버 부동산 가격 하락 알림! ({current_time.strftime('%Y-%m-%d %H:%M:%S')})\n\n"

                
                # 텍스트 파일에 기록 및 알림 메시지 구성 (수정된 부분)
                with open('price_drops.txt', 'a', encoding='utf-8') as f:
                    f.write(f"\n======== 가격 하락 발견: {current_time.strftime('%Y-%m-%d %H:%M:%S')} ========\n")
                    for _, row in price_drop_df.iterrows():
                        
                        # --- 평수 정보 추가 ---
                        supply_area_pyung = f"{row['공급면적(평수)_현재']:.1f}평"
                        only_area_pyung = f"{row['전용면적(평수)_현재']:.1f}평"
                        # -------------------------
                        
                        record = (
                            f"  아파트: {row['아파트명']}\n"
                            f"  거래타입: {row['거래타입']}\n"
                            f"  공급면적: {row['공급면적']}\n"
                            f"  공급평형: {supply_area_pyung}\n"
                            f"  전용평형: {only_area_pyung}\n"
                            f"  이전 가격: {row['가격_이전']}\n"
                            f"  현재 가격: {row['가격_현재']}\n"
                            f"  ---------------------\n"
                        )
                        print(record, end='') # 콘솔에도 출력
                        f.write(record)
                        notification_message += record

                send_google_chat_notification(notification_message)

            else:
                print("👍 가격이 하락한 매물이 없습니다.")
        else:
            print("ℹ️ 이전 데이터가 없어 가격 비교를 할 수 없습니다. 다음 실행부터 비교가 시작됩니다.")
            
    except Exception as e:
        print(f"❌ 작업 중 치명적인 오류 발생: {e}")

# --- 메인 실행부 ---
if __name__ == "__main__":
    
    job() # 먼저 실행 하고, 다음에 N 분 주기로 스케쥴링 타도록 하기위해 단독 수행
    
    schedule.every(20).minutes.do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)