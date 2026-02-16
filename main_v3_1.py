# -*- coding: utf-8 -*-
"""
Main v3.1 - 조기경보 시스템 완전체 (제미나이 검증 반영)
"""

import asyncio
import logging
from telegram_bot_v3_1 import TelegramBotV3_1

# 로깅
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_v3_1.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """메인"""
    logger.info("=" * 60)
    logger.info("🐺 조기경보 시스템 v3.1 완전체 시작")
    logger.info("=" * 60)
    logger.info("AI Brain v3.0: ✅ (공격적 스캘퍼)")
    logger.info("News Engine v3.0: ✅ (미국 5대장 + 한국 4대장 + SEC)")
    logger.info("Momentum Tracker v3.1: ✅ (Finviz + 이중 스캔)")
    logger.info("Predictor Engine v3.0: ✅ (SEC Only)")
    logger.info("=" * 60)
    logger.info("🔥 v3.1 완전체 특징:")
    logger.info("  • Finviz 급등주 스캔 (Yahoo 대신)")
    logger.info("  • 뉴스 종목 1분 주기 감시")
    logger.info("  • 시장 전체 10분 주기 스캔")
    logger.info("  • 랜덤 User-Agent (차단 방지)")
    logger.info("  • 랜덤 지연 (Anti-Ban)")
    logger.info("=" * 60)
    
    try:
        bot = TelegramBotV3_1()
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
