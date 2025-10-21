import logging
from typing import Dict, List, Optional
from aiogram import Bot
from aiogram.types import Message
import asyncio

logger = logging.getLogger(__name__)


class OnboardingService:
    """
    УНИВЕРСАЛЬНЫЙ СЕРВИС ПРОМЕЖУТОЧНЫХ ШАГОВ
    Выполняет последовательность шагов перед основным действием
    """

    def __init__(self, bot: Bot = None):
        self.bot = bot
        self.steps = []  # Конфигурируемая последовательность шагов

    def configure_steps(self, steps_config: List[Dict]):
        """
        НАСТРОЙКА ПОСЛЕДОВАТЕЛЬНОСТИ ШАГОВ

        Args:
            steps_config: [
                {
                    "type": "channel_subscription",
                    "channel": "@my_channel",
                    "message": "Подпишитесь на канал",
                    "skip_if_subscribed": True
                },
                {
                    "type": "ad_view",
                    "ad_text": "Реклама партнера...",
                    "duration": 5,
                    "image_url": "https://example.com/ad.jpg"  # опционально
                },
                {
                    "type": "data_collection",
                    "fields": ["phone", "email"],
                    "message": "Заполните данные"
                }
            ]
        """
        self.steps = steps_config
        logger.info(f"✅ Onboarding сконфигурирован: {len(steps_config)} шагов")

    async def execute_steps(self, user_id: int, message: Message = None) -> Dict:
        """
        ВЫПОЛНЕНИЕ ВСЕХ ШАГОВ ONBOARDING

        Returns:
            {
                "completed": bool,
                "next_action": str,  # "create_vpn", "show_menu", etc.
                "message": str,
                "failed_step": str   # если completed=False
            }
        """
        if not self.steps:
            logger.info("⚠️ Onboarding шаги не настроены, пропускаем")
            return {"completed": True, "next_action": "create_vpn"}

        logger.info(f"🔍 Запуск onboarding для пользователя {user_id}")

        for step in self.steps:
            step_result = await self._execute_single_step(step, user_id, message)

            if not step_result["completed"]:
                logger.info(f"⏸️ Onboarding остановлен на шаге: {step['type']}")
                return {
                    "completed": False,
                    "next_action": "wait_onboarding",
                    "message": step_result["message"],
                    "failed_step": step["type"]
                }

        logger.info(f"✅ Onboarding завершен для пользователя {user_id}")
        return {"completed": True, "next_action": "create_vpn"}

    async def _execute_single_step(self, step: Dict, user_id: int, message: Message) -> Dict:
        """ВЫПОЛНЕНИЕ ОДНОГО ШАГА"""
        step_type = step["type"]

        try:
            if step_type == "channel_subscription":
                return await self._check_channel_subscription(step, user_id)

            elif step_type == "ad_view":
                return await self._show_advertisement(step, user_id, message)

            elif step_type == "data_collection":
                return await self._collect_additional_data(step, user_id, message)

            else:
                logger.error(f"❌ Неизвестный тип шага: {step_type}")
                return {"completed": True, "message": "Unknown step"}  # Пропускаем неизвестные шаги

        except Exception as e:
            logger.error(f"❌ Ошибка в шаге {step_type}: {e}")
            return {"completed": False, "message": f"Ошибка шага: {e}"}

    # 🎪 ШАБЛОН 1: ПРОВЕРКА ПОДПИСКИ НА КАНАЛ
    async def _check_channel_subscription(self, step: Dict, user_id: int) -> Dict:
        """ШАГ 1: Проверка подписки на Telegram канал"""
        channel = step["channel"]
        message_text = step.get("message", f"Подпишитесь на канал {channel}")
        skip_if_subscribed = step.get("skip_if_subscribed", True)

        try:
            # Проверяем подписку пользователя
            if await self._is_user_subscribed(user_id, channel):
                if skip_if_subscribed:
                    logger.info(f"✅ Пользователь {user_id} уже подписан на {channel}")
                    return {"completed": True, "message": "Уже подписан"}
                else:
                    # Все равно показываем сообщение
                    return {
                        "completed": False,
                        "message": f"{message_text}\n\n✅ Вы уже подписаны! Нажмите продолжить."
                    }

            # Пользователь не подписан
            return {
                "completed": False,
                "message": f"{message_text}\n\n🔗 Ссылка: https://t.me/{channel.lstrip('@')}\n\nПосле подписки нажмите 'Проверить подписку'"
            }

        except Exception as e:
            logger.error(f"❌ Ошибка проверки подписки: {e}")
            return {"completed": True, "message": "Ошибка проверки подписки"}  # Пропускаем шаг при ошибке

    async def _is_user_subscribed(self, user_id: int, channel: str) -> bool:
        """Проверка подписки пользователя на канал"""
        if not self.bot:
            logger.warning("⚠️ Bot не установлен, пропускаем проверку подписки")
            return True  # В тестовом режиме пропускаем проверку

        try:
            member = await self.bot.get_chat_member(chat_id=channel, user_id=user_id)
            return member.status in ["member", "administrator", "creator"]
        except Exception as e:
            logger.error(f"❌ Ошибка проверки подписки на {channel}: {e}")
            return False

    # 📺 ШАБЛОН 2: ПОКАЗ РЕКЛАМЫ
    async def _show_advertisement(self, step: Dict, user_id: int, message: Message) -> Dict:
        """ШАГ 2: Показ рекламного сообщения с задержкой"""
        ad_text = step["ad_text"]
        duration = step.get("duration", 5)  # секунд
        image_url = step.get("image_url")

        try:
            # Отправляем рекламное сообщение
            if image_url:
                # TODO: реализовать отправку фото с текстом
                await message.answer(
                    f"📺 {ad_text}\n\n⏳ Пожалуйста, подождите {duration} секунд...",
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    f"📺 {ad_text}\n\n⏳ Пожалуйста, подождите {duration} секунд...",
                    parse_mode="HTML"
                )

            # Ждем указанное время
            await asyncio.sleep(duration)

            logger.info(f"✅ Реклама показана пользователю {user_id} ({duration}сек)")
            return {"completed": True, "message": "Реклама просмотрена"}

        except Exception as e:
            logger.error(f"❌ Ошибка показа рекламы: {e}")
            return {"completed": True, "message": "Ошибка показа рекламы"}

    # 📝 ШАБЛОН 3: СБОР ДОПОЛНИТЕЛЬНЫХ ДАННЫХ
    async def _collect_additional_data(self, step: Dict, user_id: int, message: Message) -> Dict:
        """ШАГ 3: Запрос дополнительных данных у пользователя"""
        fields = step.get("fields", [])
        message_text = step.get("message", "Пожалуйста, заполните дополнительные данные")

        try:
            # Проверяем, какие данные уже есть
            from services.database import get_user
            user = await get_user(user_id)

            missing_fields = []
            for field in fields:
                if field == "email" and (not user or not user.get('email')):
                    missing_fields.append("email")
                elif field == "phone" and (not user or not user.get('phone_number')):
                    missing_fields.append("телефон")
                elif field == "name" and (not user or not user.get('first_name')):
                    missing_fields.append("имя")

            if not missing_fields:
                logger.info(f"✅ Все данные уже собраны для пользователя {user_id}")
                return {"completed": True, "message": "Данные уже собраны"}

            # Формируем сообщение с недостающими полями
            fields_text = ", ".join(missing_fields)
            return {
                "completed": False,
                "message": f"{message_text}\n\n📋 Необходимо заполнить: {fields_text}\n\nИспользуйте команду /profile для заполнения"
            }

        except Exception as e:
            logger.error(f"❌ Ошибка сбора данных: {e}")
            return {"completed": True, "message": "Ошибка сбора данных"}


# Глобальный экземпляр для использования
onboarding_service = OnboardingService()
