import sys
import time
import json
import os
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QHBoxLayout, QWidget, QTextEdit, QTabWidget, 
                             QLabel, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QDateEdit, QGroupBox)
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop, QTimer, QDate, QTime, pyqtSignal, QObject
from telegram_manager import TelegramManager

class KiwoomApp(QMainWindow):
    # Cross-thread signals
    log_signal = pyqtSignal(str)
    remote_add_signal = pyqtSignal(str, str, int)
    remote_del_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kiwoom OpenAPI+ Pro (자동매매 엔진 V3 🚀)")
        self.setGeometry(200, 200, 1150, 750)
        
        self.kiwoom = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        
        # OpenAPI Events
        self.kiwoom.OnEventConnect.connect(self.event_connect)
        self.kiwoom.OnReceiveTrData.connect(self.receive_tr_data)
        self.kiwoom.OnReceiveRealData.connect(self.receive_real_data)
        
        # Condition Search Events
        self.kiwoom.OnReceiveConditionVer.connect(self.receive_condition_ver)
        self.kiwoom.OnReceiveTrCondition.connect(self.receive_tr_condition)
        self.kiwoom.OnReceiveRealCondition.connect(self.receive_real_condition)
        self.kiwoom.OnReceiveChejanData.connect(self.receive_chejan_data)
        
        self.login_event_loop = None
        self.tr_event_loop = None
        self.balance_event_loop = None # [추가] 실시간 잔고 확인용 루프
        self.last_synced_balance = 0   # [추가] 실시간 잔고 확인 결과 저장용
        
        # State Variables
        self.account_num = ""
        self.condition_dict = {}     
        self.initial_money = 0       # 기준 원금 (최초 D+2 예수금)
        self.available_money = 0     # 실시간 남은 매매가능 예수금
        
        # Auto Trading State
        self.target_condition_name = "상한가 양봉"
        self.api_queue = []          
        self.is_processing_tr = False
        
        self.target_stocks = {}      # dict[str, dict]
        self.ordered_stocks = {}     # dict[str, dict]
        self.held_stock_codes = set() # set[str]
        
        # TR Limitation Safe Queue Processor
        self.api_timer = QTimer()
        self.api_timer.timeout.connect(self.process_api_queue)
        self.api_timer.start(333) # 0.33초 (초당 3회 요청으로 안정성 확보)
        
        # Telegram Bot
        self.telegram_manager = None
        self.telegram_token = ""
        self.telegram_chat_id = ""
        self.is_telegram_enabled = False
        
        # Connect Signals
        self.log_signal.connect(self._log_slot)
        self.remote_add_signal.connect(self.process_remote_add)
        self.remote_del_signal.connect(self.process_remote_del)
        
        self.setup_ui()

    # ==========================
    # UI Setup
    # ==========================
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()

        # Top Bar (Login, Account, Deposit)
        top_layout = QHBoxLayout()
        self.btn_login = QPushButton("로그인")
        self.btn_login.clicked.connect(self.login)
        top_layout.addWidget(self.btn_login)

        top_layout.addWidget(QLabel("계좌선택:"))
        self.combo_account = QComboBox()
        self.combo_account.currentIndexChanged.connect(self.change_account)
        top_layout.addWidget(self.combo_account)
        
        self.lbl_deposit = QLabel("매매가능 예수금: - 원")
        top_layout.addWidget(self.lbl_deposit)
        
        main_layout.addLayout(top_layout)

        # Tabs
        self.tabs = QTabWidget()
        self.tab_balance = QWidget()
        self.tab_autotrade = QWidget()

        self.tabs.addTab(self.tab_balance, "1. 계좌 보유종목")
        self.tabs.addTab(self.tab_autotrade, "2. 조건검색 자동매매 (6분할 타점매수 / 3% 자동익절)")
        
        self.tab_settings = QWidget()
        self.tab_settings.setObjectName("tab_settings")
        self.tabs.addTab(self.tab_settings, "3. 설정 (텔레그램/알림)")
        
        main_layout.addWidget(self.tabs)

        self.setup_tab_balance()
        self.setup_tab_autotrade()
        self.setup_tab_settings()

        # Global Log
        queue_layout = QHBoxLayout()
        queue_layout.addWidget(QLabel("현재 포착된 종목 대기열 (Queue):"))
        self.lbl_queue_status = QLabel("없음")
        self.lbl_queue_status.setStyleSheet("color: blue; font-weight: bold;")
        queue_layout.addWidget(self.lbl_queue_status)
        main_layout.addLayout(queue_layout)

        main_layout.addWidget(QLabel("시스템 로그 (Log):"))
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(180)
        self.log_text.setReadOnly(True)
        main_layout.addWidget(self.log_text)

        central_widget.setLayout(main_layout)

    def log(self, message):
        """Public log interface (thread-safe)"""
        timestamp = QTime.currentTime().toString("HH:mm:ss")
        full_msg = f"[{timestamp}] {message}"
        if threading.current_thread() is not threading.main_thread():
            self.log_signal.emit(full_msg)
        else:
            self._log_slot(full_msg)

    def _log_slot(self, message):
        """Actual UI logging (Main thread only)"""
        self.log_text.append(message)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        # Also print to terminal for easier debugging
        print(message)

    # --- Tab 1 ---
    def setup_tab_balance(self):
        layout = QVBoxLayout()
        self.btn_check_balance = QPushButton("보유종목 및 예수금 새로고침")
        self.btn_check_balance.clicked.connect(self.check_balance)
        self.btn_check_balance.setEnabled(False)
        layout.addWidget(self.btn_check_balance)

        self.table_balance = QTableWidget()
        self.table_balance.setColumnCount(5)
        self.table_balance.setHorizontalHeaderLabels(["종목명", "보유수량", "매입가", "현재가", "수익률(%)"])
        self.table_balance.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table_balance)
        self.tab_balance.setLayout(layout)

    # --- Tab 2 (Auto Trading) ---
    def setup_tab_autotrade(self):
        layout = QVBoxLayout()
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel(f"연동 조건명: [{self.target_condition_name}] | 최대 2종목 보유 | 6분할 매수 | 3% 이상 즉시 전량 매도"))
        
        self.btn_trade_start = QPushButton("🚀 조건검색 자동매매 AI 가동 시작")
        self.btn_trade_start.clicked.connect(self.start_auto_trade)
        self.btn_trade_stop = QPushButton("정지")
        self.btn_trade_stop.clicked.connect(self.stop_auto_trade)
        
        input_layout.addWidget(self.btn_trade_start)
        input_layout.addWidget(self.btn_trade_stop)
        layout.addLayout(input_layout)

        manual_layout = QHBoxLayout()
        manual_layout.addWidget(QLabel("수동 종목명/코드:"))
        self.input_manual_code = QLineEdit()
        self.input_manual_code.setPlaceholderText("예: 삼성전자 또는 005930")
        manual_layout.addWidget(self.input_manual_code)

        manual_layout.addWidget(QLabel("기준일자:"))
        self.input_manual_date = QDateEdit()
        self.input_manual_date.setCalendarPopup(True)
        today = QDate.currentDate()
        self.input_manual_date.setDateRange(today.addMonths(-6), today)
        self.input_manual_date.setDate(today)
        self.input_manual_date.setDisplayFormat("yyyy-MM-dd")
        self.input_manual_date.setStyleSheet("QDateEdit { min-width: 100px; }")
        manual_layout.addWidget(self.input_manual_date)
        
        self.combo_target_type = QComboBox()
        self.combo_target_type.addItems(["종가/시가 둘다 (6분할)", "종가만 (3분할)", "시가만 (3분할)"])
        manual_layout.addWidget(self.combo_target_type)

        self.btn_manual_add = QPushButton("수동 타점 등록")
        self.btn_manual_add.clicked.connect(self.add_manual_stock)
        manual_layout.addWidget(self.btn_manual_add)
        
        layout.addLayout(manual_layout)

        self.table_autotrade = QTableWidget()
        self.table_autotrade.setColumnCount(10)
        self.table_autotrade.setHorizontalHeaderLabels(["구분", "종목명", "종목코드", "기준일자(발생일)", "기준가(고가/종가)", "시가", "거래대금(백만)", "진행 분할차수", "현재 시스템 상태", "관리(삭제)"])
        self.table_autotrade.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table_autotrade)
        self.tab_autotrade.setLayout(layout)

    # --- Tab 3 (Settings) ---
    def setup_tab_settings(self):
        layout = QVBoxLayout()
        
        # Group Box for Telegram
        group = QGroupBox("📢 텔레그램 연동 및 원격 제어")
        group_layout = QVBoxLayout()
        
        token_layout = QHBoxLayout()
        token_lbl = QLabel("봇 토큰(Token):")
        token_lbl.setFixedWidth(100)
        token_layout.addWidget(token_lbl)
        self.edit_telegram_token = QLineEdit()
        self.edit_telegram_token.setEchoMode(QLineEdit.Password)
        self.edit_telegram_token.setPlaceholderText("봇 토큰을 입력하세요")
        token_layout.addWidget(self.edit_telegram_token)
        group_layout.addLayout(token_layout)
        
        chat_id_layout = QHBoxLayout()
        chat_id_lbl = QLabel("채팅 ID(ChatID):")
        chat_id_lbl.setFixedWidth(100)
        chat_id_layout.addWidget(chat_id_lbl)
        self.edit_telegram_chat_id = QLineEdit()
        self.edit_telegram_chat_id.setPlaceholderText("숫자로 된 Chat ID를 입력하세요")
        chat_id_layout.addWidget(self.edit_telegram_chat_id)
        group_layout.addLayout(chat_id_layout)
        
        self.btn_telegram_toggle = QPushButton("텔레그램 봇 가동 시작")
        self.btn_telegram_toggle.setFixedHeight(40)
        self.btn_telegram_toggle.setStyleSheet("background-color: #e1f5fe; font-weight: bold;")
        self.btn_telegram_toggle.clicked.connect(self.toggle_telegram)
        group_layout.addWidget(self.btn_telegram_toggle)
        
        help_lbl = QLabel("\n* 원격 명령 지원: /add 삼성전자, /status, /start\n* 매수/매도 실시간 푸시 알림이 발송됩니다.")
        help_lbl.setStyleSheet("color: gray;")
        group_layout.addWidget(help_lbl)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
        layout.addStretch()
        self.tab_settings.setLayout(layout)

    def toggle_telegram(self):
        if self.telegram_manager and self.telegram_manager.is_running:
            self.telegram_manager.stop()
            self.is_telegram_enabled = False
            self.btn_telegram_toggle.setText("텔레그램 봇 가동 시작")
            self.log("📴 텔레그램 봇이 정지되었습니다.")
        else:
            token = self.edit_telegram_token.text().strip()
            chat_id = self.edit_telegram_chat_id.text().strip()
            
            if not token or not chat_id:
                self.log("⚠️ 텔레그램 토큰과 Chat ID를 먼저 입력해주세요.")
                return
            
            self.telegram_token = token
            self.telegram_chat_id = chat_id
            self.telegram_manager = TelegramManager(
                token, chat_id, 
                add_callback=self.handle_remote_add,
                list_callback=self.handle_remote_list,
                del_callback=self.handle_remote_del
            )
            self.telegram_manager.start()
            self.is_telegram_enabled = True
            self.btn_telegram_toggle.setText("텔레그램 봇 정지")
            self.log("🚀 텔레그램 봇이 가동되었습니다. 이제 실시간 알림을 받을 수 있습니다.")
            self.telegram_manager.send_message("✅ Kiwoom 앱과 텔레그램 봇이 성공적으로 연결되었습니다.")
            self.save_state()

    def handle_remote_add(self, stock_info, target_date, target_type):
        """Telegram에서 전달된 종목 추가 요청 처리 (Bot 스레드에서 호출됨)"""
        self.log(f"📱 [원격수신] {stock_info}, {target_date}, 타입:{target_type}")
        # 시그널을 통해 메인 스레드로 데이터 전달
        self.remote_add_signal.emit(stock_info, target_date, target_type)

    def handle_remote_list(self):
        """Telegram에서 종목 리스트 요청 시 처리 (Bot 스레드)"""
        # [안전] 딕셔너리 복사본으로 순회하여 스레드 간 충돌(Size Change) 방지
        target_copy = dict(self.target_stocks)
        if not target_copy:
            return "현재 감시 중인 종목이 없습니다."
        
        msg = "📋 **현재 감시/보유 종목 리스트**\n\n"
        for code, data in target_copy.items():
            name = data.get('name', '미확인')
            date = data.get('date', '00000000')
            config = data.get('config', 0)
            c_name = "6분할" if config == 0 else ("종가3" if config == 1 else "시가3")
            
            # 보유 상태 확인 (읽기 전용이므로 직접 접근하되 딕셔너리 구조 유의)
            st = self.ordered_stocks.get(code)
            qty = st['total_qty'] if (isinstance(st, dict) and 'total_qty' in st) else 0
            avg = st['avg_price'] if (isinstance(st, dict) and 'avg_price' in st) else 0
            h_count = len(st['hit_levels']) if (isinstance(st, dict) and 'hit_levels' in st) else 0
            
            msg += f"🔹 **{name}({code})**\n"
            msg += f"   - 기준: {date} ({c_name})\n"
            msg += f"   - 상태: {qty}주 보유 (평균 {avg:,}원 / {h_count}차 매수)\n\n"
        return msg

    def handle_remote_del(self, stock_info):
        """Telegram에서 종목 삭제 요청 시 처리 (Bot 스레드)"""
        # 시그널을 통해 메인 스레드로 전달 (COM 객체 접근 방지)
        self.remote_del_signal.emit(stock_info)
        return f"✅ {stock_info} 삭제 요청을 앱으로 전달했습니다. 결과를 확인하세요."

    def process_remote_del(self, stock_info):
        """삭제 요청 실제 처리 (메인 스레드)"""
        code = stock_info
        if not stock_info.isdigit() or len(stock_info) != 6:
            code = self.get_code_from_name(stock_info)
            if not code:
                self.log(f"❌ [원격삭제 실패] '{stock_info}' 종목을 찾을 수 없습니다.")
                return
        
        if code not in self.target_stocks:
            self.log(f"❌ [원격삭제 실패] {stock_info}({code}) 종목이 감시 리스트에 없습니다.")
            return
            
        name = self.kiwoom.dynamicCall("GetMasterCodeName(QString)", code)
        self.manual_delete_stock(code)
        self.log(f"🗑️ [원격삭제 완료] {name}({code}) 종목이 삭제되었습니다.")

    def process_remote_add(self, stock_info, target_date, target_type):
        self.log(f"⚙️ [원격처리] {stock_info} 필드 세팅 중...")
        # UI 업데이트 (사용자 확인용)
        self.input_manual_code.setText(stock_info)
        qdate = QDate.fromString(target_date, "yyyyMMdd")
        if qdate.isValid():
            self.input_manual_date.setDate(qdate)
        if 0 <= target_type <= 2:
            self.combo_target_type.setCurrentIndex(target_type)
            
        self.add_manual_stock_logic(stock_info, target_date, target_type)

    def add_manual_stock(self):
        """GUI 버튼 클릭 시 호출"""
        code_or_name = self.input_manual_code.text().strip()
        date_str = self.input_manual_date.date().toString("yyyyMMdd")
        trigger_config = self.combo_target_type.currentIndex()
        self.add_manual_stock_logic(code_or_name, date_str, trigger_config)

    def add_manual_stock_logic(self, input_text, date_str, trigger_config):
        """실제 등록 로직 (GUI/원격 공통)"""
        if not input_text:
            self.log("⚠️ 종목 정보를 확인해주세요.")
            return
            
        code = input_text
        if not input_text.isdigit() or len(input_text) != 6:
            self.log(f"🔍 '{input_text}' 종목명으로 코드 검색 중...")
            code = self.get_code_from_name(input_text)
            if not code:
                self.log(f"❌ [에러] '{input_text}' 종목명을 찾을 수 없습니다. (로그인 필수/종목명 확인)")
                if self.telegram_manager:
                    self.telegram_manager.send_message(f"❌ [등록실패] {input_text} 종목명을 찾을 수 없습니다.")
                return
            self.log(f"✅ 코드 변환 성공: {input_text} -> {code}")
            
        if self.is_in_queue(code) or code in self.target_stocks:
            self.log(f"⚠️ 이미 리스트에 존재하거나 대기 중입니다: {code}")
            return
            
        self.api_queue.append({'code': code, 'type': 'manual', 'date': date_str, 'config': trigger_config})
        self.log(f"🚀 {code} 종목이 TR 요청 대기열(Queue)에 추가되었습니다.")
        
        config_names = ["종가+시가 6분할", "종가 3분할", "시가 3분할"]
        c_name = config_names[trigger_config] if trigger_config < len(config_names) else str(trigger_config)
        
        name = self.kiwoom.dynamicCall("GetMasterCodeName(QString)", code)
        self.log(f"📝 [대기열 등록] {name}({code}), 일자:{date_str}, {c_name}")
        self.update_queue_ui()
        
        self.input_manual_code.clear()

    # ==========================
    # State Persistence (JSON)
    # ==========================
    def get_state_filepath(self):
        return os.path.join(os.getcwd(), "kiwoom_state.json")

    def save_state(self):
        state_ordered = {}
        for k, v in self.ordered_stocks.items():
            copied = dict(v)
            copied['hit_levels'] = list(copied['hit_levels'])
            state_ordered[k] = copied

        state_data = {
            "target_stocks": self.target_stocks,
            "ordered_stocks": state_ordered,
            "held_stock_codes": list(self.held_stock_codes),
            "telegram_token": self.telegram_token,
            "telegram_chat_id": self.telegram_chat_id,
            "is_telegram_enabled": self.is_telegram_enabled
        }
        with open(self.get_state_filepath(), "w", encoding="utf-8") as f:
            json.dump(state_data, f, ensure_ascii=False, indent=4)

    def load_state(self):
        filepath = self.get_state_filepath()
        if not os.path.exists(filepath): return
            
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                state_data = json.load(f)
                self.target_stocks = state_data.get("target_stocks", {})
                state_ordered = state_data.get("ordered_stocks", {})
                self.held_stock_codes = set(state_data.get("held_stock_codes", []))
                
                self.ordered_stocks = {}
                for k, v in state_ordered.items():
                    if not isinstance(v, dict): continue
                    copied = dict(v)
                    # hit_levels가 리스트로 저장되어 있으므로 set으로복구
                    h_lv = copied.get('hit_levels', [])
                    copied['hit_levels'] = set(h_lv) if isinstance(h_lv, list) else set()
                    self.ordered_stocks[k] = copied
                
                self.table_autotrade.setRowCount(0)
                for code, data in self.target_stocks.items():
                    date_fmt = f"{data['date'][:4]}-{data['date'][4:6]}-{data['date'][6:]}"
                    val_fmt = format(data.get('val', 0), ",")
                    config = data.get('config', 0)
                    config_name = "종가+시가 6분할" if config == 0 else ("종가 3분할" if config == 1 else "시가 3분할")
                    
                    # [Fix] 린트 오류 방지를 위해 딕셔너리 접근을 안전하게 처리
                    stock_data = self.ordered_stocks.get(code)
                    hit_levels = stock_data.get('hit_levels', set()) if isinstance(stock_data, dict) else set()
                    hit_count = len(hit_levels)
                    
                    if hit_count > 0:
                        status = f"🟢 {hit_count}차 분할매수 재연결"
                    else:
                        status = f"👀 파일 로드 복원됨 ({config_name})"
                        
                    self.add_autotrade_row(data.get('list_type', '자동'), data.get('name', ''), code, date_fmt, f"{data['close']:,}", f"{data['open']:,}", val_fmt, str(hit_count), status)
                    self.kiwoom.dynamicCall("SetRealReg(QString, QString, QString, QString)", "3000", code, "10;11;12", "1")
                    
                self.log(f"💾 시스템 상태({len(self.target_stocks)}종목)를 파일에서 복원했습니다.")
                
                # Telegram Settings Restore
                self.telegram_token = state_data.get("telegram_token", "")
                self.telegram_chat_id = state_data.get("telegram_chat_id", "")
                self.is_telegram_enabled = state_data.get("is_telegram_enabled", False)
                
                self.edit_telegram_token.setText(self.telegram_token)
                self.edit_telegram_chat_id.setText(self.telegram_chat_id)
                
                if self.is_telegram_enabled:
                    # 자동 시작 (사용자 경험 향상)
                    QTimer.singleShot(1000, self.toggle_telegram)
            except Exception as e:
                self.log(f"⚠️ 상태 파일 로드 실패: {str(e)}")

    # ==========================
    # OpenAPI Connection & Core
    # ==========================
    def login(self):
        self.log("로그인 연결 시도 중...")
        self.kiwoom.dynamicCall("CommConnect()")
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()

    def event_connect(self, err_code):
        if err_code == 0:
            self.log("로그인 성공!")
            acc_list = self.kiwoom.dynamicCall("GetLoginInfo(\"ACCNO\")")
            accounts = [a.strip() for a in acc_list.split(';') if a.strip()]
            self.combo_account.addItems(accounts)
            
            # [추가] 서버 구분 (실전/모의) 확인
            server_gubun = self.kiwoom.dynamicCall("GetLoginInfo(QString)", "GetServerGubun")
            server_str = "모의투자" if server_gubun == "1" else "실전투자"
            self.log(f"🔎 접속 성공! (서버: {server_str})")
            self.log(f"📋 발견된 전체 계좌 목록: {accounts}")
            
            # [강제] 특정 계좌번호(6050325010)만 사용하도록 고정
            target_acc = next((acc for acc in accounts if "6050325010" in acc), None)
            if target_acc:
                idx = self.combo_account.findText(target_acc)
                if idx >= 0:
                    self.combo_account.setCurrentIndex(idx)
                self.account_num = target_acc
                self.log(f"✅ 사용 계좌: {target_acc} (6050325010 전전용 계좌 강제 지정됨)")
            else:
                self.log(f"❌ [심각] 6050325010 계좌를 찾을 수 없습니다! 현재 접속된 계좌들: {accounts}")
                # 일단 첫 번째 계좌를 할당하되, 사용자에게 강력 경고
                if accounts:
                    self.account_num = accounts[0]
                    self.log(f"⚠️ 임시로 첫 번째 계좌({self.account_num})를 선택했으나, 오작동 가능성이 큽니다!")

            if accounts:
                self.btn_check_balance.setEnabled(True)
                self.fetch_deposit(is_initial=True) # 초기 예수금을 원금으로 고정
                
            self.log("사용자 조건검색식 목록 로드 중...")
            self.kiwoom.dynamicCall("GetConditionLoad()")
            
            # 로그인 성공 후 로컬 상태 복원
            self.load_state()
            
            # [추가] 로그인 성공 2초 후 상시 잔고 동기화 (기존 파일의 잘못된 수량 자동 보정용)
            QTimer.singleShot(2000, self.check_balance)
        else:
            self.log(f"로그인 실패 (에러코드: {err_code})")
            
        if self.login_event_loop:
            self.login_event_loop.exit()

    def change_account(self):
        self.account_num = self.combo_account.currentText()
        self.log(f"계좌 변경됨: {self.account_num}")
        self.fetch_deposit(is_initial=True)

    def fetch_deposit(self, is_initial=False):
        self.is_initial_deposit_fetch = is_initial
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_num)
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "비밀번호", "")
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "비밀번호입력매체구분", "00")
        # 조회구분 3: 추정조회 (D+2 예수금 등 추정 데이터 포함)
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "조회구분", "3") 
        self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", "예수금조회", "opw00001", 0, "2000")

    def check_balance(self):
        self.fetch_deposit(is_initial=False)
        # TR 연속 호출 시 오류 방지를 위해 0.5초 뒤에 잔고조회 수행
        QTimer.singleShot(500, self._check_balance_tr)

    def _check_balance_tr(self):
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_num)
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "비밀번호", "")
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "비밀번호입력매체구분", "00")
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "조회구분", "1")
        self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", "계좌잔고조회", "opw00018", 0, "1000")

    def get_balance_sync(self, target_code):
        """
        [핵심] 키움 서버에 현재 실제 매도 가능한 주식수를 '동기 방식'으로 즉시 조회합니다.
        로컬에 저장된 수량을 믿지 않고, TR을 날려 응답이 올 때까지 대기(Block)합니다.
        """
        self.log(f"🔍 [서버 조회 시작] 종목: {target_code} | 계좌: {self.account_num}")
        self.last_synced_balance = 0
        
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_num)
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "비밀번호", "")
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "비밀번호입력매체구분", "00")
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "조회구분", "1")
        
        # 고유한 rqname을 사용하여 다른 TR과 섞이지 않게 함
        rqname = f"실시간잔고확약_{target_code}"
        
        # [Fix] AttributeError 방지: TR 요청 전에 필요한 속성들을 명시적으로 초기화
        self._found_target_qty_sync = 0
        self._all_codes_log = []
        
        res = self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", rqname, "opw00018", 0, "5001")
        if res != 0:
            self.log(f"❌ [에러] 잔고 조회 TR 요청 실패: {res}")
            return 0
        
        self.balance_event_loop = QEventLoop()
        
        # [추가] 5초 타임아웃 설정 (서버 응답 없을 경우 무한 대기 방지)
        def on_timeout():
            if self.balance_event_loop and self.balance_event_loop.isRunning():
                self.log(f"⚠️ [타임아웃] {target_code} 잔고 조회 응답이 5초간 없어 조회를 중단합니다.")
                self.balance_event_loop.exit()
                
        QTimer.singleShot(5000, on_timeout)
        
        self.balance_event_loop.exec_() # OnReceiveTrData에서 exit 시켜줄 때까지 여기서 대기
        
        self.log(f"🔍 [서버 조회 완료] {target_code} 결과: {self.last_synced_balance}주")
        return self.last_synced_balance

    # ==========================
    # API Queue Processing (Limit Safe)
    # ==========================
    def update_queue_ui(self):
        if not self.api_queue:
            self.lbl_queue_status.setText("없음")
        else:
            names = []
            for item in self.api_queue:
                code = item['code'] if isinstance(item, dict) else item
                name = self.kiwoom.dynamicCall("GetMasterCodeName(QString)", code)
                names.append(f"{name}({code})")
            self.lbl_queue_status.setText(" | ".join(names))

    def get_code_from_name(self, target_name):
        target_name = target_name.strip()
        for market in ["0", "10"]:
            codes_str = self.kiwoom.dynamicCall("GetCodeListByMarket(QString)", market)
            if not codes_str: 
                continue
            codes = codes_str.split(";")
            for c in codes:
                c = c.strip()
                if c:
                    name = self.kiwoom.dynamicCall("GetMasterCodeName(QString)", c)
                    if name.strip() == target_name:
                        return c
        return None

    def is_in_queue(self, code):
        for item in self.api_queue:
            q_code = item['code'] if isinstance(item, dict) else item
            if q_code == code: return True
        return False


    def process_api_queue(self):
        # [추가] TR 대기 루프 중(Block)에는 큐 처리를 중단하여 TR 꼬임 방지
        if (self.login_event_loop and self.login_event_loop.isRunning()) or \
           (self.balance_event_loop and self.balance_event_loop.isRunning()):
            return
            
        if self.api_queue and not self.is_processing_tr:
            item = self.api_queue.pop(0)
            code = item['code'] if isinstance(item, dict) else item
            req_type = item['type'] if isinstance(item, dict) else 'auto'
            target_date = item.get('date', '') if isinstance(item, dict) else ''
            
            self.is_processing_tr = True
            name = self.kiwoom.dynamicCall("GetMasterCodeName(QString)", code)
            
            if req_type == 'manual':
                trigger_config = item.get('config', 0)
                self.log(f"[TR큐] {name} ({code}) 수동 타점({target_date}) 분석 TR 요청...")
                self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
                self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
                self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", f"수동스캔_{code}_{target_date}_{trigger_config}", "opt10081", 0, "1005")
            else:
                self.log(f"[TR큐] {name} ({code}) 과거 데이터 분석 TR 요청...")
                self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
                self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
                self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", f"오토스캔_{code}", "opt10081", 0, "1004")
            
            self.update_queue_ui()

    # ==========================
    # TR & Real-time Event Routines
    # ==========================
    def receive_tr_data(self, screen_no, rqname, trcode, record_name, next_val, reserved1, reserved2, reserved3, reserved4):
        if rqname == "예수금조회":
            # ... (기존 코드)
            pass # Replacement handle handles specific section below

        elif rqname == "계좌잔고조회" or rqname.startswith("실시간잔고확약_"):
            # ...
            pass
        if rqname == "예수금조회":
            deposit = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "d+2추정예수금").strip()
            if not deposit or not deposit.replace('-','').isdigit() or int(deposit) == 0:
                deposit_alt = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "출금가능금액").strip()
                if deposit_alt and deposit_alt.replace('-','').isdigit() and int(deposit_alt) > 0:
                    deposit = deposit_alt
            
            val = int(deposit) if deposit and deposit.replace('-','').isdigit() else 0
            self.available_money = val
            if hasattr(self, 'is_initial_deposit_fetch') and self.is_initial_deposit_fetch:
                self.initial_money = val
                self.log(f"초기 원금 세팅: {self.initial_money:,}원")
                self.is_initial_deposit_fetch = False
            self.lbl_deposit.setText(f"매매가능 잉여 예수금: {self.available_money:,} 원")
            
        elif rqname == "계좌잔고조회" or rqname.startswith("실시간잔고확약_"):
            is_sync_check = rqname.startswith("실시간잔고확약_")
            target_code = rqname.split("_")[1] if is_sync_check else None
            cnt = self.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
            
            # 초기화 처리 (첫 페이지)
            if not is_sync_check and not hasattr(self, '_held_codes_buffer'):
                self.table_balance.setRowCount(0)
                self._held_codes_buffer = set()
                self._all_codes_log = []
            elif is_sync_check:
                if not hasattr(self, '_all_codes_log'):
                    self._all_codes_log = []
                if not hasattr(self, '_found_target_qty_sync'):
                    self._found_target_qty_sync = 0
                self.log(f"🔍 [서버응답 수신] {rqname} 분석 중 (계좌: {self.account_num}, 레코드: {cnt})")

            for i in range(cnt):
                code = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "종목번호").strip().replace('A', '')
                name = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "종목명").strip()
                qty = int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "보유수량").strip() or 0)
                buy = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "매입가").strip() or 0))
                cur = abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "현재가").strip() or 0))
                rate = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "수익률(%)").strip()
                
                self._all_codes_log.append(f"{name}({code})")
                if is_sync_check and code == target_code:
                    self._found_target_qty_sync = qty

                # 봇 매니징 필터링 (140410 문제 해결)
                is_managed = (code in self.ordered_stocks) or (code in self.target_stocks)
                if is_managed:
                    if code not in self.ordered_stocks:
                        self.ordered_stocks[code] = {
                            'avg_price': buy, 'total_qty': qty, 'total_invested': qty * buy, 
                            'hit_levels': set(), 'sold': False, 'trade_count': 1,
                            'pending_sell': False,
                            'pending_buy': False # [추가] 중복 매수 방지 플래그
                        }
                    else:
                        st = self.ordered_stocks[code]
                        if isinstance(st, dict):
                            st.update({'total_qty': qty, 'avg_price': buy, 'total_invested': qty * buy})
                            if 'pending_sell' not in st: st['pending_sell'] = False
                            if 'pending_buy' not in st: st['pending_buy'] = False
                    if qty > 0:
                        self.kiwoom.dynamicCall("SetRealReg(QString, QString, QString, QString)", "3000", code, "10;11;12", "1")
                        self.held_stock_codes.add(code)
                
                if not is_sync_check:
                    self._held_codes_buffer.add(code)
                    curr_row = self.table_balance.rowCount()
                    self.table_balance.insertRow(curr_row)
                    rate_val = f"{float(rate)/100:.2f}" if rate.replace('.','',1).replace('-','',1).isdigit() else rate
                    self.table_balance.setItem(curr_row, 0, QTableWidgetItem(name))
                    self.table_balance.setItem(curr_row, 1, QTableWidgetItem(str(qty)))
                    self.table_balance.setItem(curr_row, 2, QTableWidgetItem(str(buy)))
                    self.table_balance.setItem(curr_row, 3, QTableWidgetItem(str(cur)))
                    self.table_balance.setItem(curr_row, 4, QTableWidgetItem(rate_val))

            if next_val == '2':
                self.log(f"📄 잔고 조회 다음 페이지 요청 중... (현재 {len(self._all_codes_log)}개 발견)")
                self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", rqname, trcode, 2, "1000" if not is_sync_check else "5001")
                return

            if is_sync_check:
                self.last_synced_balance = self._found_target_qty_sync
                if self.last_synced_balance == 0:
                    self.log(f"❓ [조회 완료] {target_code}를 찾지 못했습니다. 계좌 내 전체 종목({len(self._all_codes_log)}개): {self._all_codes_log}")
                if hasattr(self, '_found_target_qty_sync'): del self._found_target_qty_sync
                if hasattr(self, '_all_codes_log'): del self._all_codes_log
                if self.balance_event_loop: self.balance_event_loop.exit()
            else:
                self.log(f"✅ 잔고 조회 완료 (총 {len(self._held_codes_buffer)}개 종목 보유 중)")
                
                # [강력 조치] 현재 계좌에 실제로 없는 '고스트 종목' 과감히 제거
                # ordered_stocks(운영 대상)에서 계좌에 실물 수량이 0인 종목들 정리
                for code in list(self.ordered_stocks.keys()):
                    if code not in self._held_codes_buffer:
                        # target_stocks(감시 설정)에 없다면 아예 삭제, 있다면 수량만 0으로 업데이트
                        if code not in self.target_stocks:
                            self.log(f"🗑️ [정리] 타 계좌 혹은 매도 완료된 고스트 종목 제거: {code}")
                            del self.ordered_stocks[code]
                        else:
                            self.ordered_stocks[code].update({'total_qty': 0, 'avg_price': 0, 'total_invested': 0})
                        
                        if code in self.held_stock_codes: 
                            self.held_stock_codes.remove(code)
                
                if hasattr(self, '_held_codes_buffer'): del self._held_codes_buffer
                if hasattr(self, '_all_codes_log'): del self._all_codes_log
            
            # [추가] 모든 TR 요청에 대해 처리 완료 플래그 리셋
            self.is_processing_tr = False
                
            
        elif rqname.startswith("오토스캔_") or rqname.startswith("수동스캔_"):
            print(f"DEBUG: TR Received - rqname: {rqname}, trcode: {trcode}")
            parts = rqname.split("_")
            scan_type = parts[0]
            code = parts[1]
            target_date = parts[2] if len(parts) > 2 else None

            cnt = self.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
            name = self.kiwoom.dynamicCall("GetMasterCodeName(QString)", code)
            
            if scan_type == "오토스캔":
                if cnt >= 30:
                    self.run_autotrade_algorithm("자동", name, code, trcode, rqname, cnt)
            elif scan_type == "수동스캔":
                trigger_config = int(parts[3]) if len(parts) > 3 else 0
                self.run_manual_algorithm("수동", name, code, target_date, trigger_config, trcode, rqname, cnt)
            
            self.is_processing_tr = False

    def receive_chejan_data(self, gubun, item_cnt, fid_list):
        """
        체결/잔고 데이터를 수신하는 이벤트
        gubun: 0(주문체결), 1(잔고통보), 3(특이신호)
        """
        # [보강] 계좌번호 확인 (FID 9201). 타 계좌 주문/잔고 신호는 무시
        fid_acc = self.kiwoom.dynamicCall("GetChejanData(int)", 9201).strip()
        if fid_acc and self.account_num and fid_acc != self.account_num:
            # 타 계좌 신호인 경우 로그 없이 조용히 무시 (사용자 혼란 방지)
            return

        code = self.kiwoom.dynamicCall("GetChejanData(int)", 9001).strip().replace('A', '') # 종목코드
        if code == "140410": return # [강제 블랙리스트] 한샘(140410)은 일절 관여 안함
        
        name = self.kiwoom.dynamicCall("GetChejanData(int)", 302).strip() # 종목명
        
        if gubun == '0': # 주문체결 (가장 중요: 실시간 체결 시 수량/단가 업데이트)
            order_status = self.kiwoom.dynamicCall("GetChejanData(int)", 913).strip() # 주문상태 (접수, 체결)
            if order_status == "체결":
                fill_qty = int(self.kiwoom.dynamicCall("GetChejanData(int)", 911).strip() or 0) # 체결량
                fill_price = int(self.kiwoom.dynamicCall("GetChejanData(int)", 910).strip() or 0) # 체결가
                
                if code in self.ordered_stocks:
                    # 체결 잔고 TR(opw00018)을 매번 호출하기엔 TR 제한이 있으므로, 체결 신호를 통해 내부 상태를 간접 업데이트
                    # 하지만 가장 정확한 것은 '잔고통보(gubun=1)'에서 전해주는 '보유수량'임.
                    # 여기서는 로그 출력 및 상태 확인만 진행
                    self.log(f"🔔 [실시간 체결 확인] {name}({code}) | {fill_qty}주 체결 / 체결가: {fill_price:,}원")
        
        elif gubun == '1': # 잔고통보 (실제 계좌의 확정된 보유수량이 내려옴)
            # 930: 보유수량, 931: 매입단가, 10: 현재가
            holding_qty = int(self.kiwoom.dynamicCall("GetChejanData(int)", 930).strip() or 0)
            buy_price = int(self.kiwoom.dynamicCall("GetChejanData(int)", 931).strip() or 0)
            
            self.log(f"📊 [잔고 동기화] {name}({code}) | 계좌: {self.account_num} | 확정 잔고: {holding_qty}주 | 매입단가: {buy_price:,}원")
            
            if code not in self.ordered_stocks:
                # 프로그램에 없던 종목이 잔고에 잡히면(수동 매수 등) 감시 리스트에 자동 편입
                self.ordered_stocks[code] = {
                    'avg_price': buy_price, 'total_qty': holding_qty, 'total_invested': holding_qty * buy_price,
                    'hit_levels': set(), 'sold': False, 'trade_count': 1,
                    'pending_sell': False, 'pending_buy': False
                }
                # 실시간 데이터를 받아야 익절 감시가 가능함
                self.kiwoom.dynamicCall("SetRealReg(QString, QString, QString, QString)", "3000", code, "10;11;12", "1")
                self.held_stock_codes.add(code)
            else:
                # 기존 종목의 수량 및 단가를 실제 서버 데이터로 즉각 업데이트 (데우건설 15주 vs 2주 문제 해결의 핵심!)
                self.ordered_stocks[code]['total_qty'] = holding_qty
                self.ordered_stocks[code]['avg_price'] = buy_price
                self.ordered_stocks[code]['total_invested'] = holding_qty * buy_price
                # 잔고 동기화 시 수량이 증가하면 매수 진행 중 플래그 해제
                if holding_qty > 0:
                    self.ordered_stocks[code]['pending_buy'] = False
                # 수량이 0이면 매도 진행 중 플래그 해제 및 보유 목록에서 제외
                if holding_qty == 0:
                    self.ordered_stocks[code]['pending_sell'] = False
                    self.held_stock_codes.discard(code)
                
                if holding_qty > 0:
                    self.held_stock_codes.add(code)
                else:
                    # 보유 수량이 0이면 포트폴리오 슬롯에서 제외
                    if code in self.held_stock_codes:
                        self.held_stock_codes.remove(code)
            
            self.save_state()
            self.update_autotrade_status(code, str(len(self.ordered_stocks.get(code, {}).get('hit_levels', []))), 
                                       f"🟢 잔고 동기화 완료: {holding_qty}주")

    def receive_real_data(self, code, real_type, real_data):
        if code == "140410": return # [강제 블랙리스트] 한샘(140410)은 일절 관여 안함
        
        if real_type == "주식체결":
            price = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", code, 10).strip()
            curr = abs(int(price))

            # --- 0. 공통 익절 감시 (주문 목록에 있으며, 실제로 봇이 관리하는 종목만 체크) ---
            stock_state = self.ordered_stocks.get(code)
            if isinstance(stock_state, dict) and stock_state.get('total_qty', 0) > 0:
                # [강력 제한] hit_levels가 있거나 target_stocks에 정의된 종목만 자동 익절 수행
                h_lvs = stock_state.get('hit_levels', set())
                is_managed = (code in self.target_stocks) or (len(h_lvs) > 0)
                
                if is_managed:
                    avg_p = stock_state.get('avg_price', 0)
                    if avg_p > 0:
                        profit_rate = (curr - avg_p) / avg_p * 100
                        t_count = stock_state.get('trade_count', 1)
                        target_profit = 2.0 if t_count == 2 else 3.0
                        
                        if profit_rate >= target_profit:
                            # [중복 방지] 이미 매도 주문이 나갔다면 스킵
                            if stock_state.get('pending_sell', False):
                                return
                                
                            self.log(f"💰 [익절 조건 달성] {code} 현재수익 {profit_rate:.2f}% >= 목표 {target_profit}%")
                            self.execute_auto_sell(code, curr, profit_rate)
                            return

            if code not in self.target_stocks: return

            # --- 2. 분할 매수 타점 감시 ---
            if code not in self.ordered_stocks:
                self.ordered_stocks[code] = {
                    'avg_price': 0, 'total_qty': 0, 'total_invested': 0,
                    'hit_levels': set(), 'sold': False,
                    'trade_count': 1,
                    'pending_sell': False, 'pending_buy': False
                }
                
            stock_state = self.ordered_stocks[code]
            
            # --- 2.1 재연결 동기화 (기록상 매수 타점은 있는데 실제 수량이 0인 경우) ---
            # [중복 방지] 이미 매수 주문이 나갔다면 스킵
            h_lvs = stock_state.get('hit_levels', set())
            is_pending_buy = stock_state.get('pending_buy', False)
            
            if not stock_state.get('sold', False) and len(h_lvs) > 0 and stock_state.get('total_qty', 0) == 0 and not is_pending_buy:
                if len(self.held_stock_codes) >= 2:
                    return # 슬롯이 없으면 복구 안 함
                
                triggers = self.target_stocks[code]['triggers']
                sync_pct = 0.0
                levels_to_sync = []
                for t in triggers:
                    if t['id'] in h_lvs:
                        sync_pct += float(t.get('pct', 0))
                        levels_to_sync.append(t['id'])
                
                if sync_pct > 0:
                    self.log(f"🔄 [재연결 동기화] {code} 종목의 타점 기록({len(levels_to_sync)}개)은 있으나 계좌 수량이 0입니다. 현재가로 복구 매수를 진행합니다.")
                    self.execute_auto_buy(code, curr, sync_pct, levels_to_sync)
                    return # 매수 진행 후 종료 (다음 틱에서 나머지 처리)
            triggers = self.target_stocks[code]['triggers']
            
            # 새 종목이 진입하려 할 때 2종목 한도 초과 방지
            is_new_buy = stock_state['total_qty'] == 0
            if is_new_buy and len(self.held_stock_codes) >= 2:
                # 2개의 슬롯이 꽉 차서 신규 매수 보류 (가격이 도달해도 무시)
                return

            total_pct_to_buy = 0.0
            levels_to_mark = []
            
            for t in triggers:
                # 지정된 타겟 가격보다 현재가가 작거나 같으면 뚫고 내려간 것 (도달)
                if curr <= t['price'] and t['id'] not in h_lvs:
                    total_pct_to_buy += float(t.get('pct', 0))
                    levels_to_mark.append(t['id'])
                    
            if total_pct_to_buy > 0:
                # [중복 방지] 이미 매수 주문이 나갔다면 스킵
                if stock_state.get('pending_buy', False):
                    self.log(f"⚠️ [중복방지] {code} 매수 주문이 이미 진행 중입니다. 요청을 무시합니다.")
                    return
                self.execute_auto_buy(code, curr, total_pct_to_buy, levels_to_mark)


    # ==========================
    # Auto Trade & Sell/Buy Logic
    # ==========================
    def execute_auto_buy(self, code, current_price, target_pct, levels_to_mark):
        if code == "140410": return # [강제 블랙리스트] 매수 차단
        
        # [유저 요청] 3분할 매수 시 비중이 과도하게 크게 잡히는 문제 해결
        # 기준 자산(initial_money)의 40%를 한 종목의 '최대 투자금'으로 설정 (buy_unit 대용)
        # 3번의 타점이 각각 0.2, 0.3, 0.5 비중이라면 -> 0.4 * 0.2, 0.4 * 0.3, 0.4 * 0.5씩 매수됨
        stock_max_budget = self.initial_money * 0.4
        budget = stock_max_budget * target_pct
        
        # 만약 계산된 예산이 현재 남은 예수금보다 많다면, 가진 현금 전체를 사용하도록 캡(Cap) 적용
        if budget > self.available_money:
            budget = self.available_money
            
        qty = int(budget / current_price)
        
        # 최소 1주 매수 보장
        if qty == 0 and budget > 0 and self.available_money >= current_price:
            qty = 1
        
        if qty > 0:
            # [중복 방지] 매수 주문 시작 전 플래그 설정
            if code in self.ordered_stocks:
                self.ordered_stocks[code]['pending_buy'] = True
                
            name = self.kiwoom.dynamicCall("GetMasterCodeName(QString)", code)
            lv_names = ", ".join(levels_to_mark)
            msg = f"🔥 [분할매수 타점도달: {lv_names}] {name}({code}) | {qty}주 시장가 매수 주문 진행!"
            self.log(msg)
            if self.telegram_manager:
                self.telegram_manager.send_message(f"📦 [매수] {name}({code})\n타점: {lv_names}\n주문: {qty}주 시장가")
            
            # 매수 주문 전송 (직접 호출 방식으로 변경하여 9개 인자 안정성 확보)
            res = self.kiwoom.SendOrder("자동매수", "8000", self.account_num, 1, code, qty, 0, "03", "")
            if res == 0:
                self.log(f"-> 매수 주문 접수 성공! ({qty}주 시장가 요청)")
                
                # [수정] 여기서 직접 수량을 올리지 않습니다. 
                # OnReceiveChejanData(gubun='1') 이벤트를 통해 실제 서버의 잔고가 내려올 때만 업데이트합니다.
                
                state = self.ordered_stocks.get(code)
                if state:
                    for l in levels_to_mark:
                        state['hit_levels'].add(l)
                
                # 자금 추정치만 우선 갱신 (추후 OnReceiveChejanData에서 확정 잔고로 덮어씌워짐)
                self.available_money -= (qty * current_price)
                
                # 주문 상태 업데이트 (리스트가 비어있을 경우 대비 안전하게 접근)
                hit_count = len(state['hit_levels']) if state else 0
                status_msg = f"{hit_count}차 분할매수 주문 시도"
                self.update_autotrade_status(code, str(hit_count), f"🟡 {status_msg}")
                self.save_state()
            else:
                self.log(f"-> 매수 주문 접수 실패. 에러코드: {res}")
                # 주문 실패 시 다시 시도할 수 있도록 플래그 해제
                if code in self.ordered_stocks:
                    self.ordered_stocks[code]['pending_buy'] = False
        else:
            self.log(f"주문 가능한 수량이 0입니다. (예수금 소진)")

    def manual_delete_stock(self, code):
        name = self.kiwoom.dynamicCall("GetMasterCodeName(QString)", code)
        self.log(f"✂️ [수동 삭제] 사용자가 직접 {name}({code}) 종목을 감시 리스트에서 제외했습니다.")
        self.remove_target_stock(code)

    def remove_target_stock(self, code):
        if code in self.target_stocks:
            del self.target_stocks[code]
        if code in self.ordered_stocks:
            self.ordered_stocks[code]['sold'] = True
            
        self.kiwoom.dynamicCall("SetRealRemove(QString, QString)", "all", code)
        
        # 테이블에서도 삭제
        for r in range(self.table_autotrade.rowCount() - 1, -1, -1):
            if self.table_autotrade.item(r, 2).text() == code:
                self.table_autotrade.removeRow(r)
                
        self.save_state()
                
    def execute_auto_sell(self, code, current_price, profit_rate, is_stoploss=False):
        if code == "140410": return # [강제 블랙리스트] 매도 차단
        
        # [수정] 성격이 급한 키움 API 특성상 매도 직전 동기 조회(get_balance_sync)는 
        # TR 충돌과 UI 프리징의 원인이 됩니다. 페이지네이션이 해결된 현재,
        # 주기적으로 업데이트되는 내부 잔고 데이터(ordered_stocks)를 그대로 사용합니다.
        stock_data = self.ordered_stocks.get(code)
        if not stock_data or stock_data.get('total_qty', 0) <= 0:
            self.log(f"⚠️ {code} 종목의 매도 신호가 발생했으나, 현재 로컬 보유 수량이 0주입니다. 매도를 취소합니다.")
            return
            
        # [중단] 중복 주문 방지
        stock_data['pending_sell'] = True
        
        qty = int(stock_data['total_qty'])
        name = self.kiwoom.dynamicCall("GetMasterCodeName(QString)", code)
        self.log(f"✅ [최종 확인] {name}({code}) 서버 확정 잔고 {qty}주 모두 매도 진행!")
        
        order_name = "자동익절"
        if is_stoploss:
            msg = f"🩸 [손절 발동] {name}({code}) 기준봉 시가 -7% 이탈! {qty}주 전량 시장가 손절 매도!!"
            self.log(msg)
            if self.telegram_manager:
                self.telegram_manager.send_message(f"📉 [손절] {name}({code})\n사유: -7% 이탈\n수량: {qty}주 전량 매도")
            order_name = "자동손절"
        else:
            msg = f"💰 [자동익절 발동] {name}({code}) 누적수익 +{profit_rate:.2f}% 달성! {qty}주 전량 시장가 매도!!"
            self.log(msg)
            if self.telegram_manager:
                self.telegram_manager.send_message(f"💵 [자동익절] {name}({code})\n수수익: +{profit_rate:.2f}%\n수량: {qty}주 전량 매도")
        
        # 2: 매도 (Sell) - 직접 호출 방식으로 변경
        res = self.kiwoom.SendOrder(order_name, "8001", self.account_num, 2, code, qty, 0, "03", "")
        if res == 0:
            self.log(f"-> 매도 주문 접수 성공!")
            
            # 상태 변경
            self.ordered_stocks[code]['sold'] = True
            
            # 확보된 금액(대략적) 예수금 원복
            self.available_money += (qty * current_price)
            
            # 포트폴리오에서 방 빼주기 (다른 종목 진입 허용)
            self.held_stock_codes.discard(code)
            
            self.update_autotrade_status(code, "-", f"🎉 전량 3% 익절 완료 (+{profit_rate:.2f}%)")
            self.log("✅ 슬롯이 비워져 매수가 안되었던 대기 종목도 타점에 들어오면 자동매수가 진행됩니다.")
            self.save_state()
        else:
            self.log(f"-> 매도 주문 접수 실패. 에러코드: {res}")
            # [중요] 주문 접수 자체가 실패했으므로 다시 주문이 나갈 수 있게 플래그 해제
            if code in self.ordered_stocks:
                self.ordered_stocks[code]['pending_sell'] = False

    def update_autotrade_status(self, code, level_idx, status_msg):
        for r in range(self.table_autotrade.rowCount()):
            if self.table_autotrade.item(r, 2).text() == code:
                self.table_autotrade.setItem(r, 7, QTableWidgetItem(level_idx))
                self.table_autotrade.setItem(r, 8, QTableWidgetItem(status_msg))
                break

    def run_autotrade_algorithm(self, list_type, name, code, trcode, rqname, cnt):
        if code == "140410": return # [강제 블랙리스트] 감시 제외
        dates, opens, highs, closes, values = [], [], [], [], []
        for i in range(cnt):
            dates.append(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "일자").strip())
            opens.append(abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "시가").strip())))
            highs.append(abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "고가").strip())))
            closes.append(abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "현재가").strip())))
            values.append(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "거래대금").strip()))
            
        if cnt == 0: return

        # 자동 검색식은 무조건 당일(최근 캔들) 기준으로 종가/시가 6분할 세팅
        t_open = opens[0]
        t_close = closes[0]
        t_high = highs[0]
        t_date = dates[0]
        t_val = values[0]

        stop_price = t_open * 0.93
        if closes[0] <= stop_price:
            self.log(f"📉 [조건 탈락] {name}({code}) 현재 가격이 이미 기준봉 시가 대비 -7%를 이탈했습니다. 큐에서 삭제합니다.")
            return

        # 트리거 라인 생성 (사용자 요청: 시가 기준 3분할)
        trigs = [
            {'id': 'O+1.5%', 'price': t_open * 1.015, 'pct': 0.20},
            {'id': 'O 0% ',  'price': t_open * 1.000, 'pct': 0.30},
            {'id': 'O-1.5%', 'price': t_open * 0.985, 'pct': 0.50},
        ]
        
        self.target_stocks[code] = {'open': t_open, 'close': t_close, 'high': t_high, 'triggers': trigs, 'config': 0, 'list_type': list_type, 'name': name, 'date': t_date, 'val': t_val}
        
        date_fmt = f"{t_date[:4]}-{t_date[4:6]}-{t_date[6:]}"
        val_fmt = format(t_val, ",")
        self.add_autotrade_row(list_type, name, code, date_fmt, f"{t_close:,}", f"{t_open:,}", val_fmt, "0", "👀 자동 종가+시가 6분할 감시중")
        
        self.kiwoom.dynamicCall("SetRealReg(QString, QString, QString, QString)", "3000", code, "10;11;12", "1")
        self.log(f"[통과] {name}({code}) 당일 기준 자동 종가/시가 6분할 테이블 등록 완료!")
        self.save_state()

    def add_autotrade_row(self, list_type, name, code, date, topen, thigh, tval, lv, status):
        # 중복 추가 방지
        for r in range(self.table_autotrade.rowCount()):
            if self.table_autotrade.item(r, 2).text() == code: return
            
        r = self.table_autotrade.rowCount()
        self.table_autotrade.insertRow(r)
        
        self.table_autotrade.setItem(r, 0, QTableWidgetItem(list_type))
        self.table_autotrade.setItem(r, 1, QTableWidgetItem(name))
        self.table_autotrade.setItem(r, 2, QTableWidgetItem(code))
        self.table_autotrade.setItem(r, 3, QTableWidgetItem(date))
        self.table_autotrade.setItem(r, 4, QTableWidgetItem(topen))
        self.table_autotrade.setItem(r, 5, QTableWidgetItem(thigh))
        self.table_autotrade.setItem(r, 6, QTableWidgetItem(tval))
        self.table_autotrade.setItem(r, 7, QTableWidgetItem(lv))
        self.table_autotrade.setItem(r, 8, QTableWidgetItem(status))
        
        btn_delete = QPushButton("X 삭제")
        btn_delete.setStyleSheet("background-color: #ffcccc; color: red; font-size: 11px;")
        btn_delete.clicked.connect(lambda _, c=code: self.manual_delete_stock(c))
        self.table_autotrade.setCellWidget(r, 9, btn_delete)

    def run_manual_algorithm(self, list_type, name, code, target_date, trigger_config, trcode, rqname, cnt):
        if code == "140410": 
            self.log(f"🚫 [차단] 140410 종목은 블랙리스트이므로 등록할 수 없습니다.")
            return
        dates, opens, highs, closes, values = [], [], [], [], []
        for i in range(cnt):
            dates.append(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "일자").strip())
            opens.append(abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "시가").strip())))
            highs.append(abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "고가").strip())))
            closes.append(abs(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "현재가").strip())))
            values.append(int(self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "거래대금").strip()))
            
        found = False
        t_open, t_close, t_high, t_val, t_date = 0, 0, 0, 0, ""

        for i in range(cnt):
            if dates[i] == target_date:
                found = True
                t_open = opens[i]
                t_close = closes[i]
                t_high = highs[i]
                t_date = dates[i]
                t_val = values[i]
                break
                
        if found:
            stop_price = t_close * 0.93 if trigger_config == 1 else t_open * 0.93
            if closes[0] <= stop_price:
                ref_str = "종가" if trigger_config == 1 else "시가"
                self.log(f"📉 [수동추가 탈락] {name}({code}) 현재 가격이 이미 기준봉 {ref_str} 대비 -7%를 이탈했습니다. 큐에서 삭제합니다.")
                return

            # 분할 매수 설정
            trigs = []
            if trigger_config == 1: # 종가만 3분할
                trigs = [
                    {'id': 'C+1.5%', 'price': t_close * 1.015, 'pct': 0.20},
                    {'id': 'C 0% ',  'price': t_close * 1.000, 'pct': 0.30},
                    {'id': 'C-1.5%', 'price': t_close * 0.985, 'pct': 0.50},
                ]
            elif trigger_config == 2: # 시가만 3분할
                trigs = [
                    {'id': 'O+1.5%', 'price': t_open * 1.015, 'pct': 0.20},
                    {'id': 'O 0% ',  'price': t_open * 1.000, 'pct': 0.30},
                    {'id': 'O-1.5%', 'price': t_open * 0.985, 'pct': 0.50},
                ]
            else: # 종가/시가 6분할
                trigs = [
                    {'id': 'C+1.5%', 'price': t_close * 1.015, 'pct': 0.05},
                    {'id': 'C 0% ',  'price': t_close * 1.000, 'pct': 0.10},
                    {'id': 'C-1.5%', 'price': t_close * 0.985, 'pct': 0.15},
                    {'id': 'O+1.5%', 'price': t_open * 1.015, 'pct': 0.10},
                    {'id': 'O 0% ',  'price': t_open * 1.000, 'pct': 0.20},
                    {'id': 'O-1.5%', 'price': t_open * 0.985, 'pct': 0.30},
                ]
            self.target_stocks[code] = {'open': t_open, 'close': t_close, 'high': t_high, 'triggers': trigs, 'config': trigger_config, 'list_type': list_type, 'name': name, 'date': t_date, 'val': t_val}
            
            date_fmt = f"{t_date[:4]}-{t_date[4:6]}-{t_date[6:]}"
            val_fmt = format(t_val, ",")
            
            config_name = "종가+시가 6분할" if trigger_config == 0 else ("종가 3분할" if trigger_config == 1 else "시가 3분할")
            self.add_autotrade_row(list_type, name, code, date_fmt, f"{t_close:,}", f"{t_open:,}", val_fmt, "0", f"👀 수동 {config_name} 대기")
            
            self.kiwoom.dynamicCall("SetRealReg(QString, QString, QString, QString)", "3000", code, "10;11;12", "1")
            self.log(f"[수동 테이블 등록] {name}({code}) {date_fmt} 기준 양봉 {config_name} 모니터링 감시 시작!")
            self.save_state()
        else:
            self.log(f"[수동추가 에러] {name}({code})의 과거 데이터에서 {target_date} 일자를 찾을 수 없습니다.")

    # ==========================
    # Condition Search Events
    # ==========================
    def receive_condition_ver(self, lRet, sMsg):
        if lRet == 1:
            condition_str = self.kiwoom.dynamicCall("GetConditionNameList()").strip()
            self.condition_dict.clear()
            for cond in condition_str.split(";"):
                if "^" in cond:
                    idx, name = cond.split("^")
                    self.condition_dict[name] = int(idx)
            
            if self.target_condition_name in self.condition_dict:
                self.log(f"자동매매용 '{self.target_condition_name}' 조건식 로드 100% 완료!")
            else:
                self.log(f"⚠️ 영웅문에 '{self.target_condition_name}' 조건식이 존재하지 않습니다. 영웅문(HTS)에서 똑같은 이름으로 먼저 만들어주세요!")
                self.btn_trade_start.setEnabled(False)

    def start_auto_trade(self):
        if self.target_condition_name not in self.condition_dict: return
        idx = self.condition_dict[self.target_condition_name]
        
        # 전체 초기화 대신 '자동' 리스트 중 아직 매수되지 않은 종목만 테이블과 메모리에서 삭제
        for r in range(self.table_autotrade.rowCount() - 1, -1, -1):
            if self.table_autotrade.item(r, 0).text() == "자동":
                code = self.table_autotrade.item(r, 2).text()
                if code not in self.ordered_stocks or self.ordered_stocks[code]['total_qty'] == 0:
                    self.table_autotrade.removeRow(r)
                    if code in self.target_stocks:
                        del self.target_stocks[code]
                    self.kiwoom.dynamicCall("SetRealRemove(QString, QString)", "all", code)
                    
        # 대기열 큐에서도 '자동(auto)' 항목만 제거하고 수동(manual) 항목은 유지
        self.api_queue = [item for item in self.api_queue if isinstance(item, dict) and item.get('type') == 'manual']
        self.update_queue_ui()
        
        self.log(f"🚀 실시간 자동매매 가동: 6분할 타점 매수 + 3% 무인 익절 감시 시작")
        self.kiwoom.dynamicCall("SendCondition(QString, QString, int, int)", "4000", self.target_condition_name, idx, 1)

    def stop_auto_trade(self):
        if self.target_condition_name not in self.condition_dict: return
        idx = self.condition_dict[self.target_condition_name]
        self.kiwoom.dynamicCall("SendConditionStop(QString, QString, int)", "4000", self.target_condition_name, idx)
        # DisconnectRealData("3000")를 여기서 호출하면 수동/기매수 종목의 실시간 데이터 갱신까지 전체 마비되므로 삭제합니다.
        self.log("자동매매 신규 편입 모니터링이 중단되었습니다. (수동 타점 및 기포착 종목 실시간 감시는 계속 유지됩니다.)")

    def receive_tr_condition(self, scr_no, code_list, condition_name, index, next_val):
        if condition_name == self.target_condition_name:
            # 장중(15:30 이전)에는 자동 검색 결과 반영 안 함 (사용자 요청)
            if QTime.currentTime() < QTime(15, 30):
                return
                
            codes = [c for c in code_list.split(";") if c]
            for c in codes:
                if not self.is_in_queue(c) and c not in self.target_stocks:
                    self.api_queue.append({'code': c, 'type': 'auto'})
            self.update_queue_ui()

    def receive_real_condition(self, code, event_type, condition_name, index):
        if condition_name == self.target_condition_name:
            # 장중(15:30 이전)에는 자동 검색 결과 반영 안 함 (사용자 요청)
            if QTime.currentTime() < QTime(15, 30):
                return
                
            if event_type == "I": # 편입
                name = self.kiwoom.dynamicCall("GetMasterCodeName(QString)", code)
                self.log(f"[실시간 편입 감지] {name} ({code}) -> 타점 추출 대기열에 진입했습니다.")
                if not self.is_in_queue(code) and code not in self.target_stocks:
                    self.api_queue.append({'code': code, 'type': 'auto'})
                    self.update_queue_ui()
            elif event_type == "D": 
                pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    kiwoom_app = KiwoomApp()
    kiwoom_app.show()
    sys.exit(app.exec_())
