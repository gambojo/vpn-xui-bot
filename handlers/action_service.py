import logging
from typing import Dict

from services.database import save_user, get_user, update_user_balance, \
    get_trial_status, mark_trial_used, get_connection_string
from services.vpn_service import create_vpn_account, get_vpn_status, renew_vpn_account
from services.payment import create_payment, check_payment, is_payment_enabled, get_available_providers, \
    create_payment_config, \
    create_payment_item
from services.onboarding import onboarding_service
from config import PAYMENT_AMOUNT, EXPIRY_TIME, TRIAL_ENABLED, TRIAL_DAYS

logger = logging.getLogger(__name__)


class ActionService:
    """
    🎯 ЦЕНТРАЛЬНЫЙ СЕРВИС БИЗНЕС-ЛОГИКИ
    Содержит ВСЮ логику обработки данных и работы с API
    ВЫЗЫВАЕТСЯ ИЗ: handlers.handlers
    """

    def __init__(self):
        # ⚠️ ИНИЦИАЛИЗАЦИЯ ЭКЗЕМПЛЯРА
        pass

    async def handle_get_vpn(self, telegram_id: int, username: str = None) -> Dict:
        """
        📍 ТОЧКА ВХОДА: Получение VPN услуги - С ПОДТВЕРЖДЕНИЕМ ПЕРЕЗАПИСИ
        """
        try:
            # Сохраняем пользователя если нужно
            if username:
                await save_user(telegram_id, username)

            # 🔄 ЗАПУСК ONBOARDING ПЕРЕД СОЗДАНИЕМ VPN
            onboarding_result = await onboarding_service.execute_steps(telegram_id)
            if not onboarding_result["completed"]:
                return {
                    "type": "onboarding_required",
                    "message": onboarding_result["message"],
                    "next_action": onboarding_result["next_action"]
                }

            # 🔴 ДОБАВЛЯЕМ: Проверка существующей подписки
            existing_vpn = await get_vpn_status(telegram_id)
            if existing_vpn and existing_vpn.get("success") and existing_vpn.get("lease_is_active"):
                return {
                    "type": "confirmation_required",
                    "message": (
                        "⚠️ <b>У вас уже есть активная подписка!</b>\n\n"
                        f"• Текущий статус: ✅ Активна\n"
                        f"• Осталось дней: {existing_vpn['expiry_days']}\n\n"
                        "Создание новой подписки <b>перезапишет</b> текущую.\n"
                        "Продолжить?"
                    ),
                    "existing_days": existing_vpn['expiry_days']
                }

            # Если оплата включена - возвращаем информацию для оплаты
            if is_payment_enabled():
                return {
                    "type": "payment_required",
                    "message": "💳 Выберите способ оплаты для активации VPN",
                    "providers": get_available_providers()
                }

            # Если оплата отключена - сразу создаем VPN
            result = await create_vpn_account(telegram_id)
            if result and result.get("success"):
                # Начисляем баллы за активацию
                await update_user_balance(telegram_id, 5)

                return {
                    "type": "success",
                    "message": (
                        f"✅ <b>VPN активирован!</b>\n"
                        f"• Срок: {result['expiry_days']} дней\n"
                        f"• ID: {telegram_id}\n"
                        f"• Подключение: <code>{result['connection_string']}</code>"
                    ),
                    "qrcode_buffer": result.get('qrcode_buffer')
                }
            else:
                return {
                    "type": "error",
                    "message": "❌ Не удалось создать VPN. Попробуйте позже."
                }

        except Exception as e:
            logger.error(f"❌ Ошибка создания VPN: {e}")
            return {
                "type": "error",
                "message": "❌ Ошибка при создании VPN сервиса"
            }

    async def handle_renew_vpn(self, telegram_id: int) -> Dict:
        """
        📍 ТОЧКА ВХОДА: Продление VPN услуги - ДОБАВЛЕННЫЙ МЕТОД
        """
        try:
            # Если оплата включена - возвращаем информацию для оплаты
            if is_payment_enabled():
                return {
                    "type": "payment_required",
                    "message": "💳 Выберите способ оплаты для продления VPN",
                    "providers": get_available_providers()
                }

            # Если оплата отключена - сразу продлеваем VPN
            result = await renew_vpn_account(telegram_id)
            if result and result.get("success"):
                # Начисляем баллы за продление
                await update_user_balance(telegram_id, 3)

                return {
                    "type": "success",
                    "message": (
                        f"✅ <b>VPN продлен!</b>\n"
                        f"• Новый срок: {EXPIRY_TIME} дней\n"
                        f"• ID: {telegram_id}\n"
                        f"• Подключение: <code>{result['connection_string']}</code>"
                    ),
                    "qrcode_buffer": result.get('qrcode_buffer')
                }
            else:
                return {
                    "type": "error",
                    "message": (
                        "❌ Не удалось продлить VPN.\n"
                        "Сначала активируйте услугу через «Приобрести подписку»"
                    )
                }

        except Exception as e:
            logger.error(f"❌ Ошибка продления VPN: {e}")
            return {
                "type": "error",
                "message": "❌ Ошибка при продлении VPN"
            }

    async def handle_free_trial(self, telegram_id: int, username: str = None) -> Dict:
        """
        📍 ТОЧКА ВХОДА: Бесплатный trial период - УЛУЧШЕННАЯ ВЕРСИЯ
        """
        try:
            # Проверяем включен ли trial
            if not TRIAL_ENABLED:
                return {
                    "type": "error",
                    "message": "❌ Бесплатный период временно недоступен"
                }

            # Проверяем использовал ли уже trial
            trial_used = await get_trial_status(telegram_id)
            if trial_used:
                return {
                    "type": "error",
                    "message": (
                        "❌ Вы уже использовали бесплатный период\n"
                        "💳 Для продолжения использования приобретите подписку"
                    )
                }

            # Сохраняем пользователя если нужно
            if username:
                await save_user(telegram_id, username)

            # 🔄 ЗАПУСК ONBOARDING ПЕРЕД СОЗДАНИЕМ VPN
            onboarding_result = await onboarding_service.execute_steps(telegram_id)
            if not onboarding_result["completed"]:
                return {
                    "type": "onboarding_required",
                    "message": onboarding_result["message"],
                    "next_action": onboarding_result["next_action"]
                }

            # Создаем VPN на trial период
            result = await create_vpn_account(telegram_id, is_trial=True)

            # 🔴 УЛУЧШЕНИЕ: Детальная проверка результата
            logger.info(f"🔍 Детальный результат создания trial VPN: {result}")

            if result and result.get("success"):
                # Отмечаем trial как использованный
                await mark_trial_used(telegram_id)

                # Начисляем баллы за активацию trial
                await update_user_balance(telegram_id, 5)

                return {
                    "type": "success",
                    "message": (
                        f"🎁 <b>Бесплатный период активирован!</b>\n"
                        f"• Срок: {result['expiry_days']} дней\n"
                        f"• ID: {telegram_id}\n"
                        f"• Подключение: <code>{result['connection_string']}</code>\n\n"
                        f"💡 После окончания trial периода вы можете продлить подписку"
                    ),
                    "qrcode_buffer": result.get('qrcode_buffer')
                }
            else:
                # 🔴 УЛУЧШЕНИЕ: Более информативное сообщение об ошибке
                error_detail = result.get("error", "Неизвестная ошибка") if result else "VPN сервер недоступен"

                logger.error(f"❌ Ошибка создания trial: {error_detail}")
                return {
                    "type": "error",
                    "message": (
                        f"❌ Не удалось активировать бесплатный период.\n"
                        f"Причина: {error_detail}\n\n"
                        f"Попробуйте позже или обратитесь в поддержку"
                    )
                }

        except Exception as e:
            logger.error(f"❌ Ошибка активации trial: {e}")
            return {
                "type": "error",
                "message": "❌ Ошибка при активации бесплатного периода"
            }


    async def handle_get_connection(self, telegram_id: int) -> Dict:
        """
        📍 ТОЧКА ВХОДА: Получить данные подключения
        ВЫЗЫВАЕТСЯ ИЗ: handlers.handle_get_connection()
        ВХОД: telegram_id
        ВЫХОД: {type: str, message: str, qrcode_buffer: BytesIO}
        """
        try:
            # Проверяем существование VPN
            existing_vpn = await get_vpn_status(telegram_id)
            logger.info(f"🔍 Проверка VPN статуса для {telegram_id}: {existing_vpn}")

            if not existing_vpn or not existing_vpn.get("success"):
                return {
                    "type": "error",
                    "message": (
                        "❌ <b>VPN не активирован</b>\n"
                        "• Сначала приобретите подписку через «🛒 Получить подписку»"
                    )
                }

            # Получаем connection_string из БД
            connection_string = await get_connection_string(telegram_id)
            logger.info(f"🔍 Получен connection_string из БД: {connection_string is not None}")

            if not connection_string:
                return {
                    "type": "error",
                    "message": (
                        "❌ <b>Данные подключения не найдены</b>\n"
                        "• Попробуйте обновить подписку через «🔄 Продлить подписку»"
                    )
                }

            # Создаем QR-код
            from services.vpn_service import create_qrcode
            qrcode_buffer = create_qrcode(connection_string, str(telegram_id))

            return {
                "type": "success",
                "message": (
                    f"📱 <b>Данные для подключения</b>\n"
                    f"• ID: {telegram_id}\n"
                    f"• Состояние: ✅ Активна\n"
                    f"• Осталось дней: {existing_vpn['expiry_days']}\n\n"
                    f"🔗 <b>Подключение:</b>\n"
                    f"<code>{connection_string}</code>"
                ),
                "qrcode_buffer": qrcode_buffer
            }

        except Exception as e:
            logger.error(f"❌ Ошибка получения подключения: {e}")
            return {
                "type": "error",
                "message": "❌ Ошибка при получении данных подключения"
            }


    async def handle_vpn_status(self, telegram_id: int) -> Dict:
        """
        📍 ТОЧКА ВХОДА: Проверка статуса VPN
        ВЫЗЫВАЕТСЯ ИЗ: handlers.handle_status()
        ВХОД: telegram_id
        ВЫХОД: {type: str, message: str}
        """
        try:
            result = await get_vpn_status(telegram_id)

            if result and result.get("success"):
                status_text = "✅ Активна" if result["lease_is_active"] else "❌ Неактивна"
                return {
                    "type": "success",
                    "message": (
                        f"📊 <b>Статус VPN</b>\n"
                        f"• Состояние: {status_text}\n"
                        f"• Осталось дней: {result['expiry_days']}\n"
                        f"• ID: {telegram_id}"
                    )
                }
            else:
                return {
                    "type": "success",
                    "message": (
                        f"📊 <b>Статус VPN</b>\n"
                        f"• Состояние: ❌ Неактивна\n"
                        f"• VPN не активирован\n"
                        f"• Нажмите «Приобрести подписку»"
                    )
                }

        except Exception as e:
            logger.error(f"❌ Ошибка проверки статуса VPN: {e}")
            return {
                "type": "error",
                "message": "❌ Ошибка при проверке статуса VPN"
            }

    async def handle_user_profile(self, telegram_id: int) -> Dict:
        """
        📍 ТОЧКА ВХОДА: Показать профиль пользователя
        ВЫЗЫВАЕТСЯ ИЗ: handlers.cmd_profile()
        ВХОД: telegram_id
        ВЫХОД: {type: str, message: str}
        """
        try:
            user = await get_user(telegram_id)

            if user:
                profile_text = (
                    f"👤 <b>Ваш профиль</b>\n"
                    f"• ID: {user['telegram_id']}\n"
                    f"• Имя: {user['first_name'] or 'Не указано'}\n"
                    f"• Фамилия: {user['last_name'] or 'Не указано'}\n"
                    f"• Email: {user['email'] or 'Не указан'}\n"
                    f"• Телефон: {user['phone_number'] or 'Не указан'}\n"
                    f"• Баланс: {user['balance']} баллов"
                )
                return {
                    "type": "success",
                    "message": profile_text
                }
            else:
                return {
                    "type": "error",
                    "message": "❌ Профиль не найден"
                }

        except Exception as e:
            logger.error(f"❌ Ошибка получения профиля: {e}")
            return {
                "type": "error",
                "message": "❌ Ошибка при получении профиля"
            }

    async def handle_user_balance(self, telegram_id: int) -> Dict:
        """
        📍 ТОЧКА ВХОДА: Показать баланс баллов
        ВЫЗЫВАЕТСЯ ИЗ: handlers.handle_balance()
        ВХОД: telegram_id
        ВЫХОД: {type: str, message: str}
        """
        try:
            user = await get_user(telegram_id)
            balance = user['balance'] if user else 0

            return {
                "type": "success",
                "message": (
                    f"🏆 <b>Ваши баллы</b>\n"
                    f"• Текущий баланс: {balance} баллов\n"
                    f"• 100 баллов = 1 рубль скидки\n\n"
                    f"💡 Баллы начисляются за:\n"
                    f"• Приглашение друзей\n"
                    f"• Активность в боте\n"
                    f"• Отзывы и предложения"
                )
            }

        except Exception as e:
            logger.error(f"❌ Ошибка получения баланса: {e}")
            return {
                "type": "error",
                "message": "❌ Ошибка при получении баланса"
            }

    async def handle_create_payment(self, telegram_id: int, provider: str, action: str) -> Dict:
        """
        📍 ТОЧКА ВХОДА: Создание платежа
        ВЫЗЫВАЕТСЯ ИЗ: handlers.handle_payment_method()
        ВХОД: telegram_id, provider, action
        ВЫХОД: {type: str, message: str, payment_id: str, ...}
        """
        try:
            config = create_payment_config(
                amount=PAYMENT_AMOUNT,
                description="VPN подписка" if action == "create_vpn" else "Продление VPN подписки",
                success_url=f"https://t.me/your_bot?start=payment_success_{telegram_id}",
                fail_url=f"https://t.me/your_bot?start=payment_fail_{telegram_id}",
                items=[create_payment_item("VPN подписка", PAYMENT_AMOUNT)],
                metadata={"action": action, "telegram_id": telegram_id}
            )

            user_data = {
                "telegram_id": telegram_id,
                "username": "user"  # Будет передано из хендлера
            }

            payment = await create_payment(provider, config, user_data)

            if payment:
                return {
                    "type": "payment_created",
                    "message": (
                        f"💳 <b>Платеж создан</b>\n"
                        f"• Сумма: {PAYMENT_AMOUNT} руб\n"
                        f"• Способ: {payment['provider_name']}\n"
                        f"• Ссылка: {payment['confirmation_url']}\n\n"
                        f"⚠️ После оплаты нажмите «Проверить оплату»"
                    ),
                    "payment_id": payment['payment_id'],
                    "provider": provider,
                    "action": action
                }
            else:
                return {
                    "type": "error",
                    "message": "❌ Ошибка создания платежа. Попробуйте другой способ."
                }

        except Exception as e:
            logger.error(f"❌ Ошибка создания платежа: {e}")
            return {
                "type": "error",
                "message": "❌ Ошибка при создании платежа"
            }

    async def handle_check_payment(self, payment_id: str, provider: str, action: str, telegram_id: int) -> Dict:
        """
        📍 ТОЧКА ВХОДА: Проверка статуса оплаты
        ВЫЗЫВАЕТСЯ ИЗ: handlers.handle_payment_confirmation()
        ВХОД: payment_id, provider, action, telegram_id
        ВЫХОД: {type: str, message: str}
        """
        try:
            if await check_payment(payment_id, provider):
                # Выполняем действие в зависимости от типа
                if action == "create_vpn":
                    vpn_result = await create_vpn_account(telegram_id)
                elif action == "renew_vpn":
                    vpn_result = await renew_vpn_account(telegram_id)
                else:
                    vpn_result = None

                # Начисляем баллы за оплату
                await update_user_balance(telegram_id, 10)

                if vpn_result and vpn_result.get("success"):
                    return {
                        "type": "success",
                        "message": "✅ Оплата подтверждена! VPN услуга активирована."
                    }
                else:
                    return {
                        "type": "success",
                        "message": "✅ Оплата подтверждена! Но возникла ошибка при активации услуги."
                    }
            else:
                return {
                    "type": "error",
                    "message": "❌ Оплата не найдена. Попробуйте позже."
                }

        except Exception as e:
            logger.error(f"❌ Ошибка проверки платежа: {e}")
            return {
                "type": "error",
                "message": "❌ Ошибка при проверке платежа"
            }


# =============================================
# 🎯 ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ДЛЯ ИСПОЛЬЗОВАНИЯ
# =============================================
action_service = ActionService()

# =============================================
# 📋 ДОКУМЕНТАЦИЯ ПО ТОЧКАМ ВХОДА ACTION SERVICE
# =============================================
"""
🏗️ АРХИТЕКТУРА ACTION SERVICE:

📍 ОСНОВНЫЕ ТОЧКИ ВХОДА:

1. handle_get_vpn(telegram_id, username=None)
   • НАЗНАЧЕНИЕ: Создание новой VPN подписки
   • ИСПОЛЬЗУЕТ: services.vpn_service.create_vpn_account()
   • ВОЗВРАЩАЕТ: {type, message, qrcode_path}

2. handle_renew_vpn(telegram_id) 
   • НАЗНАЧЕНИЕ: Продление существующей VPN подписки
   • ИСПОЛЬЗУЕТ: services.vpn_service.renew_vpn_account()
   • ВОЗВРАЩАЕТ: {type, message}

3. handle_vpn_status(telegram_id)
   • НАЗНАЧЕНИЕ: Проверка статуса VPN подписки
   • ИСПОЛЬЗУЕТ: services.vpn_service.get_vpn_status() 
   • ВОЗВРАЩАЕТ: {type, message}

4. handle_user_profile(telegram_id)
   • НАЗНАЧЕНИЕ: Получение профиля пользователя
   • ИСПОЛЬЗУЕТ: services.database.get_user()
   • ВОЗВРАЩАЕТ: {type, message}

5. handle_user_balance(telegram_id)
   • НАЗНАЧЕНИЕ: Получение баланса баллов
   • ИСПОЛЬЗУЕТ: services.database.get_user()
   • ВОЗВРАЩАЕТ: {type, message}

6. handle_create_payment(telegram_id, provider, action)
   • НАЗНАЧЕНИЕ: Создание платежа
   • ИСПОЛЬЗУЕТ: services.payment.create_payment()
   • ВОЗВРАЩАЕТ: {type, message, payment_id, provider, action}

7. handle_check_payment(payment_id, provider, action, telegram_id)
   • НАЗНАЧЕНИЕ: Проверка статуса оплаты
   • ИСПОЛЬЗУЕТ: services.payment.check_payment()
   • ВОЗВРАЩАЕТ: {type, message}

🔄 ТИПЫ ВОЗВРАЩАЕМЫХ РЕЗУЛЬТАТОВ:
• "success" - операция выполнена успешно
• "error" - произошла ошибка
• "payment_required" - требуется оплата
• "onboarding_required" - требуется пройти onboarding

🎯 ИНТЕГРАЦИЯ С ONBOARDING:
• handle_get_vpn() автоматически запускает onboarding
• Настройка шагов в services.onboarding.py
• Можно отключить через конфигурацию
"""
