import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path
import re

class DialogManager:
    def __init__(self):
        self.db_path = Path('mika_data.db')
        self._init_db()
        self.name_patterns = [
            r'меня зовут (\w+)',
            r'я (\w+)',
            r'моё имя (\w+)',
            r'мое имя (\w+)',
            r'можешь называть меня (\w+)',
            r'можешь звать меня (\w+)'
        ]
    
    def _init_db(self):
        """Инициализация базы данных."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Таблица для сообщений
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        human_message TEXT,
                        ai_message TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица для пользовательских данных
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
        except Exception as e:
            logging.error(f"Ошибка при инициализации БД: {str(e)}")
    
    def add_interaction(self, human_message: str, ai_message: str):
        """Добавляет взаимодействие в базу данных."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO messages (human_message, ai_message) VALUES (?, ?)',
                    (human_message, ai_message)
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Ошибка при сохранении взаимодействия: {str(e)}")
    
    def get_recent_messages(self, limit: int = 5) -> List[Dict[str, str]]:
        """Получает последние сообщения из базы данных."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT human_message, ai_message FROM messages ORDER BY timestamp DESC LIMIT ?',
                    (limit,)
                )
                messages = []
                for human_msg, ai_msg in cursor.fetchall():
                    messages.extend([
                        {'role': 'user', 'content': human_msg},
                        {'role': 'assistant', 'content': ai_msg}
                    ])
                return messages[::-1]  # Возвращаем в хронологическом порядке
        except Exception as e:
            logging.error(f"Ошибка при получении сообщений: {str(e)}")
            return []
    
    def clear_old_messages(self, days: int = 7):
        """Удаляет старые сообщения из базы данных."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'DELETE FROM messages WHERE timestamp < datetime("now", ?)',
                    (f'-{days} days',)
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Ошибка при очистке старых сообщений: {str(e)}")
    
    def update_user_preferences(self, preferences: Dict[str, Any]):
        """Обновляет пользовательские настройки."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for key, value in preferences.items():
                    cursor.execute(
                        '''INSERT OR REPLACE INTO user_preferences (key, value, timestamp)
                           VALUES (?, ?, CURRENT_TIMESTAMP)''',
                        (key, json.dumps(value))
                    )
                conn.commit()
        except Exception as e:
            logging.error(f"Ошибка при обновлении настроек: {str(e)}")
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """Получает пользовательские настройки."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT key, value FROM user_preferences')
                return {key: json.loads(value) for key, value in cursor.fetchall()}
        except Exception as e:
            logging.error(f"Ошибка при получении настроек: {str(e)}")
            return {}
    
    def process_message(self, message: str) -> Dict[str, Any]:
        """Обрабатывает сообщение и возвращает информацию о нём."""
        result = {
            'requires_name_confirmation': False,
            'name': None,
            'requires_wiki': False,
            'wiki_info': None,
            'sentiment': {'polarity': 0, 'subjectivity': 0},
            'keywords': []
        }
        
        # Проверяем, спрашивает ли пользователь имя Мики
        if re.search(r'как\s+тебя\s+зовут', message.lower()):
            result['is_mika_name_question'] = True
            return result
        
        # Проверяем, представляется ли пользователь
        for pattern in self.name_patterns:
            match = re.search(pattern, message.lower())
            if match:
                name = match.group(1)
                # Проверяем длину имени и наличие недопустимых символов
                if 2 <= len(name) <= 20 and re.match(r'^[а-яА-ЯёЁa-zA-Z]+$', name):
                    result['requires_name_confirmation'] = True
                    result['name'] = name.capitalize()
                break
        
        # Проверяем, нужна ли информация из Wikipedia
        wiki_triggers = {'что такое', 'кто такой', 'расскажи о', 'расскажи про'}
        message_lower = message.lower()
        for trigger in wiki_triggers:
            if trigger in message_lower:
                # Извлекаем тему после триггера
                topic = message_lower.split(trigger)[-1].strip()
                if topic:
                    result['requires_wiki'] = True
                    # Здесь можно добавить получение информации из Wikipedia
                break
        
        return result 