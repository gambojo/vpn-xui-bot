# services/registration_service.py
import logging
from aiogram.fsm.state import State, StatesGroup

logger = logging.getLogger(__name__)


class RegistrationStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_phone = State()
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_patronymic = State()


class RegistrationManager:
    def __init__(self):
        self.fields_config = {}

    def configure_fields(self, email=False, phone=False, first_name=False,
                         last_name=False, patronymic=False):
        self.fields_config = {
            'email': email,
            'phone': phone,
            'first_name': first_name,
            'last_name': last_name,
            'patronymic': patronymic
        }

    def get_next_field(self, current_state=None):
        """Получить следующее поле для запроса"""
        field_order = ['email', 'phone', 'first_name', 'last_name', 'patronymic']

        if not current_state:
            # Первое поле
            for field in field_order:
                if self.fields_config.get(field):
                    state_map = {
                        'email': RegistrationStates.waiting_for_email,
                        'phone': RegistrationStates.waiting_for_phone,
                        'first_name': RegistrationStates.waiting_for_first_name,
                        'last_name': RegistrationStates.waiting_for_last_name,
                        'patronymic': RegistrationStates.waiting_for_patronymic
                    }
                    return field, state_map[field]
            return None

        # Следующее поле после текущего
        current_index = None
        for i, field in enumerate(field_order):
            state_map = {
                'email': RegistrationStates.waiting_for_email,
                'phone': RegistrationStates.waiting_for_phone,
                'first_name': RegistrationStates.waiting_for_first_name,
                'last_name': RegistrationStates.waiting_for_last_name,
                'patronymic': RegistrationStates.waiting_for_patronymic
            }
            if state_map[field] == current_state:
                current_index = i
                break

        if current_index is not None:
            for field in field_order[current_index + 1:]:
                if self.fields_config.get(field):
                    state_map = {
                        'email': RegistrationStates.waiting_for_email,
                        'phone': RegistrationStates.waiting_for_phone,
                        'first_name': RegistrationStates.waiting_for_first_name,
                        'last_name': RegistrationStates.waiting_for_last_name,
                        'patronymic': RegistrationStates.waiting_for_patronymic
                    }
                    return field, state_map[field]

        return None

    def get_question(self, field_name):
        questions = {
            'email': '📧 Введите ваш email:',
            'phone': '📞 Введите ваш номер телефона:',
            'first_name': '👤 Введите ваше имя:',
            'last_name': '👤 Введите вашу фамилию:',
            'patronymic': '👤 Введите ваше отчество:'
        }
        return questions.get(field_name, 'Введите данные:')

    def validate_field(self, field_name, value):
        """Простая валидация полей"""
        if not value or len(value.strip()) == 0:
            return False

        if field_name == 'email':
            return '@' in value and '.' in value
        elif field_name == 'phone':
            return any(c.isdigit() for c in value) and len(value) >= 5

        return len(value.strip()) >= 2


# Глобальный экземпляр
registration_manager = RegistrationManager()