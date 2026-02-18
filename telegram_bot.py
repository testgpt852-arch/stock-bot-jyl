# -*- coding: utf-8 -*-
"""
Telegram Bot (Production)
- ✅ 모든 import 표준화 (버전 접미사 제거)
- ✅ top_ticker → add_dynamic_ticker 즉시 연동 (AI 대장주 집중 감시)
- ✅ 이중 스캔 모드: 뉴스 종목 1분 / 시장 전체 10분
- ✅ 알림 우선순위 표시 (🚨🚨🚨 / 🔥🔥 / 🔥 / 📊)
- ✅ /stats 명령어 (통계 대시보드)
"""

import asyncio
import logging
import random
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import Config

# ── 표준화된 파일명으로 import ──
from ai_brain import AIBrainV3
from news_engine import NewsEngineV3
from momentum_tracker import MomentumTracker, AlertPriority
from predictor_engine import PredictorEngineV3

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self):
        self.app = None
        self.chat_id = Config.TELEGRAM_CHAT_ID

        # 알림 제어
        self.notifications_paused = False

        # 중복 방지
        self.seen_filings = set()

        # 엔진 초기화
        try:
            self.ai        = AIBrainV3()
            self.news_engine = NewsEngineV3(self.ai)
            self.momentum  = MomentumTracker()
            self.predictor = PredictorEngineV3()
            logger.info("✅ 모든 엔진 초기화 성공 (Production)")
        except Exception as e:
            logger.error(f"❌ 엔진 초기화 실패: {e}")
            raise

        logger.info("🚀 Telegram Bot (Production) 초기화")

    # ────────────────────────────────────────────
    # 봇 시작
    # ────────────────────────────────────────────
    async def start(self):
        try:
            self.app = Application.builder().token(Config.TELEGRAM_TOKEN).build()

            # 명령어 핸들러 등록
            handlers = [
                ("start",   self.cmd_start),
                ("analyze", self.cmd_analyze),
                ("report",  self.cmd_report),
                ("status",  self.cmd_status),
                ("news",    self.cmd_news),
                ("pause",   self.cmd_pause),
                ("resume",  self.cmd_resume),
                ("help",    self.cmd_help),
                ("stats",   self.cmd_stats),
            ]
            for cmd, handler in handlers:
                self.app.add_handler(CommandHandler(cmd, handler))

            await self.app.initialize()
            await self.app.start()

            # 백그라운드 태스크
            asyncio.create_task(self.schedule_reports())
            asyncio.create_task(self.news_monitor())
            asyncio.create_task(self.momentum_monitor_dynamic())  # 1분 주기
            asyncio.create_task(self.momentum_monitor_full())     # 10분 주기

            logger.info("✅ 봇 시작 (Production)")

            await self.send_message(
                "🚀 조기경보 시스템 Production 시작!\n\n"
                "✅ AI Brain: 대장주 지목 + top_ticker 연동\n"
                "✅ News Engine: 미국 5대장 + 한국 3대장 + SEC\n"
                "✅ Momentum Tracker: Finviz(curl_cffi) + 장전 감지\n"
                "✅ Predictor Engine: SEC Form4 + 13D/G\n\n"
                "⚡ 핵심 연동 플로우:\n"
                "  뉴스 호재 → AI 대장주 지목(top_ticker)\n"
                "  → 즉시 1분 집중 감시 모드 전환 🎯\n"
                "  → 급등 초입 포착 알림\n\n"
                "📊 모니터링:\n"
                "  🇺🇸 미국: AI 지목 종목만 (1분 주기)\n"
                "  🇰🇷 한국: 전체 급등주 (2분 주기)\n\n"
                "🎯 노이즈 제거 완료: 미국 Finviz 페니스탁 알림 OFF!"
            )

        except Exception as e:
            logger.error(f"봇 시작 실패: {e}")
            raise

    # ────────────────────────────────────────────
    # 명령어 핸들러
    # ────────────────────────────────────────────
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🚀 조기경보 시스템 Production\n\n"
            "📱 명령어:\n"
            "• /analyze [종목명] - 종목 분석\n"
            "• /report - 즉시 리포트\n"
            "• /status - 시스템 상태\n"
            "• /stats - 📊 알림 통계\n"
            "• /news - 최근 뉴스 TOP 5\n"
            "• /pause - 알림 일시 정지\n"
            "• /resume - 알림 재개\n"
            "• /help - 전체 도움말\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚡ 실시간 모니터링:\n"
            "  뉴스 종목 AI 지목 → 1분 집중 감시 🎯\n"
            "  시장 전체 스캔 → 10분 주기\n\n"
            f"💡 현재 상태:\n"
            f"  알림: {'⏸️ 일시정지' if self.notifications_paused else '▶️ 활성화'}\n"
            f"  집중 감시 (US): {len(self.momentum.dynamic_tickers_us)}개\n"
            f"  집중 감시 (KR): {len(self.momentum.dynamic_tickers_kr)}개\n\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.notifications_paused = True
        await update.message.reply_text(
            "⏸️ 알림이 일시 정지되었습니다.\n\n"
            "💡 /resume 으로 재개"
        )
        logger.info("⏸️ 알림 일시 정지")

    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.notifications_paused = False
        await update.message.reply_text(
            "▶️ 알림이 다시 시작되었습니다!\n\n"
            "• 뉴스 알림: 활성화\n"
            "• 급등 알림: 활성화\n\n"
            "🐺 Beast Mode 가동!"
        )
        logger.info("▶️ 알림 재개")

    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(
                "사용법:\n"
                "/analyze 삼성전자\n"
                "/analyze AAPL\n"
                "/analyze 005930"
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

            symbol = ticker_map.get(ticker.lower())
            if not symbol:
                symbol = f"{ticker}.KS" if ticker.isdigit() else ticker.upper()

            stock = yf.Ticker(symbol)
            hist  = stock.history(period='5d', prepost=True)

            if hist.empty:
                await update.message.reply_text(f"⚠️ {ticker} 데이터를 찾을 수 없습니다.")
                return

            current    = hist['Close'].iloc[-1]
            prev       = hist['Close'].iloc[-2] if len(hist) > 1 else current
            change     = current - prev
            change_pct = (change / prev) * 100 if prev != 0 else 0
            volume     = hist['Volume'].iloc[-1]
            avg_vol    = hist['Volume'].mean()
            vol_ratio  = volume / avg_vol if avg_vol > 0 else 0

            msg  = f"📊 {ticker} 분석 결과\n\n"
            msg += f"현재가: {current:,.2f} ({change:+.2f}, {change_pct:+.2f}%)\n"
            msg += f"거래량: {volume:,.0f} (평균 대비 {vol_ratio:.1f}배)\n\n"
            msg += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            await update.message.reply_text(msg)

        except Exception as e:
            logger.error(f"/analyze 오류: {e}")
            await update.message.reply_text(f"⚠️ 분석 중 오류 발생: {str(e)}")

    async def cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📊 리포트 생성 중...")
        try:
            us_report = await self.predictor.generate_daily_report('US')
            us_msg    = self._format_daily_report(us_report, '🇺🇸 미국')
            await update.message.reply_text(us_msg)
        except Exception as e:
            logger.error(f"리포트 생성 오류: {e}")
            await update.message.reply_text(f"⚠️ 리포트 생성 실패: {str(e)}")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            status_emoji = "⏸️ 일시정지" if self.notifications_paused else "▶️ 활성화"

            msg  = "🚀 시스템 상태 (Production)\n\n"
            msg += f"알림: {status_emoji}\n\n"
            msg += f"🧠 AI Brain\n"
            msg += f"  ✅ 모델: {', '.join(self.ai.scanner_models[:2])}\n"
            msg += f"  ✅ top_ticker 연동: 활성화\n\n"
            msg += f"📰 News Engine\n"
            msg += f"  ✅ 소스: {len(self.news_engine.sources)}개\n"
            msg += f"  ✅ 중복 체크: {len(self.news_engine.seen_urls)}개\n\n"
            msg += f"📊 Momentum Tracker\n"
            msg += f"  ✅ Finviz: curl_cffi TLS 위장\n"
            msg += f"  ✅ 집중 감시 US: {len(self.momentum.dynamic_tickers_us)}개\n"
            msg += f"  ✅ 집중 감시 KR: {len(self.momentum.dynamic_tickers_kr)}개\n"
            msg += f"  ✅ 총 알림: {self.momentum.stats['total_alerts']}건\n\n"
            msg += f"⏱️ 스캔 주기\n"
            msg += f"  ✅ 뉴스: 30초\n"
            msg += f"  ✅ 미국 AI 지목 종목: 1분 🎯\n"
            msg += f"  ✅ 한국 전체: 2분\n"
            msg += f"  ❌ 미국 전체: OFF (노이즈 제거)\n\n"
            msg += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

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
            "📚 조기경보 시스템 Production\n\n"
            "📱 명령어:\n"
            "• /start - 메뉴판\n"
            "• /analyze 종목명 - 종목 분석\n"
            "• /report - 즉시 리포트\n"
            "• /status - 시스템 상태\n"
            "• /stats - 📊 알림 통계\n"
            "• /news - 최근 뉴스 TOP 5\n"
            "• /pause - 알림 일시 정지\n"
            "• /resume - 알림 재개\n"
            "• /help - 이 도움말\n\n"
            "⏰ 자동 알림:\n"
            "• 23:00 - 미국장 저녁 브리핑\n"
            "• 30초 - 실시간 뉴스 스캔\n"
            "• 1분  - AI 지목 종목 집중 감시 🎯 (미국)\n"
            "• 2분  - 한국 전체 급등주 스캔\n\n"
            "⚡ AI 대장주 연동:\n"
            "• 호재 뉴스 → AI가 top_ticker 지목\n"
            "• 즉시 1분 집중 감시 등록\n"
            "• 급등 초입 포착 알림\n\n"
            "🔥 알림 우선순위:\n"
            "  🚨🚨🚨 CRITICAL: AI 지목 + 20%↑ + 거래량 10배\n"
            "  🔥🔥   HIGH: AI 지목 종목 급등\n"
            "  🔥     MEDIUM: 시장 전체 급등\n"
            "  📊     LOW: 프로그램/테마\n\n"
            "🎯 RIME 급등주 선취매!"
        )

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            stats_text = self.momentum.get_stats_summary()
            await update.message.reply_text(stats_text)
        except Exception as e:
            logger.error(f"/stats 오류: {e}")
            await update.message.reply_text(f"⚠️ 통계 조회 실패: {str(e)}")

    # ────────────────────────────────────────────
    # 스케줄러 / 모니터
    # ────────────────────────────────────────────
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
        ✅ top_ticker 연동: AI가 지목한 대장주를 즉시 1분 집중 감시 등록
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
                        passes_quick = await self.ai.quick_score(news['title'], threshold=8.0)
                        if not passes_quick:
                            continue

                        analysis = await self.ai.analyze_news_signal(news)
                        if not analysis:
                            continue

                        market = news.get('market', 'US')

                        # ✅ [핵심] AI가 직접 지목한 대장주 → 즉시 1분 집중 감시 등록
                        top_ticker = analysis.get('top_ticker')
                        if top_ticker:
                            self.momentum.add_dynamic_ticker(top_ticker, market)
                            logger.info(f"🎯 AI 대장주 집중 감시 등록: {top_ticker} ({market})")

                        # 뉴스에 명시된 종목도 추가
                        ticker_in_news = analysis.get('ticker_in_news')
                        if ticker_in_news and ticker_in_news != 'null':
                            self.momentum.add_dynamic_ticker(ticker_in_news, market)

                        # AI 추천 종목도 추가 (최대 3개)
                        for rec in analysis.get('recommendations', [])[:3]:
                            rec_ticker = rec.get('ticker', 'UNKNOWN')
                            if rec_ticker not in ('UNKNOWN', '', None):
                                self.momentum.add_dynamic_ticker(rec_ticker, market)

                        # 알림 발송
                        msg = self._format_news_alert(news, analysis)
                        await self.send_message(msg)
                        await asyncio.sleep(random.uniform(0.8, 1.2))

                    except Exception as e:
                        logger.debug(f"뉴스 처리 오류: {e}")
                        continue

                await asyncio.sleep(random.uniform(25, 35))

            except Exception as e:
                logger.error(f"뉴스 모니터 오류: {e}")
                await asyncio.sleep(random.uniform(55, 65))

    async def momentum_monitor_dynamic(self):
        """AI 지목 + 뉴스 종목 집중 감시 (1분 주기)"""
        logger.info("🎯 AI 지목 종목 집중 감시 시작 (1분 주기)")

        while True:
            try:
                if self.notifications_paused:
                    await asyncio.sleep(random.uniform(55, 65))
                    continue

                # 미국 AI 지목 종목
                us_signals = await self.momentum.scan_momentum('US', mode='dynamic')
                for signal in us_signals:
                    await self.send_message(self._format_momentum_alert(signal))
                    await asyncio.sleep(random.uniform(0.8, 1.2))

                # 한국 AI 지목 종목
                kr_signals = await self.momentum.scan_momentum('KR', mode='dynamic')
                for signal in kr_signals:
                    await self.send_message(self._format_momentum_alert(signal))
                    await asyncio.sleep(random.uniform(0.8, 1.2))

                await asyncio.sleep(random.uniform(55, 65))

            except Exception as e:
                logger.error(f"집중 감시 오류: {e}")
                await asyncio.sleep(random.uniform(55, 65))

    async def momentum_monitor_full(self):
        """
        한국 전체 스캔 ONLY (2분 주기)
        ✅ 미국 전체 스캔 제거 (동적 모멘텀만 유지)
        ✅ 한국 10분 → 2분으로 변경
        """
        logger.info("📊 한국 전체 스캔 시작 (2분 주기)")

        while True:
            try:
                if self.notifications_paused:
                    await asyncio.sleep(random.uniform(115, 125))
                    continue

                # ✅ 미국 전체 스캔 완전 제거 (동적 모멘텀만 유지)
                # us_signals = await self.momentum.scan_momentum('US', mode='full')  # 삭제!

                # ✅ 한국만 스캔 (2분 주기)
                kr_signals = await self.momentum.scan_momentum('KR', mode='full')
                for signal in kr_signals:
                    await self.send_message(self._format_momentum_alert(signal))
                    await asyncio.sleep(random.uniform(0.8, 1.2))

                # 메모리 정리
                self.momentum.cleanup_alerts()

                # ✅ 2분 주기 (115~125초)
                await asyncio.sleep(random.uniform(115, 125))

            except Exception as e:
                logger.error(f"한국 전체 스캔 오류: {e}")
                await asyncio.sleep(random.uniform(115, 125))

    # ────────────────────────────────────────────
    # 메시지 포맷
    # ────────────────────────────────────────────
    def _format_news_alert(self, news: dict, analysis: dict) -> str:
        score       = analysis.get('score', 0)
        certainty   = analysis.get('certainty', 'uncertain')
        summary     = analysis.get('summary', '')
        key_catalyst = analysis.get('key_catalyst', '')
        top_ticker  = analysis.get('top_ticker')

        cert_emoji = "✅" if certainty == "confirmed" else "⚠️"

        msg  = f"🔥 급등 가능성 {score}/10\n"
        msg += f"{cert_emoji} {certainty.upper()}\n\n"
        msg += f"📰 {news['title']}\n\n"
        msg += f"💡 {summary}\n"
        msg += f"🎯 재료: {key_catalyst}\n\n"

        # ✅ AI 대장주 표시
        if top_ticker:
            msg += f"👑 AI 대장주: {top_ticker} → 1분 집중 감시 등록!\n\n"

        recommendations = analysis.get('recommendations', [])
        if recommendations:
            msg += "📊 수혜주:\n"
            for rec in recommendations[:3]:
                rank   = rec.get('rank', '')
                ticker = rec.get('ticker', 'UNKNOWN')
                name   = rec.get('name', 'Unknown')
                reason = rec.get('reason', '')
                msg += f"  {rank}: {name} ({ticker})\n"
                msg += f"  → {reason}\n"

        msg += f"\n🔗 {news.get('url', 'N/A')}\n"
        msg += f"⏰ {news.get('published_time_kst', 'N/A')}"
        return msg

    def _format_momentum_alert(self, signal: dict) -> str:
        ticker       = signal.get('ticker', 'UNKNOWN')
        name         = signal.get('name', 'Unknown')
        reason       = signal.get('reason', '')
        change_pct   = signal.get('change_percent', 0)
        volume_ratio = signal.get('volume_ratio', 0)
        market       = signal.get('market', 'US')
        source       = signal.get('source', '')

        # 우선순위 이모지 (없으면 alert_type 기반 fallback)
        priority_emoji = signal.get('priority_emoji')
        if not priority_emoji:
            priority_emoji = "🔥🔥" if signal.get('alert_type') == 'dynamic_surge' else "🔥"

        market_flag = "🇺🇸" if market == 'US' else "🇰🇷"

        source_text = f" [{source.upper()}]" if source else ""

        msg  = f"{priority_emoji} 급등 포착!{source_text}\n\n"
        msg += f"{market_flag} {name} ({ticker})\n"
        msg += f"💹 {change_pct:+.1f}%\n"
        msg += f"📈 거래량 {volume_ratio:.1f}배\n\n"
        msg += f"💡 {reason}\n"
        msg += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        return msg

    def _format_daily_report(self, report: dict, title: str) -> str:
        msg  = f"━━━━━━━━━━━━━━━━\n"
        msg += f"{title}\n"
        msg += f"📅 {report['date'].strftime('%Y-%m-%d')}\n"
        msg += f"━━━━━━━━━━━━━━━━\n\n"

        events = report.get('events_today', [])
        if events:
            msg += f"📋 주요 이벤트 ({len(events)}건)\n\n"
            for event in events[:5]:
                ticker     = event.get('ticker', 'UNKNOWN')
                name       = event.get('name', 'Unknown')
                reason     = event.get('reason', '')
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

    # ────────────────────────────────────────────
    # 메시지 전송
    # ────────────────────────────────────────────
    async def send_message(self, text: str):
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=None,
            )
        except Exception as e:
            logger.error(f"메시지 전송 실패: {e}")

    # ────────────────────────────────────────────
    # 메인 루프
    # ────────────────────────────────────────────
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
