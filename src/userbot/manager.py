from telethon import TelegramClient
from src.config import Config, logger
from src.userbot.handlers import register_userbot_handlers

class UserbotManager:
    def __init__(self):
        self.client = TelegramClient(
            Config.TELEGRAM_SESSION_NAME,
            Config.TELEGRAM_API_ID,
            Config.TELEGRAM_API_HASH
        )

    async def start(self):
        logger.info("🔑 Starting Userbot (Telethon)...")
        # При первом запуске попросит код в терминале
        await self.client.start()
        
        # Получаем данные о себе для проверки
        me = await self.client.get_me()
        logger.info(f"✅ Userbot started as: {me.first_name} (@{me.username})")

        # Регистрируем обработчики событий (парсинг сообщений)
        register_userbot_handlers(self.client)

    async def run_until_disconnected(self):
        await self.client.run_until_disconnected()

    async def stop(self):
        await self.client.disconnect()