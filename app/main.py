import asyncio
import logging
from aiogram import Bot, Dispatcher
from handlers.handlers import router  # ⚠️ ИСПРАВЛЕНО
from config import BOT_TOKEN
from services.database import init_database
from handlers.keyboards import setup_menu_button

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    try:
        logger.info("🚀 Запуск бота...")

        # 1. Инициализация базы данных
        logger.info("🔍 Инициализация базы данных...")
        db_success = await init_database()
        if not db_success:
            logger.error("❌ Не удалось инициализировать базу данных")
            return

        # 2. Создаем бота и диспетчер
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher()

        # 3. Настраиваем Menu Button
        logger.info("📋 Настройка меню...")
        await setup_menu_button(bot)

        # 4. Подключаем роутер
        dp.include_router(router)

        # 5. Запускаем бота
        logger.info("✅ Бот запущен и готов к работе!")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске: {e}")
    finally:
        logger.info("🛑 Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())