import logging
import requests
import uuid
import os
from typing import Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PaymentItem:
    """Универсальный товар/услуга для чека"""
    name: str
    price: float
    quantity: int = 1
    tax: str = "none"  # none, vat0, vat10, vat20


@dataclass
class PaymentConfig:
    """Универсальная конфигурация платежа"""
    amount: float
    currency: str = "RUB"
    description: str = ""
    success_url: str = ""
    fail_url: str = ""
    items: List[PaymentItem] = None
    metadata: Dict = None


class BasePaymentProvider:
    """Базовый класс для всех платежных провайдеров"""

    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled

    async def create_payment(self, config: PaymentConfig, user_data: Dict) -> Optional[Dict]:
        """Создание платежа - должен быть реализован в дочерних классах"""
        raise NotImplementedError

    async def check_payment(self, payment_id: str) -> bool:
        """Проверка статуса платежа - должен быть реализован в дочерних классах"""
        raise NotImplementedError


class YooMoneyProvider(BasePaymentProvider):
    """Универсальный провайдер ЮMoney"""

    def __init__(self, shop_id: str, secret_key: str):
        super().__init__("ЮMoney")
        self.shop_id = shop_id
        self.secret_key = secret_key
        self.base_url = "https://yoomoney.ru/api/v4"

    async def create_payment(self, config: PaymentConfig, user_data: Dict) -> Optional[Dict]:
        try:
            headers = {
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "amount": {
                    "value": f"{config.amount:.2f}",
                    "currency": config.currency
                },
                "capture": True,
                "description": config.description,
                "confirmation": {
                    "type": "redirect",
                    "return_url": config.success_url
                },
                "metadata": config.metadata or {}
            }

            # Добавляем пользовательские данные в metadata
            payload["metadata"].update(user_data)

            response = requests.post(
                f"{self.base_url}/payments",
                json=payload,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'payment_id': data['id'],
                    'confirmation_url': data['confirmation']['confirmation_url'],
                    'status': data['status'],
                    'provider': 'yoomoney'
                }
            else:
                logger.error(f"❌ ЮMoney API error: {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ ЮMoney payment error: {e}")
            return None

    async def check_payment(self, payment_id: str) -> bool:
        try:
            headers = {
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json"
            }

            response = requests.get(
                f"{self.base_url}/payments/{payment_id}",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return data['status'] == 'succeeded'
            return False

        except Exception as e:
            logger.error(f"❌ ЮMoney check error: {e}")
            return False


class SBPProvider(BasePaymentProvider):
    """Универсальный провайдер СБП"""

    def __init__(self, merchant_id: str, secret_key: str):
        super().__init__("СБП")
        self.merchant_id = merchant_id
        self.secret_key = secret_key
        self.base_url = "https://securepay.tinkoff.ru/v2"

    async def create_payment(self, config: PaymentConfig, user_data: Dict) -> Optional[Dict]:
        try:
            order_id = str(uuid.uuid4())

            # Формируем items для чека
            receipt_items = []
            if config.items:
                for item in config.items:
                    receipt_items.append({
                        "Name": item.name,
                        "Price": int(item.price * 100),  # в копейках
                        "Quantity": item.quantity,
                        "Amount": int(item.price * item.quantity * 100),
                        "Tax": item.tax
                    })
            else:
                # Дефолтный item если не указаны
                receipt_items.append({
                    "Name": config.description or "Услуга",
                    "Price": int(config.amount * 100),
                    "Quantity": 1,
                    "Amount": int(config.amount * 100),
                    "Tax": "none"
                })

            payload = {
                "TerminalKey": self.merchant_id,
                "Amount": int(config.amount * 100),
                "OrderId": order_id,
                "Description": config.description,
                "SuccessURL": config.success_url,
                "FailURL": config.fail_url,
                "Data": user_data,
                "Receipt": {
                    "Email": user_data.get("email", "user@example.com"),
                    "Phone": user_data.get("phone", "+79999999999"),
                    "Taxation": "osn",
                    "Items": receipt_items
                }
            }

            # Подпись запроса
            import hashlib
            sign_data = "".join([
                str(payload["Amount"]),
                payload["OrderId"],
                payload["Description"],
                payload["SuccessURL"],
                payload["FailURL"],
                self.secret_key
            ])
            payload["Token"] = hashlib.sha256(sign_data.encode()).hexdigest()

            response = requests.post(
                f"{self.base_url}/Init",
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data['Success']:
                    return {
                        'payment_id': data['PaymentId'],
                        'confirmation_url': data['PaymentURL'],
                        'status': 'pending',
                        'provider': 'sbp'
                    }
            return None

        except Exception as e:
            logger.error(f"❌ СБП payment error: {e}")
            return None

    async def check_payment(self, payment_id: str) -> bool:
        try:
            payload = {
                "TerminalKey": self.merchant_id,
                "PaymentId": payment_id
            }

            import hashlib
            sign_data = payload["TerminalKey"] + payload["PaymentId"] + self.secret_key
            payload["Token"] = hashlib.sha256(sign_data.encode()).hexdigest()

            response = requests.post(
                f"{self.base_url}/GetState",
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return data['Success'] and data['Status'] == 'CONFIRMED'
            return False

        except Exception as e:
            logger.error(f"❌ СБП check error: {e}")
            return False


class BankCardProvider(BasePaymentProvider):
    """Универсальный провайдер банковских карт"""

    def __init__(self, shop_id: str, secret_key: str):
        super().__init__("Банковская карта")
        self.shop_id = shop_id
        self.secret_key = secret_key
        self.base_url = "https://api.yookassa.ru/v3"

    async def create_payment(self, config: PaymentConfig, user_data: Dict) -> Optional[Dict]:
        try:
            auth = (self.shop_id, self.secret_key)
            headers = {
                "Idempotence-Key": str(uuid.uuid4()),
                "Content-Type": "application/json"
            }

            payload = {
                "amount": {
                    "value": f"{config.amount:.2f}",
                    "currency": config.currency
                },
                "payment_method_data": {
                    "type": "bank_card"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": config.success_url
                },
                "capture": True,
                "description": config.description,
                "metadata": config.metadata or {}
            }

            # Добавляем пользовательские данные
            payload["metadata"].update(user_data)

            response = requests.post(
                f"{self.base_url}/payments",
                json=payload,
                headers=headers,
                auth=auth,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'payment_id': data['id'],
                    'confirmation_url': data['confirmation']['confirmation_url'],
                    'status': data['status'],
                    'provider': 'card'
                }
            return None

        except Exception as e:
            logger.error(f"❌ Bank card payment error: {e}")
            return None

    async def check_payment(self, payment_id: str) -> bool:
        try:
            auth = (self.shop_id, self.secret_key)

            response = requests.get(
                f"{self.base_url}/payments/{payment_id}",
                auth=auth,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return data['status'] == 'succeeded'
            return False

        except Exception as e:
            logger.error(f"❌ Bank card check error: {e}")
            return False


class UniversalPaymentManager:
    """Универсальный менеджер платежей для любого проекта"""

    def __init__(self):
        self.enabled = os.getenv('PAYMENT_ENABLED', 'False').lower() == 'true'

        # Динамическая инициализация провайдеров из переменных окружения
        self.providers = {}

        # ЮMoney
        yoomoney_shop_id = os.getenv('YOOMONEY_SHOP_ID')
        yoomoney_secret = os.getenv('YOOMONEY_SECRET_KEY')
        if yoomoney_shop_id and yoomoney_secret:
            self.providers['yoomoney'] = YooMoneyProvider(yoomoney_shop_id, yoomoney_secret)

        # СБП
        sbp_merchant_id = os.getenv('SBP_MERCHANT_ID')
        sbp_secret = os.getenv('SBP_SECRET_KEY')
        if sbp_merchant_id and sbp_secret:
            self.providers['sbp'] = SBPProvider(sbp_merchant_id, sbp_secret)

        # Банковские карты
        card_shop_id = os.getenv('CARD_SHOP_ID')
        card_secret = os.getenv('CARD_SECRET_KEY')
        if card_shop_id and card_secret:
            self.providers['card'] = BankCardProvider(card_shop_id, card_secret)

    def is_enabled(self) -> bool:
        """Проверка включена ли платежная система"""
        return self.enabled and len(self.providers) > 0

    def get_available_providers(self) -> List[str]:
        """Получить список доступных провайдеров"""
        return list(self.providers.keys())

    def get_provider_name(self, provider: str) -> str:
        """Получить человеческое название провайдера"""
        if provider in self.providers:
            return self.providers[provider].name
        return provider

    async def create_payment(
            self,
            provider: str,
            config: PaymentConfig,
            user_data: Dict
    ) -> Optional[Dict]:
        """Создание универсального платежа"""
        if not self.is_enabled():
            logger.warning("⚠️ Payment system is disabled")
            return None

        if provider not in self.providers:
            logger.warning(f"⚠️ Payment provider {provider} not available")
            return None

        result = await self.providers[provider].create_payment(config, user_data)

        if result:
            result['provider_name'] = self.get_provider_name(provider)
            result['amount'] = config.amount
            result['currency'] = config.currency
            logger.info(f"✅ Payment created: {result['payment_id']}")

        return result

    async def check_payment(self, payment_id: str, provider: str) -> bool:
        """Проверка статуса платежа"""
        if not self.is_enabled() or provider not in self.providers:
            return False

        return await self.providers[provider].check_payment(payment_id)


# Глобальный экземпляр для удобства
payment_manager = UniversalPaymentManager()


# 📋 УНИВЕРСАЛЬНЫЕ ФУНКЦИИ ДЛЯ ЛЮБОГО ПРОЕКТА
async def create_payment(provider: str, config: PaymentConfig, user_data: Dict) -> Optional[Dict]:
    """
    Универсальная функция создания платежа для любого проекта

    Args:
        provider: 'yoomoney', 'sbp', 'card'
        config: PaymentConfig с настройками платежа
        user_data: данные пользователя для метаданных

    Returns:
        Dict с данными платежа или None при ошибке
    """
    return await payment_manager.create_payment(provider, config, user_data)


async def check_payment(payment_id: str, provider: str) -> bool:
    """Универсальная проверка статуса платежа"""
    return await payment_manager.check_payment(payment_id, provider)


def is_payment_enabled() -> bool:
    """Проверка доступности платежной системы"""
    return payment_manager.is_enabled()


def get_available_providers() -> List[str]:
    """Получить список доступных провайдеров"""
    return payment_manager.get_available_providers()


def create_payment_config(
        amount: float,
        description: str = "",
        success_url: str = "",
        fail_url: str = "",
        items: List[PaymentItem] = None,
        metadata: Dict = None,
        currency: str = "RUB"
) -> PaymentConfig:
    """Вспомогательная функция для создания конфигурации платежа"""
    return PaymentConfig(
        amount=amount,
        currency=currency,
        description=description,
        success_url=success_url,
        fail_url=fail_url,
        items=items,
        metadata=metadata
    )


def create_payment_item(name: str, price: float, quantity: int = 1, tax: str = "none") -> PaymentItem:
    """Вспомогательная функция для создания товара/услуги"""
    return PaymentItem(name=name, price=price, quantity=quantity, tax=tax)



### АННОТАЦИЯ ###
# Переменные окружения
'''
# Активация платежей
PAYMENT_ENABLED=true

# Ключи провайдеров (добавляются по необходимости)
YOOMONEY_SHOP_ID=your_shop_id
YOOMONEY_SECRET_KEY=your_secret_key

SBP_MERCHANT_ID=your_merchant_id
SBP_SECRET_KEY=your_secret_key

CARD_SHOP_ID=your_shop_id  
CARD_SECRET_KEY=your_secret_key
'''

# Пример 1: VPN сервис
'''
from payment import create_payment, create_payment_config, create_payment_item, is_payment_enabled

# Проверяем доступность платежей
if is_payment_enabled():
    # Создаем конфиг для VPN
    config = create_payment_config(
        amount=299.0,
        description="VPN подписка на 30 дней",
        success_url="https://t.me/your_bot?start=success",
        fail_url="https://t.me/your_bot?start=fail",
        items=[
            create_payment_item("VPN Premium", 299.0, 1)
        ],
        metadata={"product_type": "vpn", "duration_days": 30}
    )

    # Данные пользователя
    user_data = {
        "telegram_id": 123456,
        "email": "user@example.com",
        "phone": "+79123456789"
    }

    # Создаем платеж
    payment = await create_payment('yoomoney', config, user_data)
'''

# Пример 2: Фитнес клуб
'''
from payment import create_payment, create_payment_config, create_payment_item

# Конфиг для фитнеса
config = create_payment_config(
    amount=1500.0,
    description="Абонемент в фитнес клуб",
    success_url="https://t.me/fitness_bot?start=success",
    items=[
        create_payment_item("Месячный абонемент", 1500.0, 1),
        create_payment_item("Персональная тренировка", 500.0, 2)
    ],
    metadata={"product_type": "fitness", "club_id": "Moscow_Center"}
)

user_data = {
    "telegram_id": 789012,
    "client_name": "Иван Иванов"
}

payment = await create_payment('sbp', config, user_data)
'''

# Пример 3: Интернет-магазин
'''
from payment import create_payment, create_payment_config, create_payment_item

# Конфиг для магазина
config = create_payment_config(
    amount=4500.0,
    description="Заказ №12345",
    items=[
        create_payment_item("Ноутбук", 4000.0, 1),
        create_payment_item("Доставка", 500.0, 1)
    ],
    metadata={"order_id": "12345", "delivery": "courier"}
)

user_data = {
    "telegram_id": 555666,
    "email": "customer@mail.com",
    "address": "Москва, ул. Примерная, 1"
}

payment = await create_payment('card', config, user_data)
'''