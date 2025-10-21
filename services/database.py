import asyncpg
import logging
from config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

logger = logging.getLogger(__name__)


# 🔧 БАЗОВЫЕ ФУНКЦИИ ПОДКЛЮЧЕНИЯ
async def get_connection():
    """УНИВЕРСАЛЬНОЕ подключение к БД для любого проекта"""
    return await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME
    )


async def init_database():
    """УНИВЕРСАЛЬНАЯ инициализация БД для любого проекта"""
    try:
        conn = await get_connection()

        # УНИВЕРСАЛЬНАЯ таблица пользователей для любого сервиса
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                username VARCHAR(100),           -- опционально
                display_name VARCHAR(100),       -- НОВОЕ: имя из профиля Telegram
                email VARCHAR(255),              -- опционально
                phone_number VARCHAR(20),        -- опционально  
                first_name VARCHAR(100),         -- опционально
                last_name VARCHAR(100),          -- опционально
                patronymic VARCHAR(100),         -- опционально
                balance INTEGER DEFAULT 0,       -- универсальные баллы
                trial_used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- УНИВЕРСАЛЬНЫЕ дополнительные поля для любого сервиса
                metadata JSONB DEFAULT '{}'      -- НОВОЕ: любые дополнительные данные
            )
        ''')

        await conn.close()
        logger.info("✅ Универсальная база данных инициализирована")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        return False


# 👤 ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ
async def save_user(telegram_id: int, username: str = None, display_name: str = None, **fields):
    """
    УНИВЕРСАЛЬНОЕ сохранение пользователя для любого проекта
    """
    try:
        conn = await get_connection()

        # Базовые поля + любые дополнительные
        all_fields = {
            'username': username,
            'display_name': display_name,
            'email': fields.get('email'),
            'phone_number': fields.get('phone_number'),
            'first_name': fields.get('first_name'),
            'last_name': fields.get('last_name'),
            'patronymic': fields.get('patronymic'),
            'trial_used': fields.get('trial_used'),  # ← ДОБАВИТЬ ЭТО
            'metadata': fields.get('metadata')
        }

        # Фильтруем только переданные поля (кроме None, но trial_used может быть False)
        provided_fields = {}
        for k, v in all_fields.items():
            if v is not None or k == 'trial_used':  # trial_used может быть False
                provided_fields[k] = v

        if not provided_fields:
            # Минимальное сохранение - только telegram_id
            await conn.execute(
                'INSERT INTO users (telegram_id) VALUES ($1) ON CONFLICT (telegram_id) DO NOTHING',
                telegram_id
            )
        else:
            # Полное сохранение с полями
            insert_fields = ['telegram_id'] + list(provided_fields.keys())
            insert_placeholders = ['$1'] + [f'${i + 2}' for i in range(len(provided_fields))]

            update_parts = [f"{field} = EXCLUDED.{field}" for field in provided_fields.keys()]
            update_parts.append("updated_at = CURRENT_TIMESTAMP")

            values = [telegram_id] + list(provided_fields.values())

            query = f'''
                INSERT INTO users ({", ".join(insert_fields)}) 
                VALUES ({", ".join(insert_placeholders)})
                ON CONFLICT (telegram_id) 
                DO UPDATE SET {", ".join(update_parts)}
            '''

            await conn.execute(query, *values)

        await conn.close()
        logger.info(f"✅ Универсальный пользователь {telegram_id} сохранен")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка сохранения пользователя: {e}")
        return False


async def get_user(telegram_id: int):
    """УНИВЕРСАЛЬНОЕ получение пользователя"""
    try:
        conn = await get_connection()
        user = await conn.fetchrow(
            'SELECT * FROM users WHERE telegram_id = $1',
            telegram_id
        )
        await conn.close()
        return user
    except Exception as e:
        logger.error(f"❌ Ошибка получения пользователя: {e}")
        return None


async def user_exists(telegram_id: int):
    """ТОЧКА ВХОДА - проверить существование пользователя"""
    user = await get_user(telegram_id)
    return user is not None


async def update_user_balance(telegram_id: int, amount: int):
    """УНИВЕРСАЛЬНОЕ обновление баланса (баллов)"""
    try:
        conn = await get_connection()
        await conn.execute(
            'UPDATE users SET balance = balance + $1, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = $2',
            amount, telegram_id
        )
        await conn.close()
        logger.info(f"✅ Баланс пользователя {telegram_id} обновлен на {amount}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка обновления баланса: {e}")
        return False


async def get_trial_status(telegram_id: int) -> bool:
    """Проверяет, использовал ли пользователь trial"""
    try:
        conn = await get_connection()
        trial_used = await conn.fetchval(
            'SELECT trial_used FROM users WHERE telegram_id = $1',
            telegram_id
        )
        await conn.close()
        return trial_used if trial_used is not None else False
    except Exception as e:
        logger.error(f"❌ Ошибка проверки trial статуса: {e}")
        return False

async def mark_trial_used(telegram_id: int):
    """Отмечает что пользователь использовал trial"""
    try:
        conn = await get_connection()
        await conn.execute(
            'UPDATE users SET trial_used = TRUE, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = $1',
            telegram_id
        )
        await conn.close()
        logger.info(f"✅ Trial отмечен как использованный для пользователя {telegram_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка отметки trial: {e}")
        return False

async def update_user_metadata(telegram_id: int, key: str, value):
    """
    УНИВЕРСАЛЬНОЕ обновление метаданных пользователя
    Используется для хранения любых дополнительных данных
    """
    try:
        conn = await get_connection()
        await conn.execute(
            'UPDATE users SET metadata = jsonb_set(COALESCE(metadata, \'{}\'), $1, $2), updated_at = CURRENT_TIMESTAMP WHERE telegram_id = $3',
            f'{{{key}}}', f'"{value}"', telegram_id
        )
        await conn.close()
        logger.info(f"✅ Метаданные пользователя {telegram_id} обновлены: {key} = {value}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка обновления метаданных: {e}")
        return False


async def get_user_balance(telegram_id: int):
    """ТОЧКА ВХОДА - получить баланс пользователя"""
    try:
        conn = await get_connection()
        balance = await conn.fetchval(
            'SELECT balance FROM users WHERE telegram_id = $1',
            telegram_id
        )
        await conn.close()
        return balance or 0
    except Exception as e:
        logger.error(f"❌ Ошибка получения баланса: {e}")
        return 0


# 📊 ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ
async def get_all_users():
    """ТОЧКА ВХОДА - получить всех пользователей"""
    try:
        conn = await get_connection()
        users = await conn.fetch('SELECT * FROM users')
        await conn.close()
        return users
    except Exception as e:
        logger.error(f"❌ Ошибка получения всех пользователей: {e}")
        return []


async def get_users_count():
    """ТОЧКА ВХОДА - получить количество пользователей"""
    try:
        conn = await get_connection()
        count = await conn.fetchval('SELECT COUNT(*) FROM users')
        await conn.close()
        return count
    except Exception as e:
        logger.error(f"❌ Ошибка получения количества пользователей: {e}")
        return 0



### КАК ИСПОЛЬЗОВАТЬ В ЛЮБОМ ПРОЕКТЕ ###
# Пример 1: VPN сервис
'''
await save_user(
    telegram_id=123456,
    username="vpn_user",
    email="user@mail.com",
    metadata={"vpn_active": True, "subscription_type": "premium"}
)
'''
# Пример 2: Интернет-магазин
'''
await save_user(
    telegram_id=789012, 
    display_name="Иван Иванов",
    phone_number="+79123456789",
    metadata={"loyalty_level": "gold", "orders_count": 5}
)
'''
# Пример 3: Фитнес клуб
'''
await save_user(
    telegram_id=345678,
    first_name="Анна",
    last_name="Петрова", 
    metadata={"club_member": True, "trainer": "Иван", "visits_this_month": 8}
)
'''