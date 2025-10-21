from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, FSInputFile
import logging
import os

from app.services import registration_manager
from app.handlers.action_service import action_service  # ⚠️ ИСПРАВЛЕНО
from app.handlers.keyboards import (  # ⚠️ ИСПРАВЛЕНО
    get_main_menu, get_profile_menu, get_subs_menu, get_instructions_menu,
    get_payment_methods, get_back_only, get_payment_check
)
from app.config import (
    WELCOME_MESSAGE, ABOUT_MESSAGE, INSTRUCTIONS_MESSAGE, SUBS_MESSAGE,
    COLLECT_EMAIL, COLLECT_PHONE, COLLECT_FIRST_NAME, COLLECT_LAST_NAME, COLLECT_PATRONYMIC
)

logger = logging.getLogger(__name__)
router = Router()


# =============================================
# 🏗️ СОСТОЯНИЯ ДЛЯ РЕГИСТРАЦИИ
# =============================================
class RegistrationStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_phone = State()
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_patronymic = State()


# =============================================
# 🏠 ОСНОВНЫЕ КОМАНДЫ MENU BUTTON
# =============================================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """
    📍 ТОЧКА ВХОДА: /start
    ЗАПУСК: При первом запуске бота или команде /start
    РЕЗУЛЬТАТ: Главное меню + регистрация при необходимости
    """
    telegram_id = message.from_user.id
    username = message.from_user.username

    # Сохраняем базовые данные
    from app.services.database import save_user
    await save_user(telegram_id, username)

    # Проверяем, нужно ли собирать дополнительные данные
    await process_registration(message, state)

    # Показываем главное меню
    await message.answer(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """
    📍 ТОЧКА ВХОДА: /profile
    ЗАПУСК: Команда /profile или кнопка "Личный кабинет"
    РЕЗУЛЬТАТ: Информация о профиле пользователя
    """
    telegram_id = message.from_user.id

    # ВСЯ логика в ActionService
    result = await action_service.handle_user_profile(telegram_id)
    await message.answer(result["message"], reply_markup=get_profile_menu(), parse_mode="HTML")


@router.message(Command("subs"))
async def cmd_subs(message: Message):
    """
    📍 ТОЧКА ВХОДА: /subs
    ЗАПУСК: Команда /subs или кнопка "Управление подписками"
    РЕЗУЛЬТАТ: Меню управления подписками VPN
    """
    await message.answer(
        SUBS_MESSAGE,
        reply_markup=get_subs_menu(),
        parse_mode="HTML"
    )


@router.message(Command("instructions"))
async def cmd_instructions(message: Message):
    """
    📍 ТОЧКА ВХОДА: /instructions
    ЗАПУСК: Команда /instructions или кнопка "Инструкции"
    РЕЗУЛЬТАТ: Инструкции по подключению VPN
    """
    await message.answer(
        INSTRUCTIONS_MESSAGE,
        reply_markup=get_instructions_menu(),
        parse_mode="HTML"
    )


# =============================================
# 🔄 ОБРАБОТЧИКИ REPLY-КЛАВИАТУР
# =============================================

@router.message(F.text == "🏠 Главное меню")
async def handle_main_menu(message: Message, state: FSMContext):
    """
    📍 ТОЧКА ВХОДА: Кнопка "🏠 Главное меню"
    ЗАПУСК: Нажатие на кнопку главного меню
    РЕЗУЛЬТАТ: Возврат в главное меню + очистка состояния
    """
    await state.clear()
    await message.answer("🏠 Главное меню:", reply_markup=get_main_menu())


@router.message(F.text == "🚀 Приобрести подписку на VPN")
async def handle_get_vpn(message: Message, state: FSMContext):
    """
    📍 ТОЧКА ВХОДА: Кнопка "🚀 Приобрести подписку на VPN"
    ЗАПУСК: Нажатие кнопки получения VPN
    РЕЗУЛЬТАТ:
      - Если оплата включена: выбор способа оплаты
      - Если оплата отключена: сразу создание VPN
    """
    telegram_id = message.from_user.id
    username = message.from_user.username

    # ВСЯ логика в ActionService
    result = await action_service.handle_get_vpn(telegram_id, username)

    if result["type"] == "payment_required":
        await message.answer(result["message"], reply_markup=get_payment_methods())
        await state.set_state("waiting_for_payment_method")
        await state.update_data(action="create_vpn")
    else:
        await message.answer(result["message"], reply_markup=get_main_menu(), parse_mode="HTML")

        # Отправляем QR-код если есть
        if result.get("qrcode_path") and os.path.exists(result["qrcode_path"]):
            photo = FSInputFile(result["qrcode_path"])
            await message.answer_photo(photo, caption="📱 QR-код для подключения")


@router.message(F.text == "🎁 Воспользоваться бесплатным периодом")
async def handle_free_period(message: Message):
    """
    📍 ТОЧКА ВХОДА: Кнопка "🎁 Воспользоваться бесплатным периодом"
    ЗАПУСК: Нажатие кнопки бесплатного периода
    РЕЗУЛЬТАТ: Активация VPN без оплаты (если доступно)
    """
    telegram_id = message.from_user.id
    username = message.from_user.username

    # ВСЯ логика в ActionService
    result = await action_service.handle_get_vpn(telegram_id, username)
    await message.answer(result["message"], reply_markup=get_main_menu(), parse_mode="HTML")


@router.message(F.text == "📊 Узнать статус")
async def handle_status(message: Message):
    """
    📍 ТОЧКА ВХОДА: Кнопка "📊 Узнать статус"
    ЗАПУСК: Нажатие кнопки проверки статуса
    РЕЗУЛЬТАТ: Информация о текущем статусе VPN подписки
    """
    telegram_id = message.from_user.id

    # ВСЯ логика в ActionService
    result = await action_service.handle_vpn_status(telegram_id)
    await message.answer(result["message"], reply_markup=get_subs_menu(), parse_mode="HTML")


@router.message(F.text == "🔄 Продлить подписку")
async def handle_renew(message: Message, state: FSMContext):
    """
    📍 ТОЧКА ВХОДА: Кнопка "🔄 Продлить подписку"
    ЗАПУСК: Нажатие кнопки продления подписки
    РЕЗУЛЬТАТ:
      - Если оплата включена: выбор способа оплаты
      - Если оплата отключена: сразу продление VPN
    """
    telegram_id = message.from_user.id

    # ВСЯ логика в ActionService
    result = await action_service.handle_renew_vpn(telegram_id)

    if result["type"] == "payment_required":
        await message.answer(result["message"], reply_markup=get_payment_methods())
        await state.set_state("waiting_for_payment_method")
        await state.update_data(action="renew_vpn")
    else:
        await message.answer(result["message"], reply_markup=get_main_menu(), parse_mode="HTML")


# =============================================
# 👤 ЛИЧНЫЙ КАБИНЕТ
# =============================================

@router.message(F.text == "📝 Дополнить информацию о себе")
async def handle_complete_profile(message: Message, state: FSMContext):
    """
    📍 ТОЧКА ВХОДА: Кнопка "📝 Дополнить информацию о себе"
    ЗАПУСК: Нажатие кнопки дополнения профиля
    РЕЗУЛЬТАТ: Запуск процесса сбора дополнительных данных
    """
    await process_registration(message, state)


@router.message(F.text == "🏆 Мои баллы")
async def handle_balance(message: Message):
    """
    📍 ТОЧКА ВХОДА: Кнопка "🏆 Мои баллы"
    ЗАПУСК: Нажатие кнопки просмотра баланса
    РЕЗУЛЬТАТ: Информация о бонусных баллах пользователя
    """
    telegram_id = message.from_user.id

    # ВСЯ логика в ActionService
    result = await action_service.handle_user_balance(telegram_id)
    await message.answer(result["message"], reply_markup=get_profile_menu(), parse_mode="HTML")


@router.message(F.text == "👥 Пригласить друга")
async def handle_invite(message: Message):
    """
    📍 ТОЧКА ВХОДА: Кнопка "👥 Пригласить друга"
    ЗАПУСК: Нажатие кнопки приглашения друга
    РЕЗУЛЬТАТ: Реферальная ссылка и информация о бонусах
    """
    telegram_id = message.from_user.id
    invite_link = f"https://t.me/your_bot?start={telegram_id}"

    await message.answer(
        f"👥 <b>Пригласите друга</b>\n\n"
        f"🔗 Ваша реферальная ссылка:\n"
        f"<code>{invite_link}</code>\n\n"
        f"💎 За каждого приглашенного друга:\n"
        f"• Вы получаете 50 баллов\n"
        f"• Друг получает 20 баллов\n"
        f"• Бонус за активность друга",
        reply_markup=get_profile_menu(),
        parse_mode="HTML"
    )


@router.message(F.text == "ℹ️ О сервисе")
async def handle_about(message: Message):
    """
    📍 ТОЧКА ВХОДА: Кнопка "ℹ️ О сервисе"
    ЗАПУСК: Нажатие кнопки "О сервисе"
    РЕЗУЛЬТАТ: Информация о VPN сервисе
    """
    await message.answer(ABOUT_MESSAGE, reply_markup=get_main_menu(), parse_mode="HTML")


# =============================================
# 💰 ОБРАБОТКА ОПЛАТЫ
# =============================================

@router.message(F.state == "waiting_for_payment_method")
async def handle_payment_method(message: Message, state: FSMContext):
    """
    📍 ТОЧКА ВХОДА: Состояние выбора способа оплаты
    ЗАПУСК: После выбора "Приобрести подписку" или "Продлить подписку"
    РЕЗУЛЬТАТ: Создание платежа и переход к подтверждению
    """
    if message.text == "⬅️ Назад":
        await state.clear()
        await message.answer("🏠 Главное меню:", reply_markup=get_main_menu())
        return

    # Определяем действие
    data = await state.get_data()
    action = data.get("action", "create_vpn")

    telegram_id = message.from_user.id
    provider_map = {
        "💳 ЮMoney": "yoomoney",
        "📱 СБП": "sbp",
        "💳 Банковская карта": "card"
    }

    provider = provider_map.get(message.text)
    if not provider:
        await message.answer("❌ Выберите способ оплаты из списка:")
        return

    # ВСЯ логика в ActionService
    result = await action_service.handle_create_payment(telegram_id, provider, action)

    if result["type"] == "payment_created":
        await message.answer(result["message"], reply_markup=get_payment_check(), parse_mode="HTML")
        await state.update_data(
            payment_id=result['payment_id'],
            provider=provider,
            action=action
        )
        await state.set_state("waiting_for_payment_confirmation")
    else:
        await message.answer(result["message"], reply_markup=get_payment_methods())


@router.message(F.state == "waiting_for_payment_confirmation")
async def handle_payment_confirmation(message: Message, state: FSMContext):
    """
    📍 ТОЧКА ВХОДА: Состояние подтверждения оплаты
    ЗАПУСК: После создания платежа
    РЕЗУЛЬТАТ: Проверка статуса оплаты и активация услуги
    """
    if message.text == "⬅️ Назад":
        await message.answer("💳 Выберите способ оплаты:", reply_markup=get_payment_methods())
        await state.set_state("waiting_for_payment_method")
        return

    if message.text == "✅ Проверить оплату":
        data = await state.get_data()
        payment_id = data.get("payment_id")
        provider = data.get("provider")
        action = data.get("action")
        telegram_id = message.from_user.id

        # ВСЯ логика в ActionService
        result = await action_service.handle_check_payment(payment_id, provider, action, telegram_id)
        await message.answer(result["message"], reply_markup=get_main_menu())
        await state.clear()
    else:
        await message.answer("Нажмите «Проверить оплату» после завершения оплаты")


# =============================================
# 🔧 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================

async def process_registration(message: Message, state: FSMContext):
    """Обработка регистрации - запрашивает недостающие поля"""
    telegram_id = message.from_user.id

    # Настраиваем регистрацию по перемычкам
    registration_manager.configure_fields(
        email=COLLECT_EMAIL,
        phone=COLLECT_PHONE,
        first_name=COLLECT_FIRST_NAME,
        last_name=COLLECT_LAST_NAME,
        patronymic=COLLECT_PATRONYMIC
    )

    # Получаем следующее поле для запроса
    next_field = registration_manager.get_next_field()
    if next_field:
        field_name, next_state = next_field
        question = registration_manager.get_question(field_name)

        await message.answer("📝 Завершите регистрацию:", reply_markup=get_back_only())
        await message.answer(question)
        await state.set_state(next_state)


# =============================================
# 🔄 ОБРАБОТЧИКИ РЕГИСТРАЦИИ
# =============================================

@router.message(RegistrationStates.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    await _process_registration_field(message, state, "email")


@router.message(RegistrationStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    await _process_registration_field(message, state, "phone")


@router.message(RegistrationStates.waiting_for_first_name)
async def process_first_name(message: Message, state: FSMContext):
    await _process_registration_field(message, state, "first_name")


@router.message(RegistrationStates.waiting_for_last_name)
async def process_last_name(message: Message, state: FSMContext):
    await _process_registration_field(message, state, "last_name")


@router.message(RegistrationStates.waiting_for_patronymic)
async def process_patronymic(message: Message, state: FSMContext):
    await _process_registration_field(message, state, "patronymic")


async def _process_registration_field(message: Message, state: FSMContext, field_name: str):
    """Универсальный обработчик полей регистрации"""
    if message.text == "⬅️ Назад":
        await state.clear()
        await message.answer("🏠 Главное меню:", reply_markup=get_main_menu())
        return

    value = message.text.strip()

    # Валидируем поле
    if not registration_manager.validate_field(field_name, value):
        await message.answer(f"❌ Некорректное значение. Попробуйте еще раз:")
        return

    # Сохраняем в базу
    telegram_id = message.from_user.id
    from app.services.database import save_user
    await save_user(telegram_id, **{field_name: value})

    # Переходим к следующему полю или завершаем регистрацию
    next_field = registration_manager.get_next_field(await state.get_state())
    if next_field:
        next_field_name, next_state = next_field
        question = registration_manager.get_question(next_field_name)
        await message.answer(question)
        await state.set_state(next_state)
    else:
        # Регистрация завершена
        await message.answer(
            "✅ Регистрация завершена! Теперь вы можете использовать все функции бота.",
            reply_markup=get_main_menu()
        )
        await state.clear()


# =============================================
# 📋 ДОКУМЕНТАЦИЯ ПО ТОЧКАМ ВХОДА
# =============================================
"""
🏗️ АРХИТЕКТУРА ТОЧЕК ВХОДА:

📍 КОМАНДЫ MENU BUTTON (слева внизу):
• /start     - Перезапуск бота, главное меню
• /profile   - Личный кабинет  
• /subs      - Управление подписками
• /instructions - Инструкции по подключению

📍 REPLY-КЛАВИАТУРЫ (основные кнопки):
• 🏠 Главное меню              - Возврат в главное меню
• 🚀 Приобрести подписку на VPN - Начало процесса получения VPN
• 🎁 Бесплатный период         - Активация без оплаты
• 📊 Узнать статус             - Проверка статуса VPN
• 🔄 Продлить подписку         - Продление существующей подписки

📍 ЛИЧНЫЙ КАБИНЕТ:
• 📝 Дополнить информацию о себе - Сбор дополнительных данных
• 🏆 Мои баллы                 - Просмотр бонусных баллов  
• 👥 Пригласить друга          - Реферальная программа

📍 СОСТОЯНИЯ FSM:
• waiting_for_payment_method     - Выбор способа оплаты
• waiting_for_payment_confirmation - Подтверждение оплаты
• RegistrationStates.*           - Сбор данных регистрации

🔄 ПОТОК ДАННЫХ:
Пользователь → Handler → ActionService → Services → База/API
"""