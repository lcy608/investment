import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Notification Toggle (Set which channels to use)
USE_GOOGLE_CHAT = True

# Google Chat Webhook URL
GOOGLE_CHAT_WEBHOOK_URL = os.getenv("GOOGLE_CHAT_WEBHOOK_URL", "https://chat.googleapis.com/v1/spaces/AAQAcDkeJSk/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=sBgQytan3_5KMuaP3xUyCSzAIw0LkfjIesu0JVx9bxY")

# Target Complex Numbers
USE_DYNAMIC_COMPLEX_LIST = True
MIN_HOUSEHOLD_COUNT = 500
COMPLEX_NUMBERS = ['1147', '407', '404', '8177', '3310', '841', '105738', '3459', '403', '2992','17081']

# API Columns to extract
API_COLUMNS = [
    "articleNo", "articleName", "tradeTypeName", "floorInfo", 
    "dealOrWarrantPrc", "area1", "area2", "direction", "sameAddrMaxPrc"
]

# Request Headers
HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'ko,ko-KR;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
    'Referer': 'https://new.land.naver.com/complexes/1147?ms=37.5455239,126.9411385,16&a=APT:ABYG:JGC:PRE&b=B1&e=RETAIL&f=60000&g=100000&h=99&i=132&l=344',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3NzQwMTIwMTksImV4cCI6MTc3NDAyMjgxOX0.or1Wud9eWWxvmQlVbQBS069VMtGxglwMTzJ0xxAWw8Y',
    'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

# Request Cookies
COOKIES = {
    'NAC': 'H3vYB4gY3HYG',
    'NNB': 'L34VC2DK25AGS',
    'NACT': '1',
    'SRT30': '1774011999',
    'SRT5': '1774011999',
    'page_uid': 'jk1bhsqVJ5UgGPi6fd8-452552',
    '_naver_usersession_': 'qMhxt+A5DtMdzHNa+rasgVuA',
    'nhn.realestate.article.rlet_type_cd': 'A01',
    'nhn.realestate.article.trade_type_cd': '""',
    'nhn.realestate.article.ipaddress_city': '1100000000',
    '_fwb': '2304Ni2T7Qw1BOJvjLeaWW3.1774011941727',
    'landHomeFlashUseYn': 'Y',
    'REALESTATE': 'Fri%20Mar%2020%202026%2022%3A06%3A59%20GMT%2B0900%20(Korean%20Standard%20Time)',
    'PROP_TEST_KEY': '1774012019652.bf455c70a7e44342e9d65765efe84e1ce2dcaab60975e2f56a191e505b5a7034',
    'PROP_TEST_ID': '530bae3e1dc6dddca0f8c5737506bcf4b40db9e632b5b967506e8465cec987d9',
    'BUC': '5AWH0GijBc5L4YgMphEwvimR4m3Y4zPt3_F_5wWqNxs=',
}

# File Paths
DATA_DIR = "."  # Current directory for now, or "data" if we move it
HISTORY_FILE_NAME = "naver_land_history.csv"
PREVIOUS_FILE_NAME = "last_min_prices.csv"
PRICE_DROPS_FILE = "price_drops.txt"
