
import requests
import json
try:
    from . import config
except ImportError:
    import config

def send_google_chat_notification(message):
    """
    구글챗 웹훅을 통해 메시지를 전송하는 함수
    """
    try:
        if config.GOOGLE_CHAT_WEBHOOK_URL.startswith("YOUR_GOOGLE_CHAT"):
             print("❌ 구글챗 웹훅 URL이 설정되지 않았거나 유효하지 않습니다.")
             return

        headers = {'Content-Type': 'application/json; charset=UTF-8'}
        data = {'text': message}
        response = requests.post(config.GOOGLE_CHAT_WEBHOOK_URL, data=json.dumps(data), headers=headers)
        response.raise_for_status()
        print("✅ 구글챗 알림 전송 성공!")
    except requests.exceptions.RequestException as e:
        print(f"❌ 구글챗 알림 전송 실패: {e}")
    except Exception as e:
        print(f"❌ 구글챗 알림 전송 중 알 수 없는 오류 발생: {e}")

def format_price_drop_message(row, stats=None):
    """
    가격 하락 정보를 포맷팅하여 메시지 문자열로 반환
    stats: {'avg_1y': 150000, 'recent_price': 155000, 'recent_date': '2025-01-01'} 형식의 통계
    """
    supply_area_pyung = f"{row['공급면적(평수)_현재']:.1f}평"
    
    # 기본 정보
    record = (
        f"🏠 *가격 하락 알림* 🏠\n"
        f"단지: {row['아파트명']}\n"
        f"평형: {supply_area_pyung} ({row['거래타입']})\n"
        f"층: {row['층_현재']}\n"
        f"직전 최저가: {row['가격_이전']}\n"
        f"*현재 최저가: {row['가격_현재']}* 📉\n"
    )

    # 실거래가 기반 통계 추가
    if stats:
        current_sort_price = row['정렬용가격_현재']
        
        # 1년 평균가 및 비율
        if stats.get('avg_1y'):
            avg_1y = stats['avg_1y']
            diff_ratio = ((current_sort_price - avg_1y) / avg_1y) * 100
            label = "상승" if diff_ratio >= 0 else "하락"
            avg_str = format_price_kr(avg_1y)
            record += f"ㄴ 최근 1년 평균: {avg_str} ({abs(diff_ratio):.1f}% {label})\n"
            
        # 최신 실거래 및 비율
        if stats.get('recent_price'):
            recent_p = stats['recent_price']
            recent_d = stats['recent_date']
            diff_ratio = ((current_sort_price - recent_p) / recent_p) * 100
            label = "상승" if diff_ratio >= 0 else "하락"
            recent_str = format_price_kr(recent_p)
            record += f"ㄴ 최신 실거래: {recent_str} ({abs(diff_ratio):.1f}% {label}) [{recent_d}]\n"
            
    record += f"---------------------\n"
    return record

def format_price_kr(price_val):
    """숫자 가격을 한국어 읽기 형식으로 변환"""
    if price_val >= 10000:
        억 = price_val // 10000
        만 = price_val % 10000
        return f"{억}억" + (f" {만}만" if 만 > 0 else "")
    return f"{price_val}만"
