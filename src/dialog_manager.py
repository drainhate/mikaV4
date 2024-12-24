import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import re
from collections import Counter

class DialogManager:
    def __init__(self):
        self.db_path = "dialogs.db"
        self._init_db()
        
    def _init_db(self):
        """Инициализация базы данных для хранения диалогов."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dialogs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    human_message TEXT NOT NULL,
                    ai_message TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            
            # Создаем запись для пользователя, если её нет
            cursor.execute("INSERT OR IGNORE INTO user_info (id) VALUES (1)")
            conn.commit()
    
    def _extract_name(self, text: str) -> Optional[str]:
        """Извлекает имя из текста."""
        # Паттерны для поиска имени
        patterns = [
            r"меня зовут (\w+)",
            r"моё имя (\w+)",
            r"мое имя (\w+)",
            r"я (\w+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                name = match.group(1)
                # Приводим имя к формату с заглавной буквы
                return name.capitalize()
        return None
    
    def update_user_name(self, name: str):
        """Обновляет имя пользователя."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE user_info SET name = ?, last_updated = CURRENT_TIMESTAMP WHERE id = 1",
                    (name,)
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Ошибка при обновлении имени пользователя: {str(e)}")
    
    def get_user_name(self) -> Optional[str]:
        """Возвращает имя пользователя."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM user_info WHERE id = 1")
                result = cursor.fetchone()
                return result[0] if result and result[0] else None
        except Exception as e:
            logging.error(f"Ошибка при получении имени пользователя: {str(e)}")
            return None
    
    def process_message(self, message: str) -> Dict[str, any]:
        """Обрабатывает сообщение и возвращает информацию о нём."""
        result = {
            "is_name_question": False,
            "contains_name": False,
            "name": None
        }
        
        # Проверяем, спрашивает ли пользователь своё имя
        name_questions = [
            "как меня зовут",
            "помнишь как меня зовут",
            "знаешь моё имя",
            "знаешь мое имя",
            "помнишь моё имя",
            "помнишь мое имя"
        ]
        
        if any(q in message.lower() for q in name_questions):
            result["is_name_question"] = True
            return result
        
        # Проверяем, представляется ли пользователь
        name = self._extract_name(message)
        if name:
            result["contains_name"] = True
            result["name"] = name
            self.update_user_name(name)
        
        return result
    
    def _tokenize(self, text: str) -> List[str]:
        """Простая токенизация текста."""
        # Приводим к нижнему регистру и удаляем пунктуацию
        text = re.sub(r'[^\w\s]', '', text.lower())
        # Разбиваем на слова
        return text.split()
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Вычисляет простое сходство между текстами на основе общих слов."""
        tokens1 = self._tokenize(text1)
        tokens2 = self._tokenize(text2)
        
        # Создаем множества слов
        set1 = set(tokens1)
        set2 = set(tokens2)
        
        # Вычисляем коэффициент Жаккара
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def add_interaction(self, human_message: str, ai_message: str):
        """Добавляет новое взаимодействие в базу данных."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO dialogs (human_message, ai_message) VALUES (?, ?)",
                    (human_message, ai_message)
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Ошибка при добавлении диалога: {str(e)}")
    
    def get_context(self, current_message: str, max_results: int = 3) -> List[str]:
        """Получает релевантный контекст на основе текущего сообщения."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Получаем все диалоги за последние 7 дней
                cursor.execute(
                    "SELECT human_message, ai_message FROM dialogs WHERE timestamp > ?",
                    (datetime.now() - timedelta(days=7),)
                )
                dialogs = cursor.fetchall()
                
                if not dialogs:
                    return []
                
                # Вычисляем сходство с каждым диалогом
                similarities = []
                for human_msg, ai_msg in dialogs:
                    similarity = self._calculate_similarity(current_message, human_msg)
                    similarities.append((similarity, human_msg, ai_msg))
                
                # Сортируем по сходству и берем top-k
                similarities.sort(reverse=True)
                context = []
                for _, human_msg, ai_msg in similarities[:max_results]:
                    context.extend([
                        f"Пользователь: {human_msg}",
                        f"Мика: {ai_msg}"
                    ])
                
                return context
        except Exception as e:
            logging.error(f"Ошибка при получении контекста: {str(e)}")
            return []
    
    def analyze_sentiment(self, text: str) -> str:
        """Простой анализ тональности на основе ключевых слов."""
        # Списки позитивных и негативных слов
        positive_words = {
            'хорошо', 'отлично', 'замечательно', 'прекрасно', 'великолепно',
            'радость', 'счастье', 'любовь', 'нравится', 'круто', 'супер',
            'класс', 'здорово', 'приятно', 'весело', 'спасибо', 'благодарю'
        }
        
        negative_words = {
            'пл��хо', 'ужасно', 'отвратительно', 'грустно', 'печально',
            'жаль', 'жалко', 'неприятно', 'раздражает', 'бесит', 'ненавижу',
            'злит', 'огорчает', 'разочарован', 'устал', 'надоело'
        }
        
        # Токенизируем текст
        tokens = self._tokenize(text)
        
        # Подсчитываем количество позитивных и негативных слов
        positive_count = sum(1 for word in tokens if word in positive_words)
        negative_count = sum(1 for word in tokens if word in negative_words)
        
        # Определяем тональность
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        return "neutral"
    
    def clear_old_messages(self, days: int = 30):
        """Удаляет старые сообщения из базы данных."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM dialogs WHERE timestamp < ?",
                    (datetime.now() - timedelta(days=days),)
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Ошибка при очистке старых сообщений: {str(e)}") 