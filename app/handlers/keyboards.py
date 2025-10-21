from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BotCommand
from aiogram import Bot

# =============================================
# 📌 MENU BUTTON (слева внизу)
# =============================================

async def setup_menu_button(bot: Bot):
    """
    📍 ТОЧКА ВХОДА: Настройка меню-кнопки
    ВЫЗЫВАЕТСЯ ИЗ: main.py при запуске бота
    РЕЗУЛЬТАТ: Установка команд меню слева внизу
    """
    await bot.set_my_commands([
        BotCommand(command="/start", description="🔄 Перезапустить бота"),
        BotCommand(command="/profile", description="👤 Личный кабинет"),
        BotCommand(command="/subs", description="📦 Управление подписками"),
        BotCommand(command="/instructions", description="📚 Инструкции"),
    ])

# =============================================
# 📌 REPLY-КЛАВИАТУРЫ ДЛЯ КАЖДОГО СОСТОЯНИЯ
# =============================================

def get_main_menu():
    """
    📍 ТОЧКА ВХОДА: Главное меню после /start
    ВЫЗЫВАЕТСЯ ИЗ: handlers.cmd_start(), handlers.handle_main_menu()
    РЕЗУЛЬТАТ: Клавиатура с основными опциями
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Приобрести подписку на VPN")],
            [KeyboardButton(text="🎁 Воспользоваться бесплатным периодом")],
            [KeyboardButton(text="ℹ️ О сервисе")]
        ],
        resize_keyboard=True
    )

def get_profile_menu():
    """
    📍 ТОЧКА ВХОДА: Личный кабинет /profile
    ВЫЗЫВАЕТСЯ ИЗ: handlers.cmd_profile(), handlers.handle_balance()
    РЕЗУЛЬТАТ: Клавиатура управления профилем
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Дополнить информацию о себе")],
            [KeyboardButton(text="🏆 Мои баллы")],
            [KeyboardButton(text="👥 Пригласить друга")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )

def get_subs_menu():
    """
    📍 ТОЧКА ВХОДА: Управление подписками /subs
    ВЫЗЫВАЕТСЯ ИЗ: handlers.cmd_subs(), handlers.handle_status()
    РЕЗУЛЬТАТ: Клавиатура управления VPN подписками
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Получить подписку")],
            [KeyboardButton(text="🔄 Продлить подписку")],
            [KeyboardButton(text="📊 Узнать статус")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )

def get_instructions_menu():
    """
    📍 ТОЧКА ВХОДА: Инструкции /instructions
    ВЫЗЫВАЕТСЯ ИЗ: handlers.cmd_instructions()
    РЕЗУЛЬТАТ: Клавиатура с инструкциями
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Как подключить услугу")],
            [KeyboardButton(text="🔄 Как продлить услугу")],
            [KeyboardButton(text="❓ Частые вопросы")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )

# =============================================
# 📌 ОПЛАТА
# =============================================

def get_payment_methods():
    """
    📍 ТОЧКА ВХОДА: Выбор способа оплаты
    ВЫЗЫВАЕТСЯ ИЗ: handlers.handle_get_vpn(), handlers.handle_renew()
    РЕЗУЛЬТАТ: Клавиатура с вариантами оплаты
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💳 ЮMoney"), KeyboardButton(text="📱 СБП")],
            [KeyboardButton(text="💳 Банковская карта")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

# =============================================
# 📌 ПРОСТЫЕ КЛАВИАТУРЫ
# =============================================

def get_back_only():
    """
    📍 ТОЧКА ВХОДА: Только кнопка Назад
    ВЫЗЫВАЕТСЯ ИЗ: handlers.process_registration()
    РЕЗУЛЬТАТ: Минимальная клавиатура для возврата
    """
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад")]],
        resize_keyboard=True
    )

def get_main_menu_only():
    """
    📍 ТОЧКА ВХОДА: Только кнопка Главное меню
    ВЫЗЫВАЕТСЯ ИЗ: Различных состояний для возврата
    РЕЗУЛЬТАТ: Клавиатура с одной кнопкой главного меню
    """
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 Главное меню")]],
        resize_keyboard=True
    )

def get_payment_check():
    """
    📍 ТОЧКА ВХОДА: Проверка оплаты
    ВЫЗЫВАЕТСЯ ИЗ: handlers.handle_payment_method()
    РЕЗУЛЬТАТ: Клавиатура для подтверждения оплаты
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Проверить оплату")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )


# =============================================
# 📋 ДОКУМЕНТАЦИЯ ПО КЛАВИАТУРАМ
# =============================================
"""
🏗️ АРХИТЕКТУРА КЛАВИАТУР:

📍 ТИПЫ КЛАВИАТУР:

1. ОСНОВНЫЕ МЕНЮ:
   • get_main_menu()     - Главное меню после старта
   • get_profile_menu()  - Личный кабинет  
   • get_subs_menu()     - Управление подписками
   • get_instructions_menu() - Инструкции

2. СПЕЦИАЛИЗИРОВАННЫЕ:
   • get_payment_methods() - Выбор способа оплаты
   • get_payment_check()   - Проверка оплаты

3. ПРОСТЫЕ:
   • get_back_only()       - Только кнопка "Назад"
   • get_main_menu_only()  - Только кнопка "Главное меню"

🎯 ПРИНЦИПЫ ИСПОЛЬЗОВАНИЯ:

• Каждая клавиатура соответствует определенному состоянию
• resize_keyboard=True для адаптации под экран
• Кнопки группируются по смыслу в рядах
• Всегда есть кнопка возврата в главное меню

🔄 ИНТЕГРАЦИЯ С HANDLERS:
Handlers → вызывают клавиатуры → отправляют пользователю
"""
