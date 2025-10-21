import os
from dotenv import load_dotenv

load_dotenv()

# === НАСТРОЙКИ БАЗЫ ДАННЫХ ===
DB_NAME = os.getenv("DB_NAME", "xui_bot_db")
DB_USER = os.getenv("DB_USER", "xui_bot_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "xui_bot_password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# === НАСТРОЙКИ 3x-ui ===
XUI_PANEL_URL = os.getenv('XUI_PANEL_URL')
XUI_USERNAME = os.getenv('XUI_USERNAME')
XUI_PASSWORD = os.getenv('XUI_PASSWORD')
INBOUND_ID = int(os.getenv('INBOUND_ID', '1'))
DATA_LIMIT_GB = int(os.getenv('DATA_LIMIT_GB', '0'))
EXPIRY_TIME = int(os.getenv('EXPIRY_TIME', '30'))
XUI_EXTERNAL_IP = os.getenv('XUI_EXTERNAL_IP')
SERVER_PORT = os.getenv('SERVER_PORT', '443')
QRCODE_DIR = os.getenv('QRCODE_DIR', 'qrcodes')

# === НАСТРОЙКИ TELEGRAM ===
BOT_TOKEN = os.getenv('BOT_TOKEN')

# === ПЕРЕМЫЧКИ РЕГИСТРАЦИИ ===
COLLECT_EMAIL = os.getenv('COLLECT_EMAIL', 'False').lower() == 'true'
COLLECT_PHONE = os.getenv('COLLECT_PHONE', 'False').lower() == 'true'
COLLECT_FIRST_NAME = os.getenv('COLLECT_FIRST_NAME', 'False').lower() == 'true'
COLLECT_LAST_NAME = os.getenv('COLLECT_LAST_NAME', 'False').lower() == 'true'
COLLECT_PATRONYMIC = os.getenv('COLLECT_PATRONYMIC', 'False').lower() == 'true'

# === ПЕРЕМЫЧКИ ОПЛАТЫ ===
PAYMENT_ENABLED = os.getenv('PAYMENT_ENABLED', 'False').lower() == 'true'
PAYMENT_AMOUNT = float(os.getenv('PAYMENT_AMOUNT', '100.0'))
PAYMENT_YOOMONEY = os.getenv('PAYMENT_YOOMONEY', 'False').lower() == 'true'
PAYMENT_SBP = os.getenv('PAYMENT_SBP', 'False').lower() == 'true'
PAYMENT_CARD = os.getenv('PAYMENT_CARD', 'False').lower() == 'true'

# === ТЕКСТЫ И ОПИСАНИЯ ===
WELCOME_MESSAGE = """
🤖 Добро пожаловать в VPN Сервис!

🔒 <b>Безопасный и анонимный доступ</b>
• Защита ваших данных
• Высокая скорость подключения
• Простая настройка

📱 <b>Как это работает?</b>
1. Нажмите «Приобрести подписку на VPN»
2. Оплатите услугу (если требуется)
3. Получите данные для подключения
4. Наслаждайтесь безопасным интернетом

💡 <b>Поддержка</b>
Если возникнут вопросы - обращайтесь!
"""

ABOUT_MESSAGE = """
ℹ️ <b>О нашем сервисе</b>

Мы предоставляем качественные VPN услуги с 2024 года.

<b>Наши преимущества:</b>
• 🔒 Высокая безопасность
• 🚀 Максимальная скорость  
• 📱 Простота использования
• 🛠 Круглосуточная поддержка

<b>Технологии:</b>
• Протокол VLESS + Reality
• Современное шифрование
• Стабильные сервера
"""

INSTRUCTIONS_MESSAGE = """
📚 <b>Инструкции по подключению</b>

<b>Для Android:</b>
1. Скачайте приложение V2RayNG
2. Нажмите ➕ и выберите «Сканировать QR-код»
3. Отсканируйте QR-код из бота
4. Нажмите подключить

<b>Для iOS:</b>  
1. Скачайте приложение Streisand
2. Нажмите ➕ и выберите «Импорт из буфера обмена»
3. Скопируйте ссылку из бота
4. Нажмите подключить

<b>Для Windows:</b>
1. Скачайте Nekoray
2. Нажмите «Add» → «From clipboard»
3. Скопируйте ссылку из бота
4. Нажмите подключить
"""

PROFILE_MESSAGE = """
👤 <b>Личный кабинет</b>

Здесь вы можете управлять своей учетной записью:
• 📝 Дополнить информацию о себе
• 🏆 Посмотреть накопленные баллы
• 👥 Пригласить друзей и получить бонусы
"""

SUBS_MESSAGE = """
📦 <b>Управление подписками</b>

• 🛒 Получить новую подписку
• 🔄 Продлить текущую подписку  
• 📊 Узнать статус и остаток дней
"""