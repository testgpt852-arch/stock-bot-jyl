# -*- coding: utf-8 -*-
"""
Telegram Bot - Production
- 모든 import: 버전 접미사 제거된 표준 파일명 사용
- top_ticker 연동: AI가 지목한 1등 대장주를 즉시 모멘텀 트래커 동적 감시 목록에 추가
- 이중 스캔 모드: 뉴스 종목 1분 / 시장 전체 10분
"""

import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import Config
import random

from ai_brain import AIBrain
from news_engine import NewsEngine
from momentum_tracker import MomentumTracker, AlertPriority
from predictor_engine import PredictorEngine

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self):
        self.app = None
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.notifications_paused = False
        self.seen_filings = set()

        try:
            self.ai       = AIBrain()
            self.news_engine = NewsEngine(self.ai)
            self.momentum = MomentumTracker()
            self.predictor = PredictorEngine()
            logger.info("✅ 모든 엔진 초기화 성공")
        except Exception as e:
            logger.error(f"❌ 엔진 초기화 실패: {e}")
            raise

        logger.info("🐺 Telegram Bot (Production) 초기화")

    # ─────────────────────────────────────────────
    # 봇 시작
    # ─────────────────────────────────────────────
    async def start(self):
        try:
            self.app = Application.builder().token(Config.TELEGRAM_TOKEN).build()

            self.app.add_handler(CommandHandler("start",   self.cmd_start))
            self.app.add_handler(CommandHandler("analyze", self.cmd_analyze))
            self.app.add_handler(CommandHandler("report",  self.cmd_report))
            self.app.add_handler(CommandHandler("status",  self.cmd_status))
            self.app.add_handler(CommandHandler("news",    self.cmd_news))
            self.app.add_handler(CommandHandler("pause",   self.cmd_pause))
            self.app.add_handler(CommandHandler("resume",  self.cmd_resume))
            self.app.add_handler(CommandHandler("help",    self.cmd_help))
            self.app.add_handler(CommandHandler("stats",   self.cmd_stats))

            await self.app.initialize()
            await self.app.start()

            asyncio.create_task(self.schedule_reports())
            asyncio.create_task(self.news_monitor())
            asyncio.create_task(self.momentum_monitor_dynamic())  # 1분 주기
            asyncio.create_task(self.momentum_monitor_full())     # 10분 주기

            logger.info("✅ 봇 시작")

            await self.send_message(
                "🚀 조기경보 시스템 v3.6 (TradingView 시간대별 분기)\n\n"
                "✅ AI Brain (공격적 스캘퍼)\n"
                "✅ News Engine (미국 5대장 + 한국 3대장 + SEC)\n"
                "✅ Momentum Tracker v3.6 (TradingView 연동)\n"
                "✅ Predictor Engine (SEC Only)\n\n"
                "🔥 핵심 개선:\n"
                "• Finviz: curl_cffi Chrome TLS 위장 (차단 방지)\n"
                "• 컬럼: 동적 헤더 매핑 (인덱스 고정 제거)\n"
                "• 장전 감시: yfinance prepost=True\n"
                "• AI 대장주 → 즉시 1분 집중 감시 연동\n\n"
                "🚀 v3.6 신규 기능 (TradingView 연동):\n"
                "• 프리마켓 (18:00~23:30 KST): TradingView 단독\n"
                "• 정규장 (23:30~06:00 KST): Finviz → TradingView 백업\n"
                "• 애프터마켓 (06:00~18:00 KST): TradingView 단독\n"
                "• KST 기준 시간대별 자동 분기\n\n"
                "⏱️ 스캔 주기:\n"
                "• 뉴스 종목: 1분 (집중 감시)\n"
                "• 시장 전체: 10분 (시간대별 자동 분기)\n"
                "• 뉴스 수집: 30초\n\n"
                f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

        except Exception as e:
            logger.error(f"봇 시작 실패: {e}")
            raise

    # ─────────────────────────────────────────────
    # 명령어
    # ─────────────────────────────────────────────
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # 현재 시간대 표시 (KST 기준)
        phase = self.momentum._get_market_phase_kst()
        time_status = {
            'premarket': '🌅 프리마켓 (18:00~23:30 KST)',
            'regular': '🏛️ 정규장 (23:30~06:00 KST)',
            'afterhours': '🌙 애프터마켓 (06:00~18:00 KST)',
        }[phase]
        
        await update.message.reply_text(
            "🐺 조기경보 시스템 v3.6 (TradingView 시간대별 분기)\n\n"
            "📱 명령어:\n"
            "• /analyze [종목명] - 종목 분석\n"
            "• /report - 즉시 리포트\n"
            "• /status - 시스템 상태\n"
            "• /stats - 알림 통계\n"
            "• /news - 최근 뉴스 TOP 5\n"
            "• /pause - 알림 일시 정지\n"
            "• /resume - 알림 재개\n"
            "• /help - 도움말\n\n"
            f"🕐 현재 시간대: {time_status}\n"
            f"💡 알림: {'⏸️ 일시정지' if self.notifications_paused else '▶️ 활성화'}\n"
            f"🔍 US 동적 감시: {len(self.momentum.dynamic_tickers_us)}개\n"
            f"🔍 KR 동적 감시: {len(self.momentum.dynamic_tickers_kr)}개\n\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.notifications_paused = True
        await update.message.reply_text("⏸️ 알림 일시 정지\n\n💡 /resume으로 재개")
        logger.info("⏸️ 알림 일시 정지")

    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.notifications_paused = False
        await update.message.reply_text("▶️ 알림 재개!\n\n🐺 Beast Mode 가동!")
        logger.info("▶️ 알림 재개")

    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(
                "사용법:\n/analyze 삼성전자\n/analyze AAPL\n/analyze 005930"
            )
            return

        ticker = ' '.join(context.args)
        await update.message.reply_text(f"🔍 {ticker} 분석 중...")

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

            symbol = ticker_map.get(ticker.lower(), f"{ticker}.KS" if ticker.isdigit() else ticker.upper())
            stock  = yf.Ticker(symbol)
            # prepost=True
            hist   = stock.history(period='5d', prepost=True)

            if hist.empty:
                await update.message.reply_text(f"⚠️ {ticker} 데이터를 찾을 수 없습니다.")
                return

            current      = hist['Close'].iloc[-1]
            prev         = hist['Close'].iloc[-2] if len(hist) > 1 else current
            change       = current - prev
            change_pct   = (change / prev) * 100 if prev != 0 else 0
            volume       = hist['Volume'].iloc[-1]
            avg_volume   = hist['Volume'].mean()
            volume_ratio = volume / avg_volume if avg_volume > 0 else 0

            msg = (
                f"📊 {ticker} 분석 결과\n\n"
                f"현재가: {current:,.2f} ({change:+.2f}, {change_pct:+.2f}%)\n"
                f"거래량: {volume:,.0f} (평균 대비 {volume_ratio:.1f}배)\n\n"
                f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            await update.message.reply_text(msg)

        except Exception as e:
            logger.error(f"/analyze 오류: {e}")
            await update.message.reply_text(f"⚠️ 분석 중 오류: {str(e)}")

    async def cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📊 리포트 생성 중...")
        try:
            report = await self.predictor.generate_daily_report('US')
            await update.message.reply_text(self._format_daily_report(report, '🇺🇸 미국'))
        except Exception as e:
            logger.error(f"/report 오류: {e}")
            await update.message.reply_text(f"⚠️ 리포트 생성 실패: {str(e)}")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            phase = self.momentum._get_market_phase_kst()
            time_status = {
                'premarket': '🌅 프리마켓 (18:00~23:30 KST)',
                'regular': '🏛️ 정규장 (23:30~06:00 KST)',
                'afterhours': '🌙 애프터마켓 (06:00~18:00 KST)',
            }[phase]
            
            msg = (
                "🐺 시스템 상태 v3.6 (TradingView 연동)\n\n"
                f"알림: {'⏸️ 일시정지' if self.notifications_paused else '▶️ 활성화'}\n"
                f"🕐 현재 시간대: {time_status}\n\n"
                "AI Brain\n"
                f"✅ 페르소나: 공격적 스캘퍼\n"
                f"✅ 모델: {', '.join(self.ai.scanner_models[:2])}\n\n"
                "News Engine\n"
                f"✅ 소스: {len(self.news_engine.sources)}개\n"
                f"✅ 중복 체크: {len(self.news_engine.seen_urls)}개\n\n"
                "Momentum Tracker v3.6\n"
                f"✅ TradingView 시간대별 자동 분기 (KST)\n"
                f"✅ Finviz: curl_cffi (Chrome TLS 위장)\n"
                f"✅ 동적 컬럼 매핑 활성화\n"
                f"✅ prepost=True (장전 감시)\n"
                f"✅ US 동적 감시: {len(self.momentum.dynamic_tickers_us)}개\n"
                f"✅ KR 동적 감시: {len(self.momentum.dynamic_tickers_kr)}개\n\n"
                "시간대별 정책:\n"
                f"• 프리마켓: TradingView 단독\n"
                f"• 정규장: Finviz → TradingView 백업\n"
                f"• 애프터마켓: TradingView 단독\n\n"
                "백그라운드\n"
                "✅ 뉴스 수집: 30초\n"
                "✅ 뉴스 종목 감시: 1분\n"
                "✅ 시장 전체 스캔: 10분 (시간대별 분기)\n"
                "✅ 리포트: 23:00\n\n"
                f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            await update.message.reply_text(msg)
        except Exception as e:
            logger.error(f"/status 오류: {e}")
            await update.message.reply_text(f"⚠️ 상태 조회 실패: {str(e)}")

    async def cmd_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await update.message.reply_text("📰 최근 뉴스 조회 중...")
            news_list = await self.news_engine.scan_all_sources()

            if not news_list:
                await update.message.reply_text("📭 최근 뉴스가 없습니다.")
                return

            msg = "📰 최근 뉴스 TOP 5\n\n"
            for i, news in enumerate(news_list[:5], 1):
                emoji = "📋" if news.get('type') == 'filing' else "📰"
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
        await update.message.reply_text(
            "📚 조기경보 시스템 v3.6 (TradingView 시간대별 분기)\n\n"
            "📱 명령어:\n"
            "• /start   - 메뉴판\n"
            "• /analyze - 종목 분석\n"
            "• /report  - 즉시 리포트\n"
            "• /status  - 시스템 상태\n"
            "• /stats   - 알림 통계\n"
            "• /news    - 최근 뉴스 TOP 5\n"
            "• /pause   - 알림 일시 정지\n"
            "• /resume  - 알림 재개\n"
            "• /help    - 이 도움말\n\n"
            "⏰ 자동 알림:\n"
            "• 23:00 - 미국장 저녁 브리핑\n"
            "• 장중  - 뉴스 수집 (30초)\n"
            "• 장중  - 뉴스 종목 감시 (1분)\n"
            "• 장중  - 시장 전체 스캔 (10분, 시간대별 분기)\n\n"
            "🚀 v3.6 시간대별 정책 (KST 기준):\n"
            "• 프리마켓 (18:00~23:30): TradingView 단독\n"
            "• 정규장 (23:30~06:00): Finviz → TradingView 백업\n"
            "• 애프터마켓 (06:00~18:00): TradingView 단독\n\n"
            "🎯 24시간 빈틈없는 급등주 포착!"
        )

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await update.message.reply_text(self.momentum.get_stats_summary())
        except Exception as e:
            logger.error(f"/stats 오류: {e}")
            await update.message.reply_text(f"⚠️ 통계 조회 실패: {str(e)}")

    # ─────────────────────────────────────────────
    # 백그라운드 작업
    # ─────────────────────────────────────────────
    async def schedule_reports(self):
        logger.info("📅 스케줄러 시작")
        while True:
            try:
                await asyncio.sleep(random.uniform(25, 35))
                now = datetime.now()
                if now.hour == 23 and now.minute == 0:
                    await self.send_evening_report_us()
                    await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"스케줄러 오류: {e}")
                await asyncio.sleep(60)

    async def send_evening_report_us(self):
        try:
            report  = await self.predictor.generate_daily_report('US')
            message = self._format_daily_report(report, '🇺🇸 미국장 저녁 브리핑')
            await self.send_message(message)
        except Exception as e:
            logger.error(f"미국 리포트 오류: {e}")

    async def news_monitor(self):
        """
        뉴스 모니터 (30초 주기)
        AI가 분석한 top_ticker를 즉시 모멘텀 트래커 동적 감시 목록에 추가 → 1분 집중 감시
        """
        logger.info("📰 뉴스 모니터 시작")
        while True:
            try:
                if self.notifications_paused:
                    await asyncio.sleep(random.uniform(25, 35))
                    continue

                news_list = await self.news_engine.scan_all_sources()

                for news in news_list[:5]:
                    try:
                        # 1차 빠른 필터
                        passes_quick = await self.ai.quick_score(news['title'], threshold=8.0)
                        if not passes_quick:
                            continue

                        # 2차 상세 분석
                        analysis = await self.ai.analyze_news_signal(news)
                        if not analysis:
                            continue

                        market = news.get('market', 'US')

                        # ✅ [핵심] AI가 지목한 1등 대장주 top_ticker → 즉시 동적 감시 추가
                        top_ticker = analysis.get('top_ticker')
                        top_market = analysis.get('top_ticker_market', market)
                        if top_ticker and top_ticker not in (None, 'null', 'UNKNOWN', ''):
                            self.momentum.add_dynamic_ticker(top_ticker, top_market)
                            logger.info(f"🎯 AI 대장주 동적 감시 등록: {top_ticker} ({top_market})")

                        # 뉴스에 명시된 종목도 추가
                        ticker_in_news = analysis.get('ticker_in_news')
                        if ticker_in_news and ticker_in_news not in (None, 'null', 'UNKNOWN', ''):
                            self.momentum.add_dynamic_ticker(ticker_in_news, market)

                        # 추천 종목 2등, 3등도 추가
                        for rec in analysis.get('recommendations', [])[1:3]:
                            t = rec.get('ticker', 'UNKNOWN')
                            if t and t not in ('UNKNOWN', '', None):
                                self.momentum.add_dynamic_ticker(t, market)

                        # 알림 전송
                        msg = self._format_news_alert(news, analysis)
                        await self.send_message(msg)
                        await asyncio.sleep(random.uniform(0.8, 1.2))

                    except Exception as e:
                        logger.debug(f"뉴스 처리 오류: {e}")

                await asyncio.sleep(random.uniform(25, 35))

            except Exception as e:
                logger.error(f"뉴스 모니터 오류: {e}")
                await asyncio.sleep(random.uniform(55, 65))

    async def momentum_monitor_dynamic(self):
        """뉴스 종목 집중 감시 (1분 주기)"""
        logger.info("🔥 뉴스 종목 감시 시작 (1분 주기)")
        while True:
            try:
                if self.notifications_paused:
                    await asyncio.sleep(random.uniform(55, 65))
                    continue

                for market in ('US', 'KR'):
                    signals = await self.momentum.scan_momentum(market, mode='dynamic')
                    for signal in signals:
                        await self.send_message(self._format_momentum_alert(signal))
                        await asyncio.sleep(random.uniform(0.8, 1.2))

                await asyncio.sleep(random.uniform(55, 65))

            except Exception as e:
                logger.error(f"뉴스 종목 감시 오류: {e}")
                await asyncio.sleep(random.uniform(55, 65))

    async def momentum_monitor_full(self):
        """시장 전체 스캔 (10분 주기)"""
        logger.info("📊 시장 전체 스캔 시작 (10분 주기)")
        while True:
            try:
                if self.notifications_paused:
                    await asyncio.sleep(random.uniform(580, 620))
                    continue

                for market in ('US', 'KR'):
                    signals = await self.momentum.scan_momentum(market, mode='full')
                    for signal in signals:
                        await self.send_message(self._format_momentum_alert(signal))
                        await asyncio.sleep(random.uniform(0.8, 1.2))

                # 메모리 정리 (전체 스캔마다)
                self.momentum.cleanup_alerts()

                await asyncio.sleep(random.uniform(580, 620))

            except Exception as e:
                logger.error(f"시장 전체 스캔 오류: {e}")
                await asyncio.sleep(random.uniform(580, 620))

    # ─────────────────────────────────────────────
    # 메시지 포맷
    # ─────────────────────────────────────────────
    def _format_news_alert(self, news: dict, analysis: dict) -> str:
        score        = analysis.get('score', 0)
        certainty    = analysis.get('certainty', 'uncertain')
        summary      = analysis.get('summary', '')
        key_catalyst = analysis.get('key_catalyst', '')
        top_ticker   = analysis.get('top_ticker')
        cert_emoji   = "✅" if certainty == "confirmed" else "⚠️"

        msg = (
            f"🔥 급등 가능성 {score}/10\n"
            f"{cert_emoji} {certainty.upper()}\n\n"
            f"📰 {news['title']}\n\n"
            f"💡 {summary}\n"
            f"🎯 재료: {key_catalyst}\n"
        )

        # AI 대장주 강조
        if top_ticker and top_ticker not in (None, 'null', 'UNKNOWN', ''):
            top_market = analysis.get('top_ticker_market', 'US')
            msg += f"\n🎯 AI 대장주: {top_ticker} ({top_market}) → 1분 집중 감시 시작\n"

        recs = analysis.get('recommendations', [])
        if recs:
            msg += "\n📊 수혜주:\n"
            for rec in recs[:3]:
                ticker = rec.get('ticker', 'UNKNOWN')
                name   = rec.get('name', 'Unknown')
                reason = rec.get('reason', '')
                rank   = rec.get('rank', '')
                msg += f"  {rank}: {name} ({ticker})\n"
                msg += f"  → {reason}\n"

        msg += (
            f"\n🔗 {news.get('url', 'N/A')}\n"
            f"⏰ {news.get('published_time_kst', 'N/A')}"
        )
        return msg

    def _format_momentum_alert(self, signal: dict) -> str:
        ticker       = signal.get('ticker', 'UNKNOWN')
        name         = signal.get('name', 'Unknown')
        reason       = signal.get('reason', '')
        change_pct   = signal.get('change_percent', 0)
        volume_ratio = signal.get('volume_ratio', 0)
        market       = signal.get('market', 'US')
        source       = signal.get('source', '')

        priority_emoji = signal.get('priority_emoji', '🔥')
        market_flag    = "🇺🇸" if market == 'US' else "🇰🇷"
        source_text    = f" [{source.upper()}]" if source else ""

        return (
            f"{priority_emoji} 급등 포착!{source_text}\n\n"
            f"{market_flag} {name} ({ticker})\n"
            f"💹 {change_pct:+.1f}%\n"
            f"📈 거래량 {volume_ratio:.1f}배\n\n"
            f"💡 {reason}\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )

    def _format_daily_report(self, report: dict, title: str) -> str:
        msg = (
            f"━━━━━━━━━━━━━━━━\n"
            f"{title}\n"
            f"📅 {report['date'].strftime('%Y-%m-%d')}\n"
            f"━━━━━━━━━━━━━━━━\n\n"
        )

        events = report.get('events_today', [])
        if events:
            msg += f"📋 주요 이벤트 ({len(events)}건)\n\n"
            for event in events[:5]:
                msg += (
                    f"• {event.get('name', 'Unknown')} ({event.get('ticker', 'UNKNOWN')})\n"
                    f"  {event.get('reason', '')}\n"
                    f"  신뢰도: {event.get('confidence', 0)*100:.0f}%\n\n"
                )
        else:
            msg += "📭 주요 이벤트 없음\n\n"

        risks = report.get('risks', [])
        if risks:
            msg += "⚠️ 리스크:\n"
            for risk in risks:
                msg += f"  • {risk}\n"

        return msg

    # ─────────────────────────────────────────────
    # 메시지 전송
    # ─────────────────────────────────────────────
    async def send_message(self, text: str):
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=None,
            )
        except Exception as e:
            logger.error(f"메시지 전송 실패: {e}")

    async def run_forever(self):
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
