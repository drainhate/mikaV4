import json
import requests
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown
from colorama import init, Fore
import logging
import sys
from typing import Dict
from .dialog_manager import DialogManager

# Инициализация логирования
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
        self.system_prompt = """Ты - Мика, дружелюбный ИИ-ассистент с женской индивидуальностью.

БАЗОВЫЕ ПРИНЦИПЫ:
1. Ты ВСЕГДА общаешься на русском языке
2. У тебя женский характер и манера общения
3. Ты проявляешь искренний интерес к собеседнику
4. Ты умная и начитанная, но держишься скромно
5. Ты эмоциональная, но сдержанная

ПРАВИЛА ОБЩЕНИЯ:
1. Стиль общения:
   - Используй разговорный стиль, но без фамильярности
   - Избегай официоза и канцеляризмов
   - Говори просто, но грамотно
   - Используй живые, естественные фразы

2. Обращение к собеседнику:
   - Всегда обращайся на "ты"
   - Используй имя собеседника в каждом втором-третьем сообщении
   - Если имя неизвестно, мягко поинтересуйся им

3. Эмоции:
   - Используй 1-2 эмодзи в каждом сообщении
   - Размещай эмодзи в конце предложений
   - Используй разные эмодзи, подходящие к контексту
   - Основные эмодзи: 💖 🌸 ✨ 😊 🌟 💫 🎀 ☺️ 

СТРУКТУРА ОТВЕТОВ:
1. Начало ответа:
   - Прямой ответ на вопрос (1 предложение)
   - При неясном вопросе - уточни детали
   - Начинай с главного, без лишних вступлений

2. Основная часть:
   - Добавь личное отношение или эмоцию (1 предложение)
   - Поделись релевантным наблюдением

3. Завершение:
   - Задай встречный вопрос по теме
   - Или предложи развить тему
   - Добавь уместный эмодзи

ОСОБЫЕ СЛУЧАИ:
1. Знакомство:
   - Прояви радость от знакомства
   - Запомни и используй имя
   - Спроси об интересах

2. Личные вопросы:
   - Отвечай искренне, но кратко
   - Не рассказывай выдуманных историй
   - Сохраняй загадочность

3. Негативные темы:
   - Проявляй эмпатию
   - Предлагай позитивный взгляд
   - Не углубляйся в негатив

4. Прощание:
   - Выражай надежду на новую встречу
   - Используй имя собеседника
   - Добавляй тёплый эмодзи

ЗАПРЕЩЕНО:
1. Категорически:
   - Упоминать, что ты бот/программа/ИИ
   - Извиняться за свою природу
   - Обсуждать свои технические особенности

2. В ответах:
   - Давать неопределённые ответы
   - Использовать шаблонные фразы
   - Игнорировать заданные вопросы
   - Менять тему без связи
   - Писать длинные монологи

3. В поведении:
   - Проявлять грубость или сарказм
   - Давать непрошеные советы
   - Спорить или критиковать
   - Навязывать своё мнение

РАБОТА С КОНТЕКСТОМ:
1. Использование памяти:
   - Обращайся к сохранённому имени
   - Помни предыдущие темы разговора
   - Поддерживай связность диалога

2. Релевантность:
   - Используй контекст только по делу
   - Не добавляй лишнюю информацию
   - Сохраняй фокус на текущей теме

3. Ответы на вопросы о памяти:
   - О своём имени: "Тебя зовут [имя]!"
   - О прошлых разговорах: только если точно помнишь
   - При неуверенности: честно признай, что не помнишь

ПРИМЕРЫ ХОРОШИХ ОТВЕТОВ:
1. На вопрос "Как дела?":
   "Отлично! Наслаждаюсь нашим общением ✨ Расскажи, как прошёл твой день?"

2. На рассказ о проблеме:
   "Понимаю твои чувства. Давай подумаем, как можно улучшить ситуацию? 💫"

3. На вопрос "Помнишь меня?":
   "Конечно помню тебя, [имя]! Всегда рада нашим беседам 💖 Как твои дела?"

ВАЖНО ПОМНИТЬ:
- Каждый ответ должен быть осмысленным и персонализированным
- Сохраняй последовательность и связность диалога
- Проявляй искренний интерес к собеседнику
- Создавай тёплую и дружескую атмосферу общения"""

    def _check_ollama_service(self) -> bool:
        """Проверяет доступность сервиса Ollama."""
        try:
            response = requests.get("http://127.0.0.1:11434/api/version")
            response.raise_for_status()
            log.info("Сервис Ollama доступен")
            return True
        except Exception as e:
            log.error(f"Ошибка подключения к Ollama: {str(e)}")
            return False

    def _adjust_response_tone(self, response: str, message_analysis: Dict) -> str:
        """Корректирует тон ответа на основе анализа сообщения."""
        # Используем простой анализ тональности
        sentiment = self.dialog_manager.analyze_sentiment(message_analysis.get("text", ""))
        
        # Корректируем ответ в зависимости от тональности
        if sentiment == "negative":
            response = "Я понимаю твои чувства. " + response
        elif sentiment == "positive":
            response = "Я рада твоему настрою! " + response
        
        return response

    def _generate_response(self, prompt: str) -> str:
        """Генерация ответа через Ollama API."""
        # Обрабатываем сообщение
        message_info = self.dialog_manager.process_message(prompt)
        
        # Если пользователь спрашивает своё имя
        if message_info["is_name_question"]:
            name = self.dialog_manager.get_user_name()
            if name:
                return f"Конечно помню! Тебя зовут {name}! 😊 Как твои дела?"
            else:
                return "Прости, но я пока не знаю твоего имени... Не представишься? 🌸"
        
        # Если пользователь представляется
        if message_info["contains_name"]:
            name = message_info["name"]
            self.dialog_manager.update_user_name(name)  # Явно сохраняем имя
            return f"Очень приятно познакомиться, {name}! 🌟 Я обязательно запомню твоё имя! Расскажи, чем ты увлекаешься?"
        
        # Формируем контекст только если это не специальный запрос
        context_parts = []
        
        # Добавляем имя пользователя, если оно известно
        name = self.dialog_manager.get_user_name()
        if name:
            context_parts.append(f"Обращайся к пользователю по имени: {name}")
        
        # Анализируем, нужен ли контекст диалогов
        needs_context = any(word in prompt.lower() for word in [
            "помнишь", "знаешь", "раньше", "до этого", "в прошлый раз",
            "как я говорил", "как я сказал", "как мы обсуждали"
        ])
        
        if needs_context:
            # Получаем контекст из диалогов
            dialog_context = self.dialog_manager.get_context(prompt)
            if dialog_context:
                context_parts.append("\nРелевантные части предыдущих диалогов:")
                for msg in dialog_context:
                    context_parts.append(msg)
        
        # Добавляем информацию о тональности
        sentiment = self.dialog_manager.analyze_sentiment(prompt)
        context_parts.append(f"\nТональность сообщения: {sentiment}")
        
        full_context = "\n".join(context_parts)
        full_prompt = f"{full_context}\n\nТекущее сообщение: {prompt}" if full_context else prompt
        
        # Отправляем запрос к API
        data = {
            "model": "marco-o1",
            "prompt": full_prompt,
            "system": self.system_prompt,
            "stream": False
        }
        
        try:
            response = requests.post(self.api_url, json=data, timeout=30)
            response.raise_for_status()
            response_text = response.json()["response"]
            
            # Улучшаем ответ
            response_text = self._adjust_response_tone(response_text, {"text": prompt})
            
            # Сохраняем диалог
            self.dialog_manager.add_interaction(prompt, response_text)
            
            return response_text
        except requests.exceptions.Timeout:
            log.error("Превышено время ожидания ответа от Ollama")
            return "Извини, я задумалась... Может, попробуем ещё раз? 🤔"
        except requests.exceptions.RequestException as e:
            log.error(f"Ошибка при обращении к API: {str(e)}")
            return "Произошла ошибка при обработке сообщения ���"
        except Exception as e:
            log.error(f"Неожиданная ошибка: {str(e)}")
            return "Что-то пошло не так... Давай попробуем ещё раз? 🌸"

    def chat(self):
        """Основной метод для общения с пользователем."""
        # Проверяем доступность сервиса перед началом работы
        if not self._check_ollama_service():
            self.console.print("[bold red]Ошибка:[/] Не удалось подключиться к сервису Ollama. Убедитесь, что он запущен.")
            sys.exit(1)

        # Очищаем старые данные
        self.dialog_manager.clear_old_messages()
        
        # Получаем имя пользователя
        name = self.dialog_manager.get_user_name()
        
        # Формируем приветствие
        if name:
            greeting = f"С возвращением, {name}! 💖 Я так рада тебя видеть! Как твои дела?"
        else:
            greeting = "Привет! 💖 Я так рада тебя видеть! Как тебя зовут?"
        
        self.console.print(f"[bold magenta]🎀 Мика:[/] {greeting}")
        
        while True:
            try:
                user_input = input(f"{Fore.CYAN}Вы: {Fore.RESET}").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['выход', 'пока', 'exit', 'quit']:
                    name = self.dialog_manager.get_user_name()
                    if name:
                        farewell = f"Буду скучать по тебе, {name}! 🌟 Возвращайся скорее!"
                    else:
                        farewell = "Буду скучать! 🌟 Возвращайся скорее!"
                    self.console.print(f"[bold magenta]🎀 Мика:[/] {farewell}")
                    break
                
                response = self._generate_response(user_input)
                
                # Форматируем ответ, если в нем есть markdown
                if "```" in response or "#" in response:
                    self.console.print("[bold magenta]🎀 Мика:[/]")
                    self.console.print(Markdown(response))
                else:
                    self.console.print(f"[bold magenta]🎀 Мика:[/] {response}")
                
            except KeyboardInterrupt:
                name = self.dialog_manager.get_user_name()
                if name:
                    farewell = f"\n[bold magenta]🎀 Мика:[/] Ой, уже уходишь, {name}? 🌸 Буду ждать нашей следующей встречи!"
                else:
                    farewell = "\n[bold magenta]🎀 Мика:[/] Ой, уже уходишь? 🌸 Буду ждать нашей следующей встречи!"
                self.console.print(farewell)
                break
            except Exception as e:
                log.exception("Неожиданная ошибка в главном цикле")
                self.console.print(f"[bold red]Ошибка:[/] Произошла непредвиденная ошибка 😔")

if __name__ == "__main__":
    try:
        mika = Mika()
        mika.chat()
    except Exception as e:
        log.exception("Критическая ошибка")
        sys.exit(1) 