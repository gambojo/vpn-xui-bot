import logging
import uuid
import qrcode
import os
from datetime import datetime, timedelta
from py3xui import AsyncApi, Client
from app.config import XUI_PANEL_URL, XUI_USERNAME, XUI_PASSWORD, INBOUND_ID, \
    DATA_LIMIT_GB, EXPIRY_TIME, XUI_EXTERNAL_IP, SERVER_PORT, QRCODE_DIR

logger = logging.getLogger(__name__)


# 🔧 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (синхронные)
def get_expiry_time(expiry_days):
    """Просто вычисляет expiry_time в ms"""
    if expiry_days != 0:
        expire_dt = datetime.now() + timedelta(days=expiry_days)
        return int(expire_dt.timestamp() * 1000)
    return 0


def get_total_gb(total_gb):
    """Просто вычисляет лимит трафика в байтах"""
    if total_gb != 0:
        return 1000 * 1024 * 1024 * total_gb
    return 0


def get_expiry_date(expire_ms):
    """Просто вычисляет оставшиеся дни"""
    if expire_ms == 0:
        return "Не ограничено"
    now_ms = int(datetime.now().timestamp() * 1000)
    delta_ms = expire_ms - now_ms
    return max(delta_ms // (1000 * 60 * 60 * 24), 0)


def get_connection_string(email, inbound, client_uuid):
    """Просто генерирует строку подключения"""
    public_key = inbound.stream_settings.reality_settings.get("settings").get("publicKey")
    website_name = inbound.stream_settings.reality_settings.get("serverNames")[0]
    short_id = inbound.stream_settings.reality_settings.get("shortIds")[0]
    remark = inbound.remark

    connection_string = (
        f"vless://{client_uuid}@{XUI_EXTERNAL_IP}:{SERVER_PORT}"
        f"?type=tcp&security=reality&pbk={public_key}&fp=firefox&sni={website_name}"
        f"&sid={short_id}&spx=%2F#{remark}-{email}"
    )
    return connection_string


def create_qrcode(connection_string, email):
    """Просто создает QR-код"""
    os.makedirs(QRCODE_DIR, exist_ok=True)
    qrcode_path = os.path.join(QRCODE_DIR, f"{email}.png")
    img = qrcode.make(connection_string)
    img.save(qrcode_path)
    return qrcode_path


# 🔄 АСИНХРОННЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С API
async def api_connect():
    """Асинхронное подключение к API"""
    try:
        api = AsyncApi(XUI_PANEL_URL, XUI_USERNAME, XUI_PASSWORD)
        await api.login()
        logger.info("✅ Успешная асинхронная авторизация в 3x-ui")
        return api
    except Exception as e:
        logger.error(f"❌ Ошибка асинхронной авторизации в 3x-ui: {e}")
        return None


async def get_inbound(api, inbound_id):
    """Асинхронное получение инбаунда"""
    try:
        inbound = await api.inbound.get_by_id(inbound_id)
        logger.info("✅ Успешное получение данных об инбаунде")
        return inbound
    except Exception as e:
        logger.error(f"❌ Ошибка получения данных об инбаунде: {e}")
        return None


async def get_client_by_email(api, email):
    """Асинхронный поиск клиента по email"""
    try:
        client = await api.client.get_by_email(email)
        logger.info(f"✅ Клиент {email} найден")
        return client
    except Exception as e:
        logger.info(f"⚠️ Клиента {email} не существует: {e}")
        return None


async def add_client(api, email, inbound_id, expiry_time, total_gb):
    """Асинхронное создание клиента"""
    try:
        new_client = Client(
            id=str(uuid.uuid4()),
            email=email,
            enable=True,
            flow="xtls-rprx-vision",
            expiry_time=expiry_time,
            total_gb=total_gb
        )
        client = await api.client.add(inbound_id, [new_client])
        logger.info(f"✅ Клиент {email} добавлен")
        return client
    except Exception as e:
        logger.error(f"❌ Ошибка добавления клиента: {e}")
        return None


async def get_client_from_inbound(inbound, email):
    """Поиск клиента в инбаунде по email"""
    try:
        client = None
        for c in inbound.settings.clients:
            if c.email == email:
                client = c
                break
        if client:
            logger.info(f"Найден клиент с ID: {client.id}")
        else:
            raise ValueError(f"Клиент с email {email} не найден в инбаунде")
        return client
    except Exception as e:
        logger.error(f"❌ Ошибка получения клиента из инбаунда: {e}")
        return None


async def update_client(api, email, expiry_time, total_gb):
    """Асинхронное обновление клиента"""
    try:
        # Получаем клиента по email
        client_by_email = await api.client.get_by_email(email)
        if not client_by_email:
            raise ValueError(f"Клиент {email} не найден для обновления")

        # Получаем inbound чтобы найти UUID клиента
        inbound = await get_inbound(api, INBOUND_ID)
        client_in_inbound = await get_client_from_inbound(inbound, email)

        # Обновляем данные
        client_by_email.total_gb = total_gb
        client_by_email.expiry_time = expiry_time
        client_by_email.id = client_in_inbound.id  # Устанавливаем правильный UUID

        await api.client.update(client_by_email.id, client_by_email)
        logger.info(f"✅ Клиент {email} обновлен")
        return client_by_email
    except Exception as e:
        logger.error(f"❌ Ошибка обновления клиента: {e}")
        return None


# ⭐⭐ ТОЧКИ ВХОДА ⭐⭐
async def create_vpn_account(telegram_id: int):
    """ТОЧКА ВХОДА - создать VPN аккаунт"""
    try:
        email = str(telegram_id)
        expiry_time = get_expiry_time(EXPIRY_TIME)
        total_gb = get_total_gb(DATA_LIMIT_GB)

        # Подключаемся к API
        api = await api_connect()
        if not api:
            return None

        # Проверяем существование клиента
        existing_client = await get_client_by_email(api, email)
        if existing_client:
            logger.info(f"⚠️ Клиент {email} уже существует")
            return None

        # Создаем клиента
        client = await add_client(api, email, INBOUND_ID, expiry_time, total_gb)
        if not client:
            return None

        # Получаем данные для подключения
        inbound = await get_inbound(api, INBOUND_ID)
        client_in_inbound = await get_client_from_inbound(inbound, email)

        connection_string = get_connection_string(email, inbound, client_in_inbound.id)
        qrcode_path = create_qrcode(connection_string, email)

        return {
            "success": True,
            "client_id": client_in_inbound.id,
            "lease_is_active": True,
            "qrcode_path": qrcode_path,
            "expiry_time": expiry_time,
            "expiry_days": EXPIRY_TIME,
            "connection_string": connection_string
        }

    except Exception as e:
        logger.error(f"❌ Ошибка создания VPN аккаунта: {e}")
        return None


async def get_vpn_status(telegram_id: int):
    """ТОЧКА ВХОДА - получить статус VPN"""
    try:
        email = str(telegram_id)

        api = await api_connect()
        if not api:
            return None

        # Получаем клиента
        client = await get_client_by_email(api, email)
        if not client:
            return None

        # Получаем inbound для дополнительной информации
        inbound = await get_inbound(api, INBOUND_ID)
        client_in_inbound = await get_client_from_inbound(inbound, email)

        expiry_days = get_expiry_date(client.expiry_time)

        return {
            "success": True,
            "client_id": client_in_inbound.id,
            "lease_is_active": client.enable,
            "expiry_days": expiry_days
        }

    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса VPN: {e}")
        return None


async def renew_vpn_account(telegram_id: int):
    """ТОЧКА ВХОДА - продлить VPN аккаунт"""
    try:
        email = str(telegram_id)
        expiry_time = get_expiry_time(EXPIRY_TIME)
        total_gb = get_total_gb(DATA_LIMIT_GB)

        api = await api_connect()
        if not api:
            return None

        # Проверяем существование клиента
        client = await get_client_by_email(api, email)
        if not client:
            logger.info(f"⚠️ Клиент {email} не найден для продления")
            return None

        # Обновляем клиента
        updated_client = await update_client(api, email, expiry_time, total_gb)
        if not updated_client:
            return None

        # Получаем обновленные данные для подключения
        inbound = await get_inbound(api, INBOUND_ID)
        client_in_inbound = await get_client_from_inbound(inbound, email)

        connection_string = get_connection_string(email, inbound, client_in_inbound.id)
        qrcode_path = create_qrcode(connection_string, email)

        return {
            "success": True,
            "client_id": updated_client.id,
            "lease_is_active": updated_client.enable,
            "qrcode_path": qrcode_path,
            "expiry_time": expiry_time,
            "expiry_days": EXPIRY_TIME,
            "connection_string": connection_string
        }

    except Exception as e:
        logger.error(f"❌ Ошибка продления VPN аккаунта: {e}")
        return None



# Изолированное использование
'''
from vpn_service import create_vpn_account, get_vpn_status

# Создать VPN для пользователя
result = await create_vpn_account(123456)
if result:
    print(f"VPN создан: {result['connection_string']}")

# Обновить VPN для пользователя
result = await renew_vpn_account(123456)
if result:
    print(f"VPN создан: {result['connection_string']}")

# Проверить статус
status = await get_vpn_status(123456)
if status:
    print(f"Осталось дней: {status['expiry_days']}")
'''
