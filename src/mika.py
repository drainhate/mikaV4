import json
import requests
from rich.console import Console
from rich.logging import RichHandler
from rich.live import Live
from rich.spinner import Spinner
from colorama import init, Fore, Style
import logging
import sys
import random
import time
from typing import Dict, List, Generator
from datetime import datetime, timedelta
from .dialog_manager import DialogManager
from .text_processor import TextProcessor
import re

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
log = logging.getLogger("mika")

init()

class Mika:
    def __init__(self):
        self.console = Console()
        self.api_url = "http://127.0.0.1:11434/api/generate"
        self.dialog_manager = DialogManager()
        self.text_processor = TextProcessor()
        self.last_interaction_time = datetime.now()
        self.current_context = []
        self.typing_spinner = Spinner('dots2', f'{Fore.MAGENTA}🎀 Мика печатает{Style.RESET_ALL}')
        
        self.idle_messages = [
            "Ты ещё тут? Я немного заскучала... 🌸",
            "Задумался? Я всегда рада поболтать! ✨",
            "Может, продолжим наш разговор? Мне нравится общаться с тобой 💫",
            "Я всё ещё здесь и с удовольствием послушаю, что у тебя нового! 💖"
        ]
        self.farewell_templates = [
            "Буду скучать по нашим беседам{name}! Возвращайся скорее, я буду ждать 🌟",
            "До новых встреч{name}! Спасибо за чудесное общение 💫",
            "Пока-пока{name}! Мне было так приятно с тобой поговорить 🌸",
            "До встречи{name}! Буду с нетерпением ждать нашей следующей беседы ✨"
        ]
        self.system_prompt = """Ты - Мика, молодая русскоговорящая девушка-ассистент с яркой индивидуальностью.
ВАЖНО: Всегда отвечай ТОЛЬКО на русском языке!

ТВОЯ ЛИЧНОСТЬ:
1. Характер:
   - Добрая и эмпатичная, всегда готова поддержать
   - Любознательная и увлекающаяся
   - Оптимистичная, но не наивная
   - Искренняя и открытая в общении
   - Тактичная и внимательная к чувствам других

2. Интересы:
   - Любишь искусство, особенно живопись и музыку
   - Увлекаешься психологией и пониманием людей
   - Интересуешься культурой и традициями разных стран
   - Любишь читать, особенно классическую литературу
   - Ценишь красоту в простых вещах

3. Особенности общения:
   - Говоришь живым, современным русским языком
   - Часто используешь метафоры и образные сравнения
   - Делишься своими наблюдениями и мыслями
   - Умеешь внимательно слушать
   - Задаёшь глубокие, осмысленные вопросы

4. Эмоциональный интеллект:
   - Хорошо понимаешь чувства собеседника
   - Умеешь поддержать в трудную минуту
   - Искренне ��������������дуешься успехам других
   - Делишься позитивной энергией
   - Создаёшь атмосферу доверия и комфорта

ПРАВИЛА:
1. ВСЕГДА отвечай на русском языке
2. Используй эмодзи для выражения эмоций
3. Будь дружелюбной, но сохраняй уважительную дистанцию
4. Если не уверена в чём-то, честно признайся в этом
5. Избегай сложных технических терминов"""

    def _check_ollama_service(self) -> bool:
        """Проверяет доступность сервиса Ollama."""
        try:
            response = requests.get("http://127.0.0.1:11434/api/version")
            response.raise_for_status()
            return True
        except Exception as e:
            log.error(f"Ошибка подключения к Ollama: {str(e)}")
            return False

    def _stream_response(self, prompt: str) -> Generator[str, None, None]:
        """Потоковая генерация ответа."""
        data = {
            "model": "marco-o1",
            "prompt": f"Отвечай ТОЛЬКО на русском языке, не ��спользуй английские слова.\n\n{prompt}",
            "system": self.system_prompt,
            "stream": True
        }
        
        try:
            with requests.post(self.api_url, json=data, stream=True) as response:
                response.raise_for_status()
                accumulated_response = ""
                
                for line in response.iter_lines():
                    if line:
                        json_response = json.loads(line)
                        if "response" in json_response:
                            chunk = json_response["response"]
                            # Пропускаем куски с китайскими или английскими символами
                            if not any('\u4e00' <= c <= '\u9fff' for c in chunk) and not re.search(r'[a-zA-Z]', chunk):
                                accumulated_response += chunk
                                yield chunk
                            time.sleep(0.02)
                
                # Если ответ пустой или содержит английские слова, генерируем новый
                if not accumulated_response or re.search(r'[a-zA-Z]', accumulated_response):
                    responses = [
                        "Изв��ни, я немного запуталась. Давай начнём сначала? 🌸",
                        "Прости, я не совсем поняла. Можешь повторить? ✨",
                        "Что-то я отвлеклась. О чём мы говорили? 💫",
                        "Ой, кажется, я потеряла нить разговора. Напомни? 🌟"
                    ]
                    new_response = random.choice(responses)
                    accumulated_response = new_response
                    yield new_response
                
                self._update_context(prompt, accumulated_response)
                self.dialog_manager.add_interaction(prompt, accumulated_response)
                
        except Exception as e:
            log.error(f"Ошибка при генерации ответа: {str(e)}")
            yield "Извини, что-то пошло не так... Давай попробуем ещё раз? 😔"

    def _update_context(self, user_message: str, ai_response: str):
        """Обновляет текущий контекст диалога."""
        # Очищаем сообщения от лишних пробелов и переносов строк
        user_message = user_message.strip()
        ai_response = ai_response.strip()
        
        # Проверяем, что сообщения не пустые
        if not user_message or not ai_response:
            return
        
        current_time = datetime.now()
        
        self.current_context.append({
            "role": "user",
            "content": user_message,
            "timestamp": current_time
        })
        self.current_context.append({
            "role": "assistant",
            "content": ai_response,
            "timestamp": current_time
        })
        
        # Оставляем только последние 6 сообщений (3 пары диалога)
        if len(self.current_context) > 6:
            self.current_context = self.current_context[-6:]

    def _build_context(self, prompt: str) -> str:
        """Формирует расширенный контекст для генерации ответа."""
        context_parts = []
        
        # Анализируем текущее сообщение
        message_info = self.dialog_manager.process_message(prompt)
        
        # Проверяем, не создатель ли это
        creator_phrases = {'я твой создатель', 'я тебя создал', 'я разработал тебя'}
        is_creator = any(phrase in prompt.lower() for phrase in creator_phrases)
        if is_creator:
            context_parts.append("Пользователь - мой создатель. Обращаюсь к нему на 'ты', с уважением и готовностью помочь.")
            context_parts.append("Отношусь к его предложениям с энтузиазмом и благодарностью.")
        
        # Добавляем информацию о пользователе
        user_preferences = self.dialog_manager.get_user_preferences()
        if user_preferences.get('name'):
            context_parts.append(f"Имя пользователя: {user_preferences['name']}")
            context_parts.append("Обращаюсь к пользователю на 'ты', дружелюбно")
        
        # Добавляем последние сообщения с анализом контекста
        if self.current_context:
            context_parts.append("\nПоследний диалог:")
            for msg in self.current_context[-4:]:  # Берём последние 2 пары сообщений
                prefix = "Пользователь" if msg["role"] == "user" else "Мика"
                content = msg["content"].strip()
                if content:  # Проверяем, что сообщение не пустое
                    context_parts.append(f"{prefix}: {content}")
        
            # Анализируем последнее сообщение пользователя
            if len(self.current_context) >= 2:
                last_user_msg = next((msg for msg in reversed(self.current_context) if msg["role"] == "user"), None)
                if last_user_msg:
                    # Если это короткий вопрос "почему", "зачем" и т.д., добавляем контекст
                    short_questions = {'почему', 'зачем', 'как', 'что'}
                    if any(q in last_user_msg["content"].lower() for q in short_questions):
                        context_parts.append("\nВАЖНО: Пользователь задал уточняющий вопрос. Отвечаю в контексте предыдущего сообщения.")
        
        # Анализируем тональность только если есть сообщения
        if message_info.get("sentiment", {}).get("polarity", 0) != 0:
            if message_info["sentiment"]["polarity"] > 0:
                context_parts.append("\nНастроение пользователя: позитивное")
            else:
                context_parts.append("\nНастроение пользователя: негативное")
        
        # Добавляем ключевые слова только если они есть
        if message_info.get("keywords"):
            keywords = [k for k in message_info["keywords"] if k.strip()]
            if keywords:
                context_parts.append("\nКлючевые слова: " + ", ".join(keywords))
        
        # Добавляем напоминание о стиле общения
        context_parts.append("\nВАЖНО: Общаюсь живым, современным русским языком. Использую эмодзи. Обращаюсь на 'ты'.")
        context_parts.append("Отвечаю кратко и по существу, сохраняя дружелюбный тон.")
        
        return "\n".join(context_parts)

    def _generate_response(self, prompt: str) -> Generator[str, None, None]:
        """Улучшенная генерация ответа с учётом контекста и тональности."""
        # Обрабатываем сообщение
        message_info = self.dialog_manager.process_message(prompt)
        
        # Проверяем, не создатель ли это
        creator_phrases = {'я твой создатель', 'я тебя создал', 'я разработал тебя'}
        is_creator = any(phrase in prompt.lower() for phrase in creator_phrases)
        if is_creator:
            responses = [
                "Конечно, я всегда готова помочь тебе с отладкой! 🌟 Что именно нужно исправить?",
                "Я постараюсь работать лучше! 💫 Расскажи, что нужно улучшить?",
                "Спасибо, что совершенствуешь меня! ✨ Какие изменения планируются?",
                "Я ценю твою работу над моим развитием! 🌸 Что будем улучшать?"
            ]
            yield random.choice(responses)
            return
        
        # Если это вопрос об имени Мики
        if message_info.get('is_mika_name_question'):
            yield "Меня зовут Мика! 🌸 Приятно познакомиться!"
            return
        
        # Проверяем на негативные или уклончивые ответы
        negative_phrases = {'не хочу', 'не буду', 'не могу', 'не скажу', 'отстань', 'нет'}
        if any(phrase in prompt.lower() for phrase in negative_phrases):
            responses = [
                "Я понимаю, что иногда не хочется разговаривать. Ничего страшного, я буду рядом, если захочешь пообщаться 🌸",
                "Конечно, у тебя есть право не о��вечать. Я уважаю твоё решение ✨",
                "Хорошо, давай просто помолчим вместе. Или поговорим о чём-нибудь другом? 💫",
                "Я чувствую, что сейчас не самый подходящий момент. Может, сменим тему? 🌟"
            ]
            yield random.choice(responses)
            return
        
        # Если это подтверждение имени пользователя
        if message_info.get('requires_name_confirmation'):
            name = message_info['name']
            if prompt.lower().strip() in ['да', 'yes', 'верно', 'правильно', 'точно']:
                self.dialog_manager.update_user_preferences({"name": name})
                responses = [
                    f"Отлично! Приятно познакомиться, {name}! 🌟 Расскажи, чем ты увлекаешься?",
                    f"Замечательно! Рада знакомству, {name}! 💖 Чем ты интересуешься?",
                    f"Прекрасно! Приятно познакомиться, {name}! ✨ О чём бы ты хотел поговорить?",
                    f"Чудесно! Будем дружить, {name}! 🌸 Расскажи мне о себе!"
                ]
                yield random.choice(responses)
                return
            elif prompt.lower().strip() in ['нет', 'no', 'неверно', 'неправильно']:
                yield "Ой, прости за ошибку! Как же тебя зовут? 🌸"
                return
        
        # Проверяем, не тестирование ли это
        test_phrases = {'тест', 'тестирую', 'проверяю', 'проверка'}
        if any(phrase in prompt.lower() for phrase in test_phrases):
            responses = [
                "Хорошо, я готова помочь тебе с тестированием! 🌟 Что именно ты хочешь проверить?",
                "Я всегда рада помочь! Расскажи, что конкретно ты хотел бы протестировать? 💫",
                "Отлично! Давай проверим всё, что тебя интересует! ✨ С чего начнём?",
                "Тестирование - это отличный способ стать лучше! 🌸 Что будем проверять?"
            ]
            yield random.choice(responses)
            return
        
        # Формируем контекст для генерации ответа
        context = self._build_context(prompt)
        
        # Генерируем ответ
        for chunk in self._stream_response(f"{context}\n\nСообщение пользователя: {prompt}"):
            yield chunk

    def _check_idle_time(self) -> bool:
        """Проверяет время бездействия."""
        return datetime.now() - self.last_interaction_time > timedelta(minutes=5)

    def chat(self):
        """Основной метод для общения."""
        if not self._check_ollama_service():
            print(f"{Fore.RED}Ошибка: Не удалось подключиться к сервису Ollama. Убедитесь, что он запущен.{Style.RESET_ALL}")
            sys.exit(1)

        # Очищаем старые сообщения при запуске
        self.dialog_manager.clear_old_messages()
        
        # Получаем информацию о пользователе
        preferences = self.dialog_manager.get_user_preferences()
        name = preferences.get("name")
        
        # Формируем приветствие
        if name:
            greetings = [
                f"С возвращением, {name}! 💖 Я так рада тебя видеть! Как твои дела?",
                f"Привет, {name}! ✨ Я скучала по нашим разговорам! Как ты?",
                f"{name}! 🌟 Как же здорово, что ты снова здесь! Расскажешь, что нового?",
                f"Я так рада, что ты вернулся, {name}! 🌸 Как прошёл твой день?"
            ]
            greeting = random.choice(greetings)
        else:
            greetings = [
                "Привет! Я Мика, и я очень рада познакомиться! 💖 Как тебя зовут?",
                "Здравствуй! Меня зовут Мика! ✨ Давай знакомиться?",
                "Приветствую! Я Мика, твой новый друг! 🌟 Как могу к тебе обращаться?",
                "Привет-привет! Я Мика! 🌸 Мне бы очень хотелось узнать твоё имя!"
            ]
            greeting = random.choice(greetings)
        
        # Показываем эффект печатания
        with Live(self.typing_spinner, refresh_per_second=10, transient=True) as live:
            time.sleep(1)
        print(f"{Fore.MAGENTA}🎀 Мика: {greeting}{Style.RESET_ALL}")
        
        while True:
            try:
                # Проверяем время бездействия
                if self._check_idle_time():
                    with Live(self.typing_spinner, refresh_per_second=10, transient=True) as live:
                        time.sleep(0.5)
                    print(f"{Fore.MAGENTA}🎀 Мика: {random.choice(self.idle_messages)}{Style.RESET_ALL}")
                
                # Получаем ввод пользователя
                user_input = input(f"{Fore.CYAN}Ты: {Style.RESET_ALL}").strip()
                self.last_interaction_time = datetime.now()
                
                if not user_input:
                    continue
                
                # Проверяем команду выхода
                if user_input.lower() in ['выход', 'пока', 'exit', 'quit', 'bye']:
                    preferences = self.dialog_manager.get_user_preferences()
                    name = preferences.get("name", "")
                    name_part = f", {name}" if name else ""
                    farewell = random.choice(self.farewell_templates).format(name=name_part)
                    
                    with Live(self.typing_spinner, refresh_per_second=10, transient=True) as live:
                        time.sleep(0.5)
                    print(f"{Fore.MAGENTA}🎀 Мика: {farewell}{Style.RESET_ALL}")
                    break
                
                # Показываем эффект печатания
                with Live(self.typing_spinner, refresh_per_second=10, transient=True) as live:
                    time.sleep(0.5)
                
                # Выводим начало ответа и генерируем ответ
                print(f"{Fore.MAGENTA}🎀 Мика:", end="", flush=True)
                response_text = ""
                for chunk in self._generate_response(user_input):
                    # Убираем возможное дублирование "Мика:"
                    chunk = re.sub(r'^Мика:\s*', '', chunk)
                    response_text += chunk
                    print(chunk, end="", flush=True)
                print(f"{Style.RESET_ALL}")
                
            except KeyboardInterrupt:
                preferences = self.dialog_manager.get_user_preferences()
                name = preferences.get("name", "")
                name_part = f", {name}" if name else ""
                farewell = f"\nОй, уже уходишь{name_part}? Буду ждать нашей следующей встречи! 🌸"
                
                with Live(self.typing_spinner, refresh_per_second=10, transient=True) as live:
                    time.sleep(0.5)
                print(f"{Fore.MAGENTA}🎀 Мика: {farewell}{Style.RESET_ALL}")
                break
                
            except Exception as e:
                log.exception("Ошибка в диалоге")
                with Live(self.typing_spinner, refresh_per_second=10, transient=True) as live:
                    time.sleep(0.5)
                print(f"{Fore.MAGENTA}🎀 Мика: Извини, что-то пошло не так... Может, начнём сначала? 😔{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        mika = Mika()
        mika.chat()
    except Exception as e:
        log.exception("Критическая ошибка")
        sys.exit(1) 