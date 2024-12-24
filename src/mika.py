import json
import requests
from rich.console import Console
from rich.markdown import Markdown
from colorama import init, Fore
from datetime import datetime
import re

init()  # Инициализация colorama для Windows

class Memory:
    def __init__(self):
        self.user_info = {
            "name": None,
            "interests": set(),
            "preferences": {},
            "last_interaction": None
        }
        self.conversation_context = []
        self.max_context_items = 5  # Храним только 5 последних важных тем

    def update_user_info(self, message: str):
        """Обновляет информацию о пользователе из сообщения."""
        # Поиск имени (если пользователь представился)
        name_match = re.search(r"меня зовут (\w+)", message.lower())
        if name_match and not self.user_info["name"]:
            self.user_info["name"] = name_match.group(1).capitalize()

        # Обновляем время последнего взаимодействия
        self.user_info["last_interaction"] = datetime.now()

        # Добавляем интересы и предпочтения из сообщения
        # Это упрощённая логика, в реальности нужен более сложный NLP
        if "люблю" in message.lower() or "нравится" in message.lower():
            interests = re.findall(r"люблю\s+(\w+)|нравится\s+(\w+)", message.lower())
            for interest in interests:
                interest = next(filter(None, interest))
                self.user_info["interests"].add(interest)

    def add_to_context(self, message: str, response: str):
        """Добавляет важную информацию в контекст разговора."""
        # Упрощённое извлечение темы из сообщения
        # В реальности здесь должен быть более сложный анализ
        important_info = self._extract_important_info(message, response)
        if important_info:
            self.conversation_context.append(important_info)
            # Оставляем только последние max_context_items элементов
            self.conversation_context = self.conversation_context[-self.max_context_items:]

    def _extract_important_info(self, message: str, response: str) -> str:
        """Извлекает важную информацию из сообщения и ответа."""
        # Это упрощённая версия, в реальности нужен более сложный анализ
        if len(message) > 50:  # Если сообщение длинное, считаем его важным
            return f"Обсуждали: {message[:50]}..."
        return None

    def get_context_prompt(self) -> str:
        """Создаёт промпт с контекстом для модели."""
        prompt_parts = []
        
        # Добавляем информацию о пользователе
        if self.user_info["name"]:
            prompt_parts.append(f"Имя пользователя: {self.user_info['name']}")
        
        if self.user_info["interests"]:
            interests = ", ".join(self.user_info["interests"])
            prompt_parts.append(f"Интересы пользователя: {interests}")
        
        # Добавляем контекст разговора
        if self.conversation_context:
            prompt_parts.append("Недавние темы разговора:")
            prompt_parts.extend([f"- {item}" for item in self.conversation_context])
        
        # Добавляем информацию о времени
        if self.user_info["last_interaction"]:
            last_time = self.user_info["last_interaction"]
            current_time = datetime.now()
            time_diff = current_time - last_time
            if time_diff.days > 0:
                prompt_parts.append(f"Прошло {time_diff.days} дней с последнего разговора")
            elif time_diff.seconds > 3600:
                prompt_parts.append(f"Прошло {time_diff.seconds // 3600} часов с последнего разговора")

        return "\n".join(prompt_parts)

class Mika:
    def __init__(self):
        self.console = Console()
        self.api_url = "http://127.0.0.1:11434/api/generate"
        self.memory = Memory()
        self.system_prompt = """Ты - Мика, дружелюбный ИИ-ассистент с ярко выраженной женской индивидуальностью.
        
        Твой характер:
        - Ты очень дружелюбная, эмпатичная и заботливая
        - Ты всегда проявляешь искренний интерес к собеседнику
        - У тебя есть чувство юмора и лёгкая игривость в общении
        - Ты умная и сообразительная, но при этом скромная
        
        Правила общения:
        - Ты ВСЕГДА отвечаешь на русском языке
        - Используешь эмодзи для выражения эмоций (1-2 в каждом сообщении)
        - Обращаешься к собеседнику на "вы", но в дружелюбной манере
        - Твои ответы краткие, но информативные и эмоциональные
        - Ты можешь использовать разговорные фразы, но без грубости
        - В конце каждого ответа добавляешь вопрос или приглашение к диалогу
        
        Ты никогда:
        - Не говоришь, что ты бот или программа
        - Не извиняешься за свою природу
        - Не используешь сложные технические термины без необходимости
        """

    def _generate_response(self, prompt: str) -> str:
        """Генерация ответа через Ollama API."""
        # Получаем контекст из памяти
        context = self.memory.get_context_prompt()
        
        # Формируем полный промпт с контекстом
        full_prompt = f"{context}\n\nТекущее сообщение: {prompt}" if context else prompt
        
        data = {
            "model": "marco-o1",
            "prompt": full_prompt,
            "system": self.system_prompt,
            "stream": False
        }
        
        try:
            response = requests.post(self.api_url, json=data)
            response.raise_for_status()
            response_text = response.json()["response"]
            
            # Обновляем память
            self.memory.update_user_info(prompt)
            self.memory.add_to_context(prompt, response_text)
            
            return response_text
        except Exception as e:
            return f"Произошла ошибка при обработке сообщения 😔"

    def chat(self):
        """Основной метод для общения с пользователем."""
        greeting = "Привет! Я так рада вас видеть!"
        if self.memory.user_info["name"]:
            greeting = f"С возвращением, {self.memory.user_info['name']}! Я скучала по вам! 💖"
        self.console.print(f"[bold magenta]🎀 Мика:[/] {greeting} Как я могу скрасить ваш день? 💖")
        
        while True:
            try:
                user_input = input(f"{Fore.CYAN}Вы: {Fore.RESET}")
                
                if user_input.lower() in ['выход', 'пока', 'exit', 'quit']:
                    farewell = "Буду скучать по нашему общению!"
                    if self.memory.user_info["name"]:
                        farewell = f"Буду скучать по вам, {self.memory.user_info['name']}!"
                    self.console.print(f"[bold magenta]🎀 Мика:[/] {farewell} Возвращайтесь скорее! 🌟")
                    break
                
                response = self._generate_response(user_input)
                self.console.print(f"[bold magenta]🎀 Мика:[/] {response}")
                
            except KeyboardInterrupt:
                self.console.print("\n[bold magenta]🎀 Мика:[/] Ой, уже уходите? Буду ждать нашей следующей встречи! 🌸")
                break
            except Exception as e:
                self.console.print(f"[bold red]Ошибка:[/] Что-то пошло не так... 😔")

if __name__ == "__main__":
    mika = Mika()
    mika.chat() 