# -*- coding: utf-8 -*-
"""
Telegram Bot v2.2 - 완전체
- 4개 엔진 통합 (AI, News, Momentum, Predictor)
- 충돌 방지
- 에러 핸들링 완벽
"""

import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import Config

# v2.2 엔진
from ai_brain_v2_2 import AIBrainV2_2
from news_engine_v2_2 import NewsEngineV2_2
from momentum_tracker_v2_2 import MomentumTrackerV2_2
from predictor_engine_v2_2 import PredictorEngineV2_2

logger = logging.getLogger(__name__)

class TelegramBotV2_2:
    def __init__(self):
        self.app = None
        self.chat_id = Config.TELEGRAM_CHAT_ID
        
        # 엔진 초기화 (충돌 방지)
        try:
            self.ai = AIBrainV2_2()
            self.news_engine = NewsEngineV2_2(self.ai)
            self.momentum = MomentumTrackerV2_2()
            self.predictor = PredictorEngineV2_2()
            
            logger.info("✅ 모든 엔진 초기화 성공")
            
        except Exception as e:
            logger.error(f"❌ 엔진 초기화 실패: {e}")
            raise
        
        logger.info("🤖 Telegram Bot v2.2 초기화")
    
    async def start(self):
        """봇 시작"""
        try:
            self.app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
            
            # 명령어
            self.app.add_handler(CommandHandler("start", self.cmd_start))
            self.app.add_handler(CommandHandler("analyze", self.cmd_analyze))
            self.app.add_handler(CommandHandler("report", self.cmd_report))
            self.app.add_handler(CommandHandler("help", self.cmd_help))
            
            await self.app.initialize()
            await self.app.start()
            
            # 백그라운드 작업
            asyncio.create_task(self.schedule_reports())
            asyncio.create_task(self.news_monitor())
            asyncio.create_task(self.momentum_monitor())
            
            logger.info("✅ 봇 시작")
            
            await self.send_message(
                "🚀 조기경보 시스템 v2.2 시작!\n\n"
                "✅ AI Brain v2.2 (3개 모델)\n"
                "✅ News Engine v2.2 (6개 소스)\n"
                "✅ Momentum Tracker v2.2\n"
                "✅ Predictor Engine v2.2 (고래 추적)\n\n"
                "승률 80% 목표!"
            )
            
        except Exception as e:
            logger.error(f"봇 시작 실패: {e}")
            raise
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시작"""
        await update.message.reply_text(
            "🤖 조기경보 시스템 v2.2\n\n"
            "**기능:**\n"
            "📰 실시간 뉴스 (6개 소스, 30초)\n"
            "📊 급등주 감지 (5분)\n"
            "💻 프로그램 매매 추적\n"
            "🎨 테마주 연쇄 상승\n"
            "🐋 고래 지분 공시\n"
            "🔮 아침/저녁 리포트\n\n"
            "**명령어:**\n"
            "/analyze 삼성전자 - 즉시 분석\n"
            "/report - 즉시 리포트\n"
            "/help - 도움말"
        )
    
    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """종목 분석"""
        if not context.args:
            await update.message.reply_text("사용법: /analyze 삼성전자")
            return
        
        ticker = ' '.join(context.args)
        await update.message.reply_text(f"🔍 {ticker} 분석 중...")
        
        # stock_analyzer_v2_2 사용 (간소화)
        await update.message.reply_text(
            f"📊 {ticker}\n"
            f"분석 기능 구현 예정"
        )
    
    async def cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """즉시 리포트"""
        await update.message.reply_text("📊 리포트 생성 중...")
        
        try:
            # 한국
            kr_report = await self.predictor.generate_daily_report('KR')
            kr_msg = self._format_daily_report(kr_report, '🇰🇷 한국')
            await update.message.reply_text(kr_msg)
            
            # 미국
            us_report = await self.predictor.generate_daily_report('US')
            us_msg = self._format_daily_report(us_report, '🇺🇸 미국')
            await update.message.reply_text(us_msg)
            
        except Exception as e:
            logger.error(f"리포트 생성 오류: {e}")
            await update.message.reply_text(f"⚠️ 리포트 생성 실패: {str(e)}")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """도움말"""
        await update.message.reply_text(
            "📚 조기경보 시스템 v2.2\n\n"
            "**자동 알림:**\n"
            "07:30 - 한국장 오전 브리핑\n"
            "23:00 - 미국장 저녁 브리핑\n"
            "장중 - 실시간 뉴스 (30초)\n"
            "장중 - 급등 감지 (5분)\n\n"
            "**데이터 소스:**\n"
            "뉴스: Yahoo, Globe, PR, Business Wire...\n"
            "공시: DART, SEC Form 4, SEC 13D/13G\n"
            "모멘텀: 프로그램 매매, 테마주\n\n"
            "**AI 모델:**\n"
            "Gemma 3-27B (무제한 쿼터)\n"
            "Gemini 3 Flash (고성능)\n"
            "3단계 fallback\n\n"
            "🎯 승률 80% 목표"
        )
    
    async def schedule_reports(self):
        """스케줄러"""
        logger.info("📅 스케줄러 시작")
        
        while True:
            try:
                now = datetime.now()
                
                # 07:30
                if now.hour == 7 and now.minute == 30:
                    await self.send_morning_report_kr()
                    await asyncio.sleep(60)
                
                # 23:00
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
        msg = f"**{title}**\n"
        msg += f"📅 {report['date'].strftime('%Y-%m-%d')}\n\n"
        
        if report['events_today']:
            msg += "**📰 오늘의 이벤트**\n"
            for event in report['events_today']:
                msg += f"• {event}\n"
            msg += "\n"
        
        if report['hot_stocks']:
            msg += "**🎯 주목 종목 TOP 5**\n"
            for i, stock in enumerate(report['hot_stocks'][:5], 1):
                confidence = int(stock['confidence'] * 100)
                msg += f"{i}. **{stock['name']}** ({confidence}%)\n"
                msg += f"   └ {stock['reason']}\n"
                msg += f"   └ 예상: {stock['expected_impact']}\n"
            msg += "\n"
        else:
            msg += "📊 특별한 이벤트 없음\n\n"
        
        if report['risks']:
            msg += "**⚠️ 리스크**\n"
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
        """뉴스 알림 포맷"""
        news = alert['news']
        analysis = alert['analysis']
        verification = alert['verification_details']
        
        score = analysis['score']
        msg = f"⚡ **[긴급] {score}/10** 🔥\n\n"
        
        msg += f"**📰 {news['title']}**\n"
        msg += f"출처: {news['source']}\n\n"
        
        msg += f"**🤖 AI 분석**\n"
        msg += f"{analysis['summary']}\n\n"
        
        checks = ' '.join(['✅' for _ in verification['checks_passed']])
        msg += f"**검증**: {checks} ({verification['total_score']}점)\n"
        for check in verification['checks_passed']:
            msg += f"• {check}\n"
        msg += "\n"
        
        if analysis.get('recommendations'):
            msg += "**💎 수혜주 TOP 3**\n"
            for i, rec in enumerate(analysis['recommendations'][:3], 1):
                confidence = int(rec.get('confidence', 0.7) * 100)
                msg += f"{i}. **{rec['name']}** ({rec['ticker']})\n"
                msg += f"   └ {rec['reason']}\n"
                msg += f"   └ 신뢰도 {confidence}%\n"
        
        if news.get('url'):
            msg += f"\n[원문]({news['url']})\n"
        
        msg += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        
        return msg
    
    async def momentum_monitor(self):
        """모멘텀 모니터 (5분)"""
        logger.info("📊 모멘텀 모니터 시작")
        
        while True:
            try:
                # 한국
                kr_signals = await self.momentum.scan_momentum('KR')
                for signal in kr_signals:
                    message = self._format_momentum_alert(signal)
                    await self.send_message(message)
                
                # 미국
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
            # 프로그램 매매
            msg = f"💻 **[프로그램 매수]** {market_emoji}\n\n"
            msg += f"**{signal['name']}** ({signal['ticker']})\n"
            msg += f"{signal['reason']}\n"
        
        elif signal.get('signal_type') == 'theme_surge':
            # 테마주
            msg = f"🎨 **[테마 급등]** {market_emoji}\n\n"
            msg += f"**{signal['theme_name']}**\n\n"
            msg += f"{signal['reason']}\n"
        
        else:
            # 급등주
            msg = f"📊 **[급등 감지]** {market_emoji}\n\n"
            msg += f"**{signal['name']}** ({signal['ticker']})\n"
            msg += f"현재: {signal['price']:,.0f} (+{signal['change_percent']:.1f}%)\n"
            msg += f"거래량: 평균 대비 {signal['volume_ratio']:.1f}배\n\n"
            
            msg += "**신호**\n"
            for s in signal['signals']:
                msg += f"• {s}\n"
            msg += "\n"
            
            msg += f"**원인**: {signal['reason']}\n"
        
        msg += f"\n⏰ {signal['timestamp'].strftime('%H:%M:%S')}"
        
        return msg
    
    async def send_message(self, text):
        """메시지 전송"""
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode='Markdown'
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
