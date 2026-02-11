# -*- coding: utf-8 -*-
"""
Main v2.2 - 조기경보 시스템 완전체
"""

import asyncio
import logging
from telegram_bot_v2_2 import TelegramBotV2_2

# 로깅
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_v2_2.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """메인"""
    logger.info("=" * 60)
    logger.info("🚀 조기경보 시스템 v2.2 시작")
    logger.info("=" * 60)
    logger.info("AI Brain v2.2: ✅")
    logger.info("News Engine v2.2 (6개 소스): ✅")
    logger.info("Momentum Tracker v2.2: ✅")
    logger.info("Predictor Engine v2.2 (고래 추적): ✅")
    logger.info("=" * 60)
    
    try:
        bot = TelegramBotV2_2()
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
