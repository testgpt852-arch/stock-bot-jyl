# -*- coding: utf-8 -*-
"""
Main - Production v3.6 (TradingView 시간대별 분기)
조기경보 시스템 최종 배포 버전
"""

import asyncio
import logging
from telegram_bot import TelegramBot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


async def main():
    logger.info("=" * 60)
    logger.info("🐺 조기경보 시스템 v3.6 (TradingView 시간대별 분기) 시작")
    logger.info("=" * 60)
    logger.info("✅ AI Brain          : 공격적 스캘퍼 (top_ticker 대장주 지목)")
    logger.info("✅ News Engine       : 미국 5대장 + 한국 3대장 + SEC 8-K")
    logger.info("✅ Momentum Tracker v3.6 : TradingView 시간대별 분기 (KST)")
    logger.info("✅ Predictor Engine  : SEC Only")
    logger.info("=" * 60)
    logger.info("🔥 핵심 개선사항:")
    logger.info("  • Finviz: curl_cffi Chrome TLS 위장 (Cloudflare 차단 방지)")
    logger.info("  • 컬럼 매핑: 헤더 텍스트 동적 탐지 (고정 인덱스 제거)")
    logger.info("  • yfinance: prepost=True (장전/장후 급등 감지)")
    logger.info("  • AI 대장주 → 즉시 1분 집중 감시 연동")
    logger.info("=" * 60)
    logger.info("🚀 v3.6 신규 기능 (TradingView 연동):")
    logger.info("  • 프리마켓 (18:00~23:30 KST): TradingView 단독")
    logger.info("  • 정규장 (23:30~06:00 KST): Finviz → TradingView 백업")
    logger.info("  • 애프터마켓 (06:00~18:00 KST): TradingView 단독")
    logger.info("  • KST 기준 시간대별 자동 분기")
    logger.info("  • Gemini 검증: 티커 추출 로직 적용")
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
