
# Google Chat Webhook URL
GOOGLE_CHAT_WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAQAcDkeJSk/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=sBgQytan3_5KMuaP3xUyCSzAIw0LkfjIesu0JVx9bxY"

# Target Complex Numbers
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
    'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3NzE0NjUyMTcsImV4cCI6MTc3MTQ3NjAxN30.YCe8rsZRzzWUO5C35UsU70Hk5AQxd4NmXAc9pOxsAQA',
    'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

# Request Cookies
COOKIES = {
    'NAC': 'XTpmB4wGHIcK',
    'NNB': 'DRATSR75NQXGS',
    '_fbp': 'fb.1.1765523765531.204862808283532169',
    'tooltipDisplayed': 'true',
    '_ga': 'GA1.1.1207086872.1769042712',
    '_ga_451MFZ9CFM': 'GS2.1.s1769042712$o1$g1$t1769042724$j48$l0$h0',
    'ASID': '7983d88a0000019c2788fa5100000026',
    'cto_bundle': 'i-H5M19qUiUyQjgzZVpIY0lCTmx4a3JpOTZUcWElMkJQZXNrJTJCTUxFVnlVNXcwUCUyQkRPREM1MWZvdDNSQlJCJTJGT0VrTDZDcklkaXI3OUNEdGxMUGdsQyUyQk9GWVFvUFRUbSUyRm0yOGFmelpWbmx4JTJCSDRnWmdCYlRrRWd6NkFVTXFUSFBYTnY4c2VTZUQ0eUZJam4yaHFJTGdxU3psYXlqaERBJTNEJTNE',
    '_fwb': '180AC7rVNBNrSgBYjwKE2Bc.1771460153879',
    'NACT': '1',
    'nhn.realestate.article.rlet_type_cd': 'A01',
    'nhn.realestate.article.ipaddress_city': '4100000000',
    'landHomeFlashUseYn': 'Y',
    'SRT30': '1771474930',
    'REALESTATE': 'Thu%20Feb%2019%202026%2010%3A54%3A15%20GMT%2B0900%20(Korean%20Standard%20Time)',
    'PROP_TEST_KEY': '1771466055709.1ed40b39ecafda3d14f855af91db26089ed148ae25eebadcbaaa86f36223dd48',
    'PROP_TEST_ID': 'fa3a4b5d90b780de5d4800ae6f69e8bf95f705a274e4c5ed7f021bcf006d8a4e',
    'page_uid': 'jiiWqlqXKZzba6G0dbR-092345',
    'SRT30': '1771474930',
    'BUC': 'j3ZBpvWz7EInsWPjx8O_t0R8WPP2Bg4VuCjgQzAWFaw=',
}

# File Paths
DATA_DIR = "."  # Current directory for now, or "data" if we move it
HISTORY_FILE_NAME = "naver_land_history.csv"
PREVIOUS_FILE_NAME = "last_min_prices.csv"
PRICE_DROPS_FILE = "price_drops.txt"
