import asyncio
import sys
import os

# Добавляем корень проекта в пути поиска модулей
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.config import Config, logger
from src.bot.bot import setup_bot

async def main():
    """ Основная точка входа в приложение. """
    logger.info("🚀 Starting BT6 Parser Bot system...")

    # Инициализируем Aiogram бота
    # Миграции теперь запустятся сами при первом импорте базы данных
    bot, dp = await setup_bot()
    
    tasks = [
        dp.start_polling(bot, skip_updates=True)
    ]

    logger.info("📡 All components are ready. Starting main loop...")
    
    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.critical(f"💥 Critical error in main loop: {e}", exc_info=True)
    finally:
        logger.info("🛑 Shutting down services...")
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 System stopped by user.")
    except Exception as e:
        logger.critical(f"💀 Unhandled exception: {e}")
        sys.exit(1)
