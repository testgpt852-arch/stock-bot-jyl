# -*- coding: utf-8 -*-
"""
Telegram Bot v2.2 - v3.0 업그레이드 (호환성 유지)
- 파일명: v2_2 (호환성)
- 내용물: v3.0 (AI 모델명 표시 + SEC 공시 구분)
"""

import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import Config

# v2.2 import (파일명 유지)
from ai_brain_v2_2 import AIBrainV2_2
from news_engine_v2_2 import NewsEngineV2_2
from momentum_tracker_v2_2 import MomentumTrackerV2_2
from predictor_engine_v2_2 import PredictorEngineV2_2

logger = logging.getLogger(__name__)

class TelegramBotV2_2:
    def __init__(self):
        self.app = None
        self.chat_id = Config.TELEGRAM_CHAT_ID
        
        # 🆕 실시간 공시 중복 방지
        self.seen_filings = set()
        
        # 엔진 초기화
        try:
            self.ai = AIBrainV2_2()
            self.news_engine = NewsEngineV2_2(self.ai)
            self.momentum = MomentumTrackerV2_2()
            self.predictor = PredictorEngineV2_2()
            
            logger.info("✅ 모든 엔진 초기화 성공")
            
        except Exception as e:
            logger.error(f"❌ 엔진 초기화 실패: {e}")
            raise
        
        logger.info("🤖 Telegram Bot v2.2 (v3.0 업그레이드 + 실시간 공시) 초기화")
    
    async def start(self):
        """봇 시작"""
        try:
            self.app = Application.builder().token(Config.TELEGRAM_TOKEN).build()
            
            # 명령어
            self.app.add_handler(CommandHandler("start", self.cmd_start))
            self.app.add_handler(CommandHandler("analyze", self.cmd_analyze))
            self.app.add_handler(CommandHandler("report", self.cmd_report))
            self.app.add_handler(CommandHandler("status", self.cmd_status))  # 🆕
            self.app.add_handler(CommandHandler("news", self.cmd_news))      # 🆕
            self.app.add_handler(CommandHandler("help", self.cmd_help))
            
            await self.app.initialize()
            await self.app.start()
            
            # 백그라운드 작업
            asyncio.create_task(self.schedule_reports())
            asyncio.create_task(self.news_monitor())
            asyncio.create_task(self.momentum_monitor())
            asyncio.create_task(self.filing_monitor_kr())   # 🆕 한국 공시 실시간
            asyncio.create_task(self.filing_monitor_us())   # 🆕 미국 공시 실시간
            
            logger.info("✅ 봇 시작")
            
            await self.send_message(
                "🚀 조기경보 시스템 v2.2 (실시간 공시 모니터링) 시작!\n\n"
                "✅ AI Brain v2.2 (3개 모델)\n"
                "✅ News Engine v2.2 (5대장 + SEC 8-K)\n"
                "✅ Momentum Tracker v2.2\n"
                "✅ Predictor Engine v2.2 (고래 추적)\n"
                "✅ 실시간 공시 모니터 🆕\n\n"
                "📊 실시간 감시 중:\n"
                "• 뉴스: 30초 주기\n"
                "• 급등: 5분 주기\n"
                "• 한국 공시: 5분 주기 🔥\n"
                "• 미국 공시: 10분 주기 🔥\n\n"
                "🎯 선취매 전략 완성!"
            )
            
        except Exception as e:
            logger.error(f"봇 시작 실패: {e}")
            raise
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시작"""
        await update.message.reply_text(
            "🤖 조기경보 시스템 v2.2 (v3.0 업그레이드)\n\n"
            "기능:\n"
            "📰 실시간 뉴스 (5대장, 30초)\n"
            "📋 SEC 8-K 공시 (단타 최상위) 🆕\n"
            "📊 급등주 감지 (5분)\n"
            "💻 프로그램 매매 추적\n"
            "🎨 테마주 연쇄 상승\n"
            "🐋 고래 지분 공시\n"
            "🔮 아침/저녁 리포트\n\n"
            "명령어:\n"
            "/analyze 삼성전자 - 종목 분석\n"
            "/report - 즉시 리포트\n"
            "/status - 시스템 상태 🆕\n"
            "/news - 최근 뉴스 조회 🆕\n"
            "/help - 도움말"
        )
    
    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """종목 분석"""
        if not context.args:
            await update.message.reply_text(
                "사용법:\n"
                "/analyze 삼성전자\n"
                "/analyze AAPL\n"
                "/analyze 005930 (종목코드)"
            )
            return
        
        ticker = ' '.join(context.args)
        await update.message.reply_text(f"🔍 **{ticker}** 분석 중...")
        
        try:
            import yfinance as yf
            
            # 종목 코드 매핑 (간단 버전)
            ticker_map = {
                '삼성전자': '005930.KS',
                'sk하이닉스': '000660.KS',
                '현대차': '005380.KS',
                'lg화학': '051910.KS',
                'naver': '035420.KS',
                '카카오': '035720.KS',
            }
            
            # 티커 변환
            search_ticker = ticker.lower()
            if search_ticker in ticker_map:
                symbol = ticker_map[search_ticker]
            elif ticker.isdigit():
                symbol = f"{ticker}.KS"
            else:
                symbol = ticker.upper()
            
            # yfinance로 데이터 가져오기
            stock = yf.Ticker(symbol)
            info = stock.info
            hist = stock.history(period='5d')
            
            if hist.empty:
                await update.message.reply_text(
                    f"⚠️ **{ticker}** 데이터를 찾을 수 없습니다.\n\n"
                    f"시도한 심볼: `{symbol}`\n\n"
                    f"다시 시도해보세요:\n"
                    f"• 한글: 삼성전자\n"
                    f"• 코드: 005930\n"
                    f"• 미국: AAPL"
                )
                return
            
            # 현재가 및 변동률
            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            change = current_price - prev_price
            change_pct = (change / prev_price) * 100
            
            volume = hist['Volume'].iloc[-1]
            avg_volume = hist['Volume'].mean()
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1
            
            # AI 분석 요청
            stock_data = {
                'name': info.get('longName', ticker),
                'symbol': symbol,
                'price': current_price,
                'change_percent': change_pct,
                'volume': volume,
                'volume_ratio': volume_ratio,
                'title': f"{ticker} 실시간 분석"
            }
            
            analysis = await self.ai.analyze_stock_manual(stock_data)
            
            if not analysis:
                await update.message.reply_text("⚠️ AI 분석 실패")
                return
            
            # 결과 메시지
            score = analysis.get('score', 0)
            recommendation = analysis.get('recommendation', 'Hold')
            
            # 이모지
            rec_emoji = {
                'Strong Buy': '🚀',
                'Buy': '✅',
                'Hold': '⏸️',
                'Sell': '⚠️',
                'Strong Sell': '🚨'
            }.get(recommendation, '📊')
            
            msg = f"📊 {ticker} 분석 결과\n\n"
            msg += f"현재가: {current_price:,.2f} ({change:+.2f}, {change_pct:+.2f}%)\n"
            msg += f"거래량: {volume:,.0f} (평균 대비 {volume_ratio:.1f}배)\n\n"
            
            msg += f"🤖 AI 분석 (모델: {analysis.get('model_used', 'unknown')})\n"
            msg += f"점수: {score}/10\n"
            msg += f"추천: {rec_emoji} {recommendation}\n\n"
            
            msg += f"요약\n{analysis.get('summary', 'N/A')}\n\n"
            
            if analysis.get('reasoning'):
                msg += f"분석 근거\n{analysis['reasoning']}\n\n"
            
            if analysis.get('entry_price'):
                msg += f"진입가: {analysis['entry_price']:,.2f}\n"
            if analysis.get('target_price'):
                msg += f"목표가: {analysis['target_price']:,.2f}\n"
            if analysis.get('stop_loss'):
                msg += f"손절가: {analysis['stop_loss']:,.2f}\n\n"
            
            risk_emoji = {
                'Low': '🟢',
                'Medium': '🟡',
                'High': '🔴',
                'Unknown': '⚪'
            }.get(analysis.get('risk_level', 'Unknown'), '⚪')
            
            msg += f"리스크: {risk_emoji} {analysis.get('risk_level', 'Unknown')}\n"
            msg += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            await update.message.reply_text(msg)
            
        except Exception as e:
            logger.error(f"/analyze 오류: {e}", exc_info=True)
            await update.message.reply_text(
                f"⚠️ 분석 중 오류 발생\n\n"
                f"{str(e)}\n\n"
                f"다시 시도하거나 다른 종목을 입력해주세요."
            )
    
    async def cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """즉시 리포트"""
        await update.message.reply_text("📊 리포트 생성 중...")
        
        try:
            kr_report = await self.predictor.generate_daily_report('KR')
            kr_msg = self._format_daily_report(kr_report, '🇰🇷 한국')
            await update.message.reply_text(kr_msg)
            
            us_report = await self.predictor.generate_daily_report('US')
            us_msg = self._format_daily_report(us_report, '🇺🇸 미국')
            await update.message.reply_text(us_msg)
            
        except Exception as e:
            logger.error(f"리포트 생성 오류: {e}")
            await update.message.reply_text(f"⚠️ 리포트 생성 실패: {str(e)}")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """🆕 시스템 상태"""
        try:
            msg = "🤖 시스템 상태\n\n"
            
            # AI 엔진
            msg += "AI Brain\n"
            msg += f"✅ 스캐너 모델: {', '.join(self.ai.scanner_models[:2])}\n"
            msg += f"✅ 리포트 모델: {self.ai.report_models[0]}\n\n"
            
            # 뉴스 엔진
            msg += "News Engine\n"
            msg += f"✅ 소스: {len(self.news_engine.sources)}개 + SEC 8-K\n"
            msg += f"✅ 중복 체크: {len(self.news_engine.seen_urls)}개 URL\n\n"
            
            # 모멘텀 트래커
            msg += "Momentum Tracker\n"
            msg += f"✅ 한국 관심종목: {len(self.momentum.kr_watchlist)}개\n"
            msg += f"✅ 미국 관심종목: {len(self.momentum.us_watchlist)}개\n\n"
            
            # 백그라운드 작업
            msg += "백그라운드 작업\n"
            msg += f"✅ 뉴스 모니터: 30초 주기\n"
            msg += f"✅ 급등 감지: 5분 주기\n"
            msg += f"✅ 리포트: 07:30, 23:00\n\n"
            
            msg += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            await update.message.reply_text(msg)
            
        except Exception as e:
            logger.error(f"/status 오류: {e}")
            await update.message.reply_text(f"⚠️ 상태 조회 실패: {str(e)}")
    
    async def cmd_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """🆕 최근 뉴스 조회"""
        try:
            await update.message.reply_text("📰 최근 뉴스 조회 중...")
            
            # 최근 뉴스 스캔
            news_list = await self.news_engine.scan_all_sources()
            
            if not news_list:
                await update.message.reply_text("📭 최근 뉴스가 없습니다.")
                return
            
            # 상위 5개만
            top_news = news_list[:5]
            
            msg = f"📰 최근 뉴스 TOP 5\n\n"
            
            for i, news in enumerate(top_news, 1):
                is_filing = news.get('type') == 'filing'
                emoji = "📋" if is_filing else "📰"
                
                msg += f"{i}. {emoji} {news['title'][:60]}...\n"
                msg += f"   출처: {news['source']}\n"
                
                if news.get('published_time_kst'):
                    msg += f"   시간: {news['published_time_kst']}\n"
                
                if news.get('url'):
                    msg += f"   링크: {news['url']}\n"
                
                msg += "\n"
            
            msg += "💡 Tip: AI 분석은 자동으로 진행됩니다."
            
            await update.message.reply_text(msg)
            
        except Exception as e:
            logger.error(f"/news 오류: {e}")
            await update.message.reply_text(f"⚠️ 뉴스 조회 실패: {str(e)}")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """도움말"""
        await update.message.reply_text(
            "📚 조기경보 시스템 v2.2 (v3.0 업그레이드)\n\n"
            "📱 명령어:\n"
            "• /start - 봇 시작\n"
            "• /analyze 삼성전자 - 종목 분석\n"
            "• /report - 즉시 리포트\n"
            "• /status - 시스템 상태 🆕\n"
            "• /news - 최근 뉴스 TOP 5 🆕\n"
            "• /help - 이 도움말\n\n"
            "⏰ 자동 알림:\n"
            "• 07:30 - 한국장 오전 브리핑\n"
            "• 23:00 - 미국장 저녁 브리핑\n"
            "• 장중 - 실시간 뉴스 (30초)\n"
            "• 장중 - 급등 감지 (5분)\n\n"
            "📊 데이터 소스:\n"
            "• 뉴스: PR, Globe, Business Wire, Benzinga\n"
            "• 공시: SEC 8-K (단타 최상위) 🔥\n"
            "• 시장: 프로그램 매매, 테마주\n\n"
            "🤖 AI 모델:\n"
            "• Gemma 3-27B (무제한 쿼터)\n"
            "• Gemini 3 Flash (고성능)\n"
            "• 3단계 fallback\n\n"
            "💡 사용 예시:\n"
            "/analyze 삼성전자\n"
            "/analyze AAPL\n"
            "/analyze 005930\n\n"
            "🎯 승률 85% 목표!"
        )
    
    async def schedule_reports(self):
        """스케줄러"""
        logger.info("📅 스케줄러 시작")
        
        while True:
            try:
                now = datetime.now()
                
                if now.hour == 7 and now.minute == 30:
                    await self.send_morning_report_kr()
                    await asyncio.sleep(60)
                
                elif now.hour == 23 and now.minute == 0:
                    await self.send_evening_report_us()
                    await asyncio.sleep(60)
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"스케줄러 오류: {e}")
                await asyncio.sleep(60)
    
    async def send_morning_report_kr(self):
        """한국 아침 리포트"""
        try:
            report = await self.predictor.generate_daily_report('KR')
            message = self._format_daily_report(report, '🇰🇷 한국장 오전 브리핑')
            await self.send_message(message)
            
        except Exception as e:
            logger.error(f"한국 리포트 오류: {e}")
    
    async def send_evening_report_us(self):
        """미국 저녁 리포트"""
        try:
            report = await self.predictor.generate_daily_report('US')
            message = self._format_daily_report(report, '🇺🇸 미국장 저녁 브리핑')
            await self.send_message(message)
            
        except Exception as e:
            logger.error(f"미국 리포트 오류: {e}")
    
    def _format_daily_report(self, report, title):
        """리포트 포맷"""
        msg = f"{title}\n"
        msg += f"📅 {report['date'].strftime('%Y-%m-%d')}\n\n"
        
        if report['events_today']:
            msg += "📰 오늘의 이벤트\n"
            for event in report['events_today']:
                msg += f"• {event}\n"
            msg += "\n"
        
        if report['hot_stocks']:
            msg += "🎯 주목 종목 TOP 5\n"
            for i, stock in enumerate(report['hot_stocks'][:5], 1):
                confidence = int(stock['confidence'] * 100)
                msg += f"{i}. {stock['name']} ({confidence}%)\n"
                msg += f"   └ {stock['reason']}\n"
                msg += f"   └ 예상: {stock['expected_impact']}\n"
            msg += "\n"
        else:
            msg += "📊 특별한 이벤트 없음\n\n"
        
        if report['risks']:
            msg += "⚠️ 리스크\n"
            for risk in report['risks']:
                msg += f"• {risk}\n"
        else:
            msg += "✅ 시장 안정\n"
        
        return msg
    
    async def news_monitor(self):
        """뉴스 모니터 (30초)"""
        logger.info("📰 뉴스 모니터 시작")
        
        while True:
            try:
                news_list = await self.news_engine.scan_all_sources()
                
                for news in news_list:
                    alert = await self.news_engine.process_news(news)
                    
                    if alert:
                        message = self._format_news_alert(alert)
                        await self.send_message(message)
                        
                        logger.info(f"🔔 뉴스 알림: {news['title'][:50]}")
                
                self.news_engine.cleanup_old_news()
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"뉴스 모니터 오류: {e}")
                await asyncio.sleep(30)
    
    def _format_news_alert(self, alert):
        """
        🆕 뉴스 알림 포맷 (v3.0)
        - AI 모델명 표시
        - SEC 공시 구분
        """
        news = alert['news']
        analysis = alert['analysis']
        verification = alert['verification_details']
        model_used = alert.get('model_used', 'unknown')
        is_filing = alert.get('is_filing', False)
        
        score = analysis['score']
        
        # SEC 공시 vs 일반 뉴스 구분
        if is_filing:
            msg = f"📋 [SEC 공시] {score}/10 🔥\n\n"
        else:
            msg = f"⚡ [긴급] {score}/10 🔥\n\n"
        
        msg += f"📰 {news['title']}\n"
        msg += f"출처: {news['source']}\n"
        
        # 발간 시간 (KST)
        if news.get('published_time_kst'):
            msg += f"발간: {news['published_time_kst']}\n"
        
        msg += "\n"
        
        # 🆕 AI 모델명 표시
        msg += f"🤖 AI 분석 (모델: {model_used})\n"
        msg += f"{analysis['summary']}\n\n"
        
        checks = ' '.join(['✅' for _ in verification['checks_passed']])
        msg += f"검증: {checks} ({verification['total_score']}점)\n"
        for check in verification['checks_passed']:
            msg += f"• {check}\n"
        msg += "\n"
        
        if analysis.get('recommendations'):
            msg += "💎 수혜주 TOP 3\n"
            for i, rec in enumerate(analysis['recommendations'][:3], 1):
                confidence = int(rec.get('confidence', 0.7) * 100)
                msg += f"{i}. {rec['name']} ({rec['ticker']})\n"
                msg += f"   └ {rec['reason']}\n"
                msg += f"   └ 신뢰도 {confidence}%\n"
                
                # 예상 수익률
                if rec.get('expected_return_30min'):
                    msg += f"   └ 30분: +{rec['expected_return_30min']}%"
                if rec.get('expected_return_1day'):
                    msg += f" / 1일: +{rec['expected_return_1day']}%\n"
        
        if news.get('url'):
            msg += f"\n원문: {news['url']}\n"
        
        msg += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        
        return msg
    
    async def momentum_monitor(self):
        """모멘텀 모니터 (5분)"""
        logger.info("📊 모멘텀 모니터 시작")
        
        while True:
            try:
                kr_signals = await self.momentum.scan_momentum('KR')
                for signal in kr_signals:
                    message = self._format_momentum_alert(signal)
                    await self.send_message(message)
                
                us_signals = await self.momentum.scan_momentum('US')
                for signal in us_signals:
                    message = self._format_momentum_alert(signal)
                    await self.send_message(message)
                
                self.momentum.cleanup_alerts()
                
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"모멘텀 모니터 오류: {e}")
                await asyncio.sleep(300)
    
    def _format_momentum_alert(self, signal):
        """모멘텀 알림 포맷"""
        market_emoji = '🇰🇷' if signal['market'] == 'KR' else '🇺🇸'
        
        if signal.get('signal_type') == 'program_buy':
            msg = f"💻 [프로그램 매수] {market_emoji}\n\n"
            msg += f"{signal['name']} ({signal['ticker']})\n"
            msg += f"{signal['reason']}\n"
        
        elif signal.get('signal_type') == 'theme_surge':
            msg = f"🎨 [테마 급등] {market_emoji}\n\n"
            msg += f"{signal['theme_name']}\n\n"
            msg += f"{signal['reason']}\n"
        
        else:
            msg = f"📊 [급등 감지] {market_emoji}\n\n"
            msg += f"{signal['name']} ({signal['ticker']})\n"
            msg += f"현재: {signal['price']:,.0f} (+{signal['change_percent']:.1f}%)\n"
            msg += f"거래량: 평균 대비 {signal['volume_ratio']:.1f}배\n\n"
            
            msg += "신호\n"
            for s in signal['signals']:
                msg += f"• {s}\n"
            msg += "\n"
            
            msg += f"원인: {signal['reason']}\n"
        
        msg += f"\n⏰ {signal['timestamp'].strftime('%H:%M:%S')}"
        
        return msg
    
    async def filing_monitor_kr(self):
        """🆕 한국 공시 실시간 모니터 (5분)"""
        logger.info("📋 한국 공시 실시간 모니터 시작")
        
        while True:
            try:
                # DART 공시 스캔 (최근 1일)
                signals = await self.predictor.scan_dart_filings(days=1)
                
                for signal in signals:
                    # 중복 체크
                    filing_id = signal.get('filing_id', '')
                    signal_id = f"KR_{signal.get('ticker', 'UNKNOWN')}_{filing_id}"
                    
                    if signal_id in self.seen_filings:
                        continue
                    
                    self.seen_filings.add(signal_id)
                    
                    # 즉시 알림!
                    message = self._format_filing_alert(signal)
                    await self.send_message(message)
                    
                    logger.info(f"🔔 한국 공시 알림: {signal.get('name')}")
                
                # 메모리 정리
                if len(self.seen_filings) > 1000:
                    self.seen_filings = set(list(self.seen_filings)[-500:])
                
                await asyncio.sleep(300)  # 5분
                
            except Exception as e:
                logger.error(f"한국 공시 모니터 오류: {e}")
                await asyncio.sleep(300)
    
    async def filing_monitor_us(self):
        """🆕 미국 공시 실시간 모니터 (10분)"""
        logger.info("📋 미국 공시 실시간 모니터 시작")
        
        while True:
            try:
                # Form 4 (내부자)
                form4_signals = await self.predictor.scan_sec_form4(hours=2)
                for signal in form4_signals:
                    filing_id = signal.get('filing_id', '')
                    signal_id = f"US_F4_{signal.get('ticker')}_{filing_id}"
                    
                    if signal_id not in self.seen_filings:
                        self.seen_filings.add(signal_id)
                        message = self._format_filing_alert(signal)
                        await self.send_message(message)
                        logger.info(f"🔔 Form 4 알림: {signal.get('name')}")
                
                # 13D/13G (고래)
                whale_signals = await self.predictor.scan_sec_13d(hours=2)
                for signal in whale_signals:
                    filing_id = signal.get('filing_id', '')
                    signal_id = f"US_13D_{signal.get('ticker')}_{filing_id}"
                    
                    if signal_id not in self.seen_filings:
                        self.seen_filings.add(signal_id)
                        message = self._format_filing_alert(signal)
                        await self.send_message(message)
                        logger.info(f"🔔 13D/13G 알림: {signal.get('name')}")
                
                # 메모리 정리
                if len(self.seen_filings) > 1000:
                    self.seen_filings = set(list(self.seen_filings)[-500:])
                
                await asyncio.sleep(600)  # 10분
                
            except Exception as e:
                logger.error(f"미국 공시 모니터 오류: {e}")
                await asyncio.sleep(600)
    
    def _format_filing_alert(self, signal):
        """🆕 공시 알림 포맷"""
        market = '🇰🇷' if signal.get('market') == 'KR' else '🇺🇸'
        
        # 시그널 타입별 이모지
        type_emoji = {
            'insider_buy': '👔',
            'ownership_increase': '🐋',
            'whale_alert': '🐳',
            'contract': '📝',
            '3rd_party_allocation': '🚀',
            'ownership_change': '👑',
            'tender_offer': '💰'
        }.get(signal.get('signal_type'), '📊')
        
        confidence = int(signal.get('confidence', 0.5) * 100)
        
        msg = f"{type_emoji} [실시간 공시] {market}\n\n"
        msg += f"{signal.get('name')} ({signal.get('ticker')})\n"
        msg += f"신호: {signal.get('reason')}\n"
        msg += f"신뢰도: {confidence}%\n"
        msg += f"예상: {signal.get('expected_impact')}\n"
        
        # 공시 링크
        filing_url = signal.get('details', {}).get('filing_url')
        if filing_url:
            msg += f"\n원문: {filing_url}\n"
        
        msg += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        
        return msg
    
    async def send_message(self, text):
        """메시지 전송"""
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=text
                # parse_mode 제거 - 안전하게!
            )
        except Exception as e:
            logger.error(f"메시지 전송 실패: {e}")
    
    async def run_forever(self):
        """실행"""
        try:
            await self.start()
            
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("봇 종료 중...")
            await self.app.stop()
            await self.app.shutdown()