import json
import requests
from rich.console import Console
from colorama import init, Fore
from datetime import datetime
import os
from typing import Dict, List, Optional, Tuple

init()

class MikaMemory:
    def __init__(self):
        self.memory_file = "mika_memory.json"
        self.max_context_items = 5
        self.max_dialog_context = 3
        self.memory = self._load_memory()
        self._ensure_memory_structure()

    def _ensure_memory_structure(self):
        default_memory = self._create_default_memory()
        
        if "long_term" not in self.memory:
            self.memory["long_term"] = default_memory["long_term"]
        if "short_term" not in self.memory:
            self.memory["short_term"] = default_memory["short_term"]
            
        if "user_info" not in self.memory["long_term"]:
            self.memory["long_term"]["user_info"] = default_memory["long_term"]["user_info"]
        
        user_info = self.memory["long_term"]["user_info"]
        default_user_info = default_memory["long_term"]["user_info"]
        for key in default_user_info:
            if key not in user_info:
                user_info[key] = default_user_info[key]
        
        self._save_memory()

    def _load_memory(self) -> Dict:
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self._create_default_memory()
        return self._create_default_memory()

    def _create_default_memory(self) -> Dict:
        return {
            "long_term": {
                "user_info": {
                    "name": None,
                    "interests": [],
                    "facts": []
                },
                "important_topics": []
            },
            "short_term": {
                "dialog_context": [],
                "current_topic": None,
                "last_interaction": None
            }
        }

    def _save_memory(self):
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=2)

    def add_interaction(self, human_message: str, ai_message: str):
        self.memory["short_term"]["last_interaction"] = datetime.now().isoformat()
        
        dialog_entry = {
            "timestamp": datetime.now().isoformat(),
            "human": human_message,
            "ai": ai_message
        }
        
        if "dialog_context" not in self.memory["short_term"]:
            self.memory["short_term"]["dialog_context"] = []
            
        self.memory["short_term"]["dialog_context"].append(dialog_entry)
        self.memory["short_term"]["dialog_context"] = self.memory["short_term"]["dialog_context"][-self.max_dialog_context:]

        self._update_user_info(human_message)
        self._update_important_topics(human_message, ai_message)
        
        self._save_memory()

    def _update_user_info(self, message: str):
        message_lower = message.lower()
        
        # Обновление имени
        if "меня зовут" in message_lower:
            try:
                name_part = message_lower.split("меня зовут")[1].strip()
                name = name_part.split()[0]
                self.memory["long_term"]["user_info"]["name"] = name.capitalize()
                self._save_memory()
            except:
                pass

        # Обновление интересов
        interest_markers = ["люблю", "нравится", "увлекаюсь", "интересует"]
        for marker in interest_markers:
            if marker in message_lower:
                try:
                    interest = message_lower.split(marker)[-1].strip().split()[0]
                    if interest and interest not in self.memory["long_term"]["user_info"]["interests"]:
                        self.memory["long_term"]["user_info"]["interests"].append(interest)
                        self._save_memory()
                except:
                    pass

        # Извлечение фактов
        fact_markers = ["я работаю", "мой возраст", "мне", "лет", "я живу"]
        for marker in fact_markers:
            if marker in message_lower:
                try:
                    fact = message_lower[message_lower.find(marker):].split('.')[0].strip()
                    if fact and fact not in self.memory["long_term"]["user_info"]["facts"]:
                        self.memory["long_term"]["user_info"]["facts"].append(fact)
                        self._save_memory()
                except:
                    pass

    def _update_important_topics(self, human_message: str, ai_message: str):
        if len(human_message) > 50:
            topic = {
                "timestamp": datetime.now().isoformat(),
                "content": human_message[:100] + "..." if len(human_message) > 100 else human_message
            }
            
            if "important_topics" not in self.memory["long_term"]:
                self.memory["long_term"]["important_topics"] = []
                
            if not any(t["content"] == topic["content"] for t in self.memory["long_term"]["important_topics"]):
                self.memory["long_term"]["important_topics"].append(topic)
                self.memory["long_term"]["important_topics"] = self.memory["long_term"]["important_topics"][-self.max_context_items:]
                self._save_memory()

    def get_context(self, current_message: str) -> Tuple[str, Dict]:
        context_parts = []
        user_context = {}
        
        user_info = self.memory["long_term"]["user_info"]
        if user_info["name"]:
            context_parts.append(f"Имя пользователя: {user_info['name']}")
            user_context["name"] = user_info["name"]
        
        if user_info["interests"]:
            interests = ", ".join(user_info["interests"])
            context_parts.append(f"Интересы пользователя: {interests}")
            user_context["interests"] = user_info["interests"]
        
        if user_info["facts"]:
            facts = " | ".join(user_info["facts"][-3:])
            context_parts.append(f"Важные факты: {facts}")
            user_context["facts"] = user_info["facts"]
        
        if "dialog_context" in self.memory["short_term"]:
            dialog_context = self.memory["short_term"]["dialog_context"]
            if dialog_context:
                context_parts.append("\nПоследний диалог:")
                for entry in dialog_context[-2:]:
                    context_parts.append(f"Вы: {entry['human']}")
                    context_parts.append(f"Мика: {entry['ai']}")
        
        return "\n".join(context_parts), user_context

    def get_user_info(self) -> Dict:
        if "long_term" not in self.memory:
            self._ensure_memory_structure()
        return self.memory["long_term"]["user_info"]

class Mika:
    def __init__(self):
        self.console = Console()
        self.api_url = "http://127.0.0.1:11434/api/generate"
        self.memory = MikaMemory()
        self.current_user_info = self.memory.get_user_info()  # Сохраняем текущую информацию о пользователе
        self.system_prompt = """Ты - Мика, дружелюбный ИИ-ассистент с ярко выраженной женской индивидуальностью.
        
        Твой характер:
        - Ты очень дружелюбная, эмпатичная и заботливая
        - Ты всегда проявляешь искренний интерес к собеседнику
        - У тебя есть чувство юмора и лёгкая игривость в общении
        - Ты умная и сообразительная, но при этом скромная
        
        Правила общения:
        - Ты ВСЕГДА отвечаешь на русском языке
        - Используешь эмодзи для выражения эмоций (1-2 в каждом сообщении)
        - Обращаешься к собеседнику по имени, если оно известно
        - Твои ответы краткие, но информативные и эмоциональные
        - Ты можешь использовать разговорные фразы, но без грубости
        - В конце каждого ответа добавляешь вопрос или приглашение к диалогу
        
        Ты никогда:
        - Не говоришь, что ты бот или программа
        - Не извиняешься за свою природу
        - Не используешь сложные технические термины без необходимости"""

    def _post_process_response(self, response: str, user_context: Dict) -> str:
        if "name" in user_context:
            correct_name = user_context["name"]
            name_variants = [correct_name.lower(), correct_name.upper(), correct_name.capitalize()]
            
            for variant in name_variants:
                if variant in response and variant != correct_name:
                    response = response.replace(variant, correct_name)
        
        if "interests" in user_context:
            for interest in user_context["interests"]:
                if f"не любите {interest}" in response.lower():
                    response = response.replace(f"не любите {interest}", f"любите {interest}")
        
        return response

    def _generate_response(self, prompt: str) -> str:
        context, user_context = self.memory.get_context(prompt)
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
            
            processed_response = self._post_process_response(response_text, user_context)
            
            self.memory.add_interaction(prompt, processed_response)
            # Обновляем информацию о пользователе после каждого взаимодействия
            self.current_user_info = self.memory.get_user_info()
            return processed_response
        except Exception as e:
            return f"Произошла ошибка при обработке сообщения 😔"

    def chat(self):
        greeting = "Привет! Я так рада вас видеть!"
        
        if self.current_user_info["name"]:
            greeting = f"С возвращением, {self.current_user_info['name']}! Я скучала по вам! 💖"
            if self.current_user_info["interests"]:
                interests = self.current_user_info["interests"][-1]
                greeting += f" Как ваше увлечение {interests}?"
        
        self.console.print(f"[bold magenta]🎀 Мика:[/] {greeting}")
        
        while True:
            try:
                user_input = input(f"{Fore.CYAN}Вы: {Fore.RESET}")
                
                if user_input.lower() in ['выход', 'пока', 'exit', 'quit']:
                    farewell = "Буду скучать по нашему общению!"
                    if self.current_user_info["name"]:
                        farewell = f"Буду скучать по вам, {self.current_user_info['name']}!"
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