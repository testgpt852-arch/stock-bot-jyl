# -*- coding: utf-8 -*-
"""
Telegram Bot v3.1 - 제미나이 검증 반영 (완전체)
- 이중 스캔 모드: 뉴스 종목 1분 / 시장 전체 10분
- 뉴스-모멘텀 연동 복구
- 랜덤 지연 적용
"""

import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import Config
import random

# v3.1 엔진 import
from ai_brain_v3 import AIBrainV3
from news_engine_v3 import NewsEngineV3
from momentum_tracker_v3_1 import MomentumTrackerV3_1
from predictor_engine_v3 import PredictorEngineV3

logger = logging.getLogger(__name__)

class TelegramBotV3_1:
    def __init__(self):
        self.app = None
        self.chat_id = Config.TELEGRAM_CHAT_ID
        
        # 알림 제어 상태
        self.notifications_paused = False
        
        # 중복 방지
        self.seen_filings = set()
        
        # 엔진 초기화
        try:
            self.ai = AIBrainV3()
            self.news_engine = NewsEngineV3(self.ai)
            self.momentum = MomentumTrackerV3_1()  # 🔥 v3.1
            self.predictor = PredictorEngineV3()
            
            logger.info("✅ 모든 엔진 초기화 성공 (v3.1 완전체)")
            
        except Exception as e:
            logger.error(f"❌ 엔진 초기화 실패: {e}")
            raise
        
        logger.info("🐺 Telegram Bot v3.1 완전체 초기화")
    
    async def start(self):
        """봇 시작"""
        try:
            self.app = Application.builder().token(Config.TELEGRAM_TOKEN).build()
            
            # 명령어
            self.app.add_handler(CommandHandler("start", self.cmd_start))
            self.app.add_handler(CommandHandler("analyze", self.cmd_analyze))
            self.app.add_handler(CommandHandler("report", self.cmd_report))
            self.app.add_handler(CommandHandler("status", self.cmd_status))
            self.app.add_handler(CommandHandler("news", self.cmd_news))
            self.app.add_handler(CommandHandler("pause", self.cmd_pause))
            self.app.add_handler(CommandHandler("resume", self.cmd_resume))
            self.app.add_handler(CommandHandler("help", self.cmd_help))
            
            await self.app.initialize()
            await self.app.start()
            
            # 🔥 v3.1: 이중 스캔 모드 백그라운드 작업
            asyncio.create_task(self.schedule_reports())
            asyncio.create_task(self.news_monitor())
            asyncio.create_task(self.momentum_monitor_dynamic())  # 1분 주기
            asyncio.create_task(self.momentum_monitor_full())     # 10분 주기
            
            logger.info("✅ 봇 시작 (v3.1 완전체)")
            
            await self.send_message(
                "🐺 조기경보 시스템 v3.1.1 완전 방어 시작!\n\n"
                "✅ AI Brain v3.0 (공격적 스캘퍼)\n"
                "✅ News Engine v3.1.1 (미국 5대장 + 한국 3대장 + SEC)\n"
                "✅ Momentum Tracker v3.1.1 (다중 fallback)\n"
                "✅ Predictor Engine v3.0 (SEC Only)\n\n"
                "📊 다중 방어 시스템:\n"
                "• 1차: Finviz 스크래핑\n"
                "• 2차: Yahoo Finance API\n"
                "• 3차: yfinance 직접 조회\n\n"
                "⏱️ 이중 스캔 모드:\n"
                "• 뉴스 종목: 1분 주기 집중 감시 🔥\n"
                "• 시장 전체: 10분 주기 전면 스캔\n"
                "• 랜덤 지연: 차단 방지\n\n"
                "🎯 RIME 급등주 선취매!"
            )
            
        except Exception as e:
            logger.error(f"봇 시작 실패: {e}")
            raise
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시작 명령어"""
        await update.message.reply_text(
            "🐺 조기경보 시스템 v3.1.1 완전 방어\n\n"
            "📱 사용 가능한 명령어:\n\n"
            "🔍 분석:\n"
            "• /analyze [종목명] - 종목 분석\n\n"
            "📊 정보:\n"
            "• /report - 즉시 리포트\n"
            "• /status - 시스템 상태\n"
            "• /news - 최근 뉴스 TOP 5\n\n"
            "🔔 알림 제어:\n"
            "• /pause - 알림 일시 정지\n"
            "• /resume - 알림 재개\n\n"
            "❓ /help - 전체 도움말\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🔥 v3.1.1 완전 방어 특징:\n"
            "• 다중 fallback (Finviz→Yahoo→yfinance)\n"
            "• 뉴스 종목 1분 주기 감시\n"
            "• 시장 전체 10분 주기 스캔\n"
            "• 랜덤 User-Agent (차단 방지)\n"
            "• 랜덤 지연 (Anti-Ban)\n\n"
            f"💡 현재 상태:\n"
            f"  알림: {'⏸️ 일시정지' if self.notifications_paused else '▶️ 활성화'}\n"
            f"  뉴스 종목: {len(self.momentum.dynamic_tickers_us)}개 (US)\n"
            f"  뉴스 종목: {len(self.momentum.dynamic_tickers_kr)}개 (KR)\n\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """알림 일시 정지"""
        self.notifications_paused = True
        await update.message.reply_text(
            "⏸️ 알림이 일시 정지되었습니다.\n\n"
            "• 모든 알림 중단\n\n"
            "💡 /resume으로 재개"
        )
        logger.info("⏸️ 알림 일시 정지")
    
    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """알림 재개"""
        self.notifications_paused = False
        await update.message.reply_text(
            "▶️ 알림이 다시 시작되었습니다!\n\n"
            "• 뉴스 알림: 활성화\n"
            "• 급등 알림: 활성화\n\n"
            "🐺 Beast Mode 가동!"
        )
        logger.info("▶️ 알림 재개")
    
    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """종목 분석"""
        if not context.args:
            await update.message.reply_text(
                "사용법:\n"
                "/analyze 삼성전자\n"
                "/analyze AAPL\n"
                "/analyze 005930"
            )
            return
        
        ticker = ' '.join(context.args)
        await update.message.reply_text(f"🔍 **{ticker}** 분석 중...")
        
        try:
            import yfinance as yf
            
            ticker_map = {
                '삼성전자': '005930.KS',
                'sk하이닉스': '000660.KS',
                '현대차': '005380.KS',
                'lg화학': '051910.KS',
                'naver': '035420.KS',
                '카카오': '035720.KS',
            }
            
            search_ticker = ticker.lower()
            if search_ticker in ticker_map:
                symbol = ticker_map[search_ticker]
            elif ticker.isdigit():
                symbol = f"{ticker}.KS"
            else:
                symbol = ticker.upper()
            
            stock = yf.Ticker(symbol)
            hist = stock.history(period='5d')
            
            if hist.empty:
                await update.message.reply_text(f"⚠️ {ticker} 데이터를 찾을 수 없습니다.")
                return
            
            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            change = current_price - prev_price
            change_pct = (change / prev_price) * 100 if prev_price != 0 else 0
            volume = hist['Volume'].iloc[-1]
            avg_volume = hist['Volume'].mean()
            volume_ratio = volume / avg_volume if avg_volume > 0 else 0
            
            msg = f"📊 {ticker} 분석 결과\n\n"
            msg += f"현재가: {current_price:,.2f} ({change:+.2f}, {change_pct:+.2f}%)\n"
            msg += f"거래량: {volume:,.0f} (평균 대비 {volume_ratio:.1f}배)\n\n"
            msg += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            await update.message.reply_text(msg)
            
        except Exception as e:
            logger.error(f"/analyze 오류: {e}")
            await update.message.reply_text(f"⚠️ 분석 중 오류 발생: {str(e)}")
    
    async def cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """즉시 리포트"""
        await update.message.reply_text("📊 리포트 생성 중...")
        
        try:
            us_report = await self.predictor.generate_daily_report('US')
            us_msg = self._format_daily_report(us_report, '🇺🇸 미국')
            await update.message.reply_text(us_msg)
            
        except Exception as e:
            logger.error(f"리포트 생성 오류: {e}")
            await update.message.reply_text(f"⚠️ 리포트 생성 실패: {str(e)}")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시스템 상태"""
        try:
            msg = "🐺 시스템 상태 (v3.1.1 완전 방어)\n\n"
            
            # 알림 상태
            status_emoji = "⏸️ 일시정지" if self.notifications_paused else "▶️ 활성화"
            msg += f"알림: {status_emoji}\n\n"
            
            # AI 엔진
            msg += "AI Brain v3.0\n"
            msg += f"✅ 페르소나: 공격적 스캘퍼\n"
            msg += f"✅ 모델: {', '.join(self.ai.scanner_models[:2])}\n\n"
            
            # 뉴스 엔진
            msg += "News Engine v3.1.1\n"
            msg += f"✅ 소스: {len(self.news_engine.sources)}개\n"
            msg += f"✅ 중복 체크: {len(self.news_engine.seen_urls)}개\n\n"
            
            # 모멘텀 트래커
            msg += "Momentum Tracker v3.1.1\n"
            msg += f"✅ 다중 fallback (Finviz→Yahoo→yfinance)\n"
            msg += f"✅ 뉴스 종목: {len(self.momentum.dynamic_tickers_us)}개 (US)\n"
            msg += f"✅ 뉴스 종목: {len(self.momentum.dynamic_tickers_kr)}개 (KR)\n"
            msg += f"✅ 랜덤 User-Agent: {len(self.momentum.user_agents)}개\n\n"
            
            # 백그라운드 작업
            msg += "백그라운드 작업\n"
            msg += f"✅ 뉴스 모니터: 30초\n"
            msg += f"✅ 뉴스 종목 감시: 1분 🔥\n"
            msg += f"✅ 시장 전체 스캔: 10분\n"
            msg += f"✅ 리포트: 23:00\n\n"
            
            msg += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            await update.message.reply_text(msg)
            
        except Exception as e:
            logger.error(f"/status 오류: {e}")
            await update.message.reply_text(f"⚠️ 상태 조회 실패: {str(e)}")
    
    async def cmd_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """최근 뉴스 조회"""
        try:
            await update.message.reply_text("📰 최근 뉴스 조회 중...")
            
            news_list = await self.news_engine.scan_all_sources()
            
            if not news_list:
                await update.message.reply_text("📭 최근 뉴스가 없습니다.")
                return
            
            top_news = news_list[:5]
            
            msg = f"📰 최근 뉴스 TOP 5\n\n"
            
            for i, news in enumerate(top_news, 1):
                is_filing = news.get('type') == 'filing'
                emoji = "📋" if is_filing else "📰"
                
                msg += f"{i}. {emoji} {news['title'][:60]}...\n"
                msg += f"   출처: {news['source']}\n"
                
                if news.get('published_time_kst'):
                    msg += f"   시간: {news['published_time_kst']}\n"
                
                msg += "\n"
            
            msg += "💡 AI 분석은 자동으로 진행됩니다."
            
            await update.message.reply_text(msg)
            
        except Exception as e:
            logger.error(f"/news 오류: {e}")
            await update.message.reply_text(f"⚠️ 뉴스 조회 실패: {str(e)}")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """도움말"""
        await update.message.reply_text(
            "📚 조기경보 시스템 v3.1.1 완전 방어\n\n"
            "📱 명령어:\n"
            "• /start - 메뉴판\n"
            "• /analyze 종목명 - 종목 분석\n"
            "• /report - 즉시 리포트\n"
            "• /status - 시스템 상태\n"
            "• /news - 최근 뉴스 TOP 5\n"
            "• /pause - 알림 일시 정지\n"
            "• /resume - 알림 재개\n"
            "• /help - 이 도움말\n\n"
            "⏰ 자동 알림:\n"
            "• 23:00 - 미국장 저녁 브리핑\n"
            "• 장중 - 실시간 뉴스 (30초)\n"
            "• 장중 - 뉴스 종목 감시 (1분) 🔥\n"
            "• 장중 - 시장 전체 스캔 (10분)\n\n"
            "🔥 v3.1.1 완전 방어 특징:\n"
            "• 다중 fallback 시스템:\n"
            "  1차: Finviz 스크래핑\n"
            "  2차: Yahoo Finance API\n"
            "  3차: yfinance 직접 조회\n"
            "• 이중 스캔 모드\n"
            "• 랜덤 User-Agent\n"
            "• 랜덤 지연 (Anti-Ban)\n\n"
            "🎯 RIME 급등주 선취매!"
        )
    
    async def schedule_reports(self):
        """스케줄러"""
        logger.info("📅 스케줄러 시작")
        
        while True:
            try:
                # 랜덤 지연
                await asyncio.sleep(random.uniform(25, 35))
                
                now = datetime.now()
                
                if now.hour == 23 and now.minute == 0:
                    await self.send_evening_report_us()
                    await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"스케줄러 오류: {e}")
                await asyncio.sleep(60)
    
    async def send_evening_report_us(self):
        """미국 저녁 리포트"""
        try:
            report = await self.predictor.generate_daily_report('US')
            message = self._format_daily_report(report, '🇺🇸 미국장 저녁 브리핑')
            await self.send_message(message)
            
        except Exception as e:
            logger.error(f"미국 리포트 오류: {e}")
    
    async def news_monitor(self):
        """🔥 v3.1: 뉴스 모니터 (30초 주기, 뉴스 종목 추출)"""
        logger.info("📰 뉴스 모니터 시작")
        
        while True:
            try:
                if self.notifications_paused:
                    await asyncio.sleep(random.uniform(25, 35))
                    continue
                
                news_list = await self.news_engine.scan_all_sources()
                
                for news in news_list[:5]:
                    try:
                        # AI 빠른 스코어
                        passes_quick = await self.ai.quick_score(news['title'], threshold=8.0)
                        
                        if not passes_quick:
                            continue
                        
                        # 상세 분석
                        analysis = await self.ai.analyze_news_signal(news)
                        
                        if not analysis:
                            continue
                        
                        # 🔥 v3.1: 뉴스에서 종목 추출하여 모멘텀 트래커에 추가
                        ticker_in_news = analysis.get('ticker_in_news')
                        recommendations = analysis.get('recommendations', [])
                        
                        market = news.get('market', 'US')
                        
                        if ticker_in_news and ticker_in_news != 'null':
                            self.momentum.add_dynamic_ticker(ticker_in_news, market)
                        
                        # 추천 종목도 추가 (최대 3개)
                        for rec in recommendations[:3]:
                            ticker = rec.get('ticker', 'UNKNOWN')
                            if ticker != 'UNKNOWN':
                                self.momentum.add_dynamic_ticker(ticker, market)
                        
                        # 알림 메시지 생성
                        msg = self._format_news_alert(news, analysis)
                        await self.send_message(msg)
                        
                        await asyncio.sleep(random.uniform(0.8, 1.2))
                        
                    except Exception as e:
                        logger.debug(f"뉴스 처리 오류: {e}")
                        continue
                
                # 랜덤 지연
                await asyncio.sleep(random.uniform(25, 35))
                
            except Exception as e:
                logger.error(f"뉴스 모니터 오류: {e}")
                await asyncio.sleep(random.uniform(55, 65))
    
    async def momentum_monitor_dynamic(self):
        """🔥 v3.1: 뉴스 종목 집중 감시 (1분 주기)"""
        logger.info("🔥 뉴스 종목 감시 시작 (1분 주기)")
        
        while True:
            try:
                if self.notifications_paused:
                    await asyncio.sleep(random.uniform(55, 65))
                    continue
                
                # 미국 뉴스 종목
                us_signals = await self.momentum.scan_momentum('US', mode='dynamic')
                for signal in us_signals:
                    msg = self._format_momentum_alert(signal)
                    await self.send_message(msg)
                    await asyncio.sleep(random.uniform(0.8, 1.2))
                
                # 한국 뉴스 종목
                kr_signals = await self.momentum.scan_momentum('KR', mode='dynamic')
                for signal in kr_signals:
                    msg = self._format_momentum_alert(signal)
                    await self.send_message(msg)
                    await asyncio.sleep(random.uniform(0.8, 1.2))
                
                # 1분 주기 (랜덤 지연)
                await asyncio.sleep(random.uniform(55, 65))
                
            except Exception as e:
                logger.error(f"뉴스 종목 감시 오류: {e}")
                await asyncio.sleep(random.uniform(55, 65))
    
    async def momentum_monitor_full(self):
        """🔥 v3.1: 시장 전체 스캔 (10분 주기)"""
        logger.info("📊 시장 전체 스캔 시작 (10분 주기)")
        
        while True:
            try:
                if self.notifications_paused:
                    await asyncio.sleep(random.uniform(580, 620))
                    continue
                
                # 미국 전체
                us_signals = await self.momentum.scan_momentum('US', mode='full')
                for signal in us_signals:
                    msg = self._format_momentum_alert(signal)
                    await self.send_message(msg)
                    await asyncio.sleep(random.uniform(0.8, 1.2))
                
                # 한국 전체
                kr_signals = await self.momentum.scan_momentum('KR', mode='full')
                for signal in kr_signals:
                    msg = self._format_momentum_alert(signal)
                    await self.send_message(msg)
                    await asyncio.sleep(random.uniform(0.8, 1.2))
                
                # 10분 주기 (랜덤 지연)
                await asyncio.sleep(random.uniform(580, 620))
                
            except Exception as e:
                logger.error(f"시장 전체 스캔 오류: {e}")
                await asyncio.sleep(random.uniform(580, 620))
    
    def _format_news_alert(self, news, analysis):
        """뉴스 알림 포맷"""
        score = analysis.get('score', 0)
        certainty = analysis.get('certainty', 'uncertain')
        summary = analysis.get('summary', '')
        key_catalyst = analysis.get('key_catalyst', '')
        
        cert_emoji = "✅" if certainty == "confirmed" else "⚠️"
        
        msg = f"🔥 급등 가능성 {score}/10\n"
        msg += f"{cert_emoji} {certainty.upper()}\n\n"
        msg += f"📰 {news['title']}\n\n"
        msg += f"💡 {summary}\n"
        msg += f"🎯 재료: {key_catalyst}\n\n"
        
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            msg += "📊 수혜주:\n"
            for rec in recommendations[:3]:
                rank = rec.get('rank', '')
                ticker = rec.get('ticker', 'UNKNOWN')
                name = rec.get('name', 'Unknown')
                reason = rec.get('reason', '')
                
                msg += f"  {rank}: {name} ({ticker})\n"
                msg += f"  → {reason}\n"
        
        msg += f"\n🔗 {news.get('url', 'N/A')}\n"
        msg += f"⏰ {news.get('published_time_kst', 'N/A')}"
        
        return msg
    
    def _format_momentum_alert(self, signal):
        """급등주 알림 포맷"""
        ticker = signal.get('ticker', 'UNKNOWN')
        name = signal.get('name', 'Unknown')
        reason = signal.get('reason', '')
        change_pct = signal.get('change_percent', 0)
        volume_ratio = signal.get('volume_ratio', 0)
        alert_type = signal.get('alert_type', 'realtime_surge')
        
        # 뉴스 종목이면 🔥 표시
        fire_emoji = "🔥🔥" if alert_type == 'dynamic_surge' else "🔥"
        
        msg = f"{fire_emoji} 급등 포착!\n\n"
        msg += f"📊 {name} ({ticker})\n"
        msg += f"💹 {change_pct:+.1f}%\n"
        msg += f"📈 거래량 {volume_ratio:.1f}배\n\n"
        msg += f"💡 {reason}\n"
        msg += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        
        return msg
    
    def _format_daily_report(self, report, title):
        """일일 리포트 포맷"""
        msg = f"━━━━━━━━━━━━━━━━\n"
        msg += f"{title}\n"
        msg += f"📅 {report['date'].strftime('%Y-%m-%d')}\n"
        msg += f"━━━━━━━━━━━━━━━━\n\n"
        
        events = report.get('events_today', [])
        if events:
            msg += f"📋 주요 이벤트 ({len(events)}건)\n\n"
            for event in events[:5]:
                ticker = event.get('ticker', 'UNKNOWN')
                name = event.get('name', 'Unknown')
                reason = event.get('reason', '')
                confidence = event.get('confidence', 0)
                
                msg += f"• {name} ({ticker})\n"
                msg += f"  {reason}\n"
                msg += f"  신뢰도: {confidence*100:.0f}%\n\n"
        else:
            msg += "📭 주요 이벤트 없음\n\n"
        
        risks = report.get('risks', [])
        if risks:
            msg += "⚠️ 리스크:\n"
            for risk in risks:
                msg += f"  • {risk}\n"
        
        return msg
    
    async def send_message(self, text):
        """메시지 전송"""
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=None
            )
        except Exception as e:
            logger.error(f"메시지 전송 실패: {e}")
    
    async def run_forever(self):
        """무한 실행"""
        try:
            await self.start()
            
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("사용자 중단")
        except Exception as e:
            logger.error(f"봇 오류: {e}", exc_info=True)
        finally:
            if self.app:
                await self.app.stop()
                await self.app.shutdown()
