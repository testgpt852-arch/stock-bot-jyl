# -*- coding: utf-8 -*-
"""
Main (Production) - 조기경보 시스템 진입점
"""

import asyncio
import logging

from telegram_bot import TelegramBot

# ── 로깅 설정 ──
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stockbot.log'),
        logging.StreamHandler(),
    ],
)

# 🔧 google-genai SDK의 AFC(Automatic Function Calling) 내부 로그 억제
# "AFC is enabled with max remote calls: 10" 반복 출력 방지
logging.getLogger('google').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def main():
    logger.info("=" * 60)
    logger.info("🚀 조기경보 시스템 Production 시작")
    logger.info("=" * 60)
    logger.info("AI Brain:           ✅ (대장주 top_ticker 지목)")
    logger.info("News Engine:        ✅ (미국 5대장 + 한국 3대장 + SEC)")
    logger.info("Momentum Tracker:   ✅ (Finviz curl_cffi + prepost=True)")
    logger.info("Predictor Engine:   ✅ (SEC Form4 + 13D/G)")
    logger.info("=" * 60)
    logger.info("⚡ 핵심 연동:")
    logger.info("  뉴스 → AI top_ticker 지목 → 1분 집중 감시 등록")
    logger.info("  Finviz 크롤링: curl_cffi (TLS 지문 위장)")
    logger.info("  yfinance: prepost=True (장전/장후 포함)")
    logger.info("=" * 60)

    try:
        bot = TelegramBot()
        await bot.run_forever()

    except KeyboardInterrupt:
        logger.info("\n👋 사용자 종료")

    except Exception as e:
        logger.error(f"💥 치명적 오류: {e}", exc_info=True)

    finally:
        logger.info("🛑 시스템 종료")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
