import asyncio
import threading
import logging
from typing import Optional, Callable
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Application
import requests
from datetime import datetime

# Suppress debug logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

class TelegramManager:
    def __init__(self, token: str, chat_id: str, 
                 add_callback: Optional[Callable[[str, str, int], None]] = None,
                 list_callback: Optional[Callable[[], str]] = None,
                 del_callback: Optional[Callable[[str], str]] = None):
        self.token = token
        self.chat_id = chat_id
        self.add_callback = add_callback
        self.list_callback = list_callback
        self.del_callback = del_callback
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.app: Optional[Application] = None
        self.thread: Optional[threading.Thread] = None
        self.is_running = False

    def start(self):
        if not self.token or not self.chat_id:
            print("Telegram Token or Chat ID missing.")
            return
        
        if self.is_running:
            return

        self.thread = threading.Thread(target=self._run_bot, daemon=True)
        self.thread.start()
        self.is_running = True

    def _run_bot(self):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            self.app = ApplicationBuilder().token(self.token).build()
            
            # Add Handlers
            self.app.add_handler(CommandHandler("start", self._cmd_start))
            self.app.add_handler(CommandHandler("add", self._cmd_add))
            self.app.add_handler(CommandHandler("list", self._cmd_list))
            self.app.add_handler(CommandHandler("del", self._cmd_del))
            self.app.add_handler(CommandHandler("status", self._cmd_status))
            
            print(f"Telegram Bot started (ChatID: {self.chat_id})")
            self.app.run_polling(close_loop=False)
        except Exception as e:
            print(f"Telegram Bot Crash: {e}")
            self.is_running = False

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            help_text = (
                "안녕하세요! Kiwoom Trading Bot입니다.\n\n"
                "📌 **주요 명령어**:\n"
                "1️⃣ `/add [종목] [날짜] [타입]` : 종목 감시 등록\n"
                "2️⃣ `/list` : 현재 감시/보유 종목 리스트 조회\n"
                "3️⃣ `/del [종목명/코드]` : 감시 종목 삭제\n"
                "4️⃣ `/status` : 앱 연결 상태 확인\n\n"
                "예시: `/add 삼성전자`, `/del 삼성전자`"
            )
            await update.message.reply_text(help_text, parse_mode='Markdown')

    async def _cmd_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_chat or not update.message: return
        if str(update.effective_chat.id) != str(self.chat_id): return

        if self.list_callback:
            result = self.list_callback()
            await update.message.reply_text(result, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ 리스트를 불러올 수 없습니다.")

    async def _cmd_del(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_chat or not update.message: return
        if str(update.effective_chat.id) != str(self.chat_id): return
        
        args = context.args
        if not args:
            await update.message.reply_text("사용법: `/del [종목명 또는 코드]`")
            return

        stock_info = " ".join(args)
        if self.del_callback:
            msg = self.del_callback(stock_info)
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("❌ 삭제 기능을 사용할 수 없습니다.")

    async def _cmd_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_chat or not update.message:
            return

        if str(update.effective_chat.id) != str(self.chat_id):
            await update.message.reply_text("권한이 없습니다.")
            return

        # Comprehensive parsing to handle multi-word stock names
        args = context.args
        if not args:
            await update.message.reply_text("사용법: `/add 삼성전자 [날짜] [타입]`", parse_mode='Markdown')
            return

        type_map = {"둘다": 0, "종가": 1, "시가": 2, "0": 0, "1": 1, "2": 2}
        
        target_date = datetime.now().strftime("%Y%m%d")
        target_type = 0
        stock_name_parts = []
        
        # Determine what's a date/type and what's the stock name
        for i, arg in enumerate(args):
            if arg.isdigit() and len(arg) == 8:
                target_date = arg
                # If there's a next arg, check if it's a type
                if i + 1 < len(args):
                    arg_next = args[i+1]
                    target_type = type_map.get(arg_next, 0)
                break
            elif arg in type_map and i > 0:
                target_type = type_map[arg]
                break
            else:
                stock_name_parts.append(arg)
        
        stock_info = " ".join(stock_name_parts)
        if not stock_info:
            await update.message.reply_text("❌ 종목명이 입력되지 않았습니다.")
            return

        if self.add_callback:
            type_names = ["둘다(6분할)", "종가(3분할)", "시가(3분할)"]
            print(f"[Telegram] Callback trigger: {stock_info}, {target_date}, {target_type}")
            self.add_callback(stock_info, target_date, target_type)
            await update.message.reply_text(
                f"✅ **등록 완료**\n종목: {stock_info}\n날짜: {target_date}\n타입: {type_names[target_type]}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ 앱과 연결되지 않았습니다.")

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_chat or not update.message:
            return
            
        if str(update.effective_chat.id) != str(self.chat_id):
            return
        await update.message.reply_text("Kiwoom Trading App이 실행 중입니다.")

    def send_message(self, text: str):
        if not self.is_running or not self.token or not self.chat_id:
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"Telegram Send Error: {e}")

    def stop(self):
        if self.app:
            try:
                self.app.stop_running()
            except:
                pass
        self.is_running = False
