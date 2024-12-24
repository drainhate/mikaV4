import sqlite3
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Any

class MikaDB:
    def __init__(self, db_path: str = "mika.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Инициализация базы данных."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица для пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    last_interaction TIMESTAMP
                )
            """)
            
            # Таблица для интересов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interests (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    interest TEXT,
                    added_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Таблица для фактов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    fact TEXT,
                    added_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Таблица для диалогов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dialogs (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    human_message TEXT,
                    ai_message TEXT,
                    timestamp TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            conn.commit()

    def get_or_create_user(self) -> int:
        """Получает или создает анонимного пользователя."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE name IS NULL")
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            cursor.execute(
                "INSERT INTO users (last_interaction) VALUES (?)",
                (datetime.now().isoformat(),)
            )
            return cursor.lastrowid

    def update_user_name(self, user_id: int, name: str):
        """Обновляет имя пользователя."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET name = ?, last_interaction = ? WHERE id = ?",
                (name, datetime.now().isoformat(), user_id)
            )

    def add_interest(self, user_id: int, interest: str):
        """Добавляет интерес пользователя."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO interests (user_id, interest, added_at) VALUES (?, ?, ?)",
                (user_id, interest.lower(), datetime.now().isoformat())
            )

    def add_fact(self, user_id: int, fact: str):
        """Добавляет факт о пользователе."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO facts (user_id, fact, added_at) VALUES (?, ?, ?)",
                (user_id, fact, datetime.now().isoformat())
            )

    def add_dialog(self, user_id: int, human_message: str, ai_message: str):
        """Добавляет диалог в историю."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO dialogs (user_id, human_message, ai_message, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, human_message, ai_message, datetime.now().isoformat())
            )

    def get_user_context(self, user_id: int, dialog_limit: int = 5) -> Dict[str, Any]:
        """Получает контекст пользователя."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Получаем имя пользователя
            cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,))
            name = cursor.fetchone()[0]
            
            # Получаем интересы
            cursor.execute(
                "SELECT interest FROM interests WHERE user_id = ? ORDER BY added_at DESC",
                (user_id,)
            )
            interests = [row[0] for row in cursor.fetchall()]
            
            # Получаем факты
            cursor.execute(
                "SELECT fact FROM facts WHERE user_id = ? ORDER BY added_at DESC",
                (user_id,)
            )
            facts = [row[0] for row in cursor.fetchall()]
            
            # Получаем последние диалоги
            cursor.execute(
                """
                SELECT human_message, ai_message 
                FROM dialogs 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
                """,
                (user_id, dialog_limit)
            )
            dialogs = [{"human": row[0], "ai": row[1]} for row in cursor.fetchall()]
            
            return {
                "name": name,
                "interests": interests,
                "facts": facts,
                "recent_dialogs": dialogs[::-1]  # Возвращаем в хронологическом порядке
            }

    def cleanup_old_data(self, days: int = 30):
        """Очищает старые данные."""
        threshold = datetime.now() - timedelta(days=days)
        threshold_str = threshold.isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Очищаем старые диалоги
            cursor.execute(
                "DELETE FROM dialogs WHERE timestamp < ?",
                (threshold_str,)
            )
            
            # Очищаем старые факты
            cursor.execute(
                "DELETE FROM facts WHERE added_at < ?",
                (threshold_str,)
            ) 