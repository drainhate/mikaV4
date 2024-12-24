import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.sentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
import wikipedia
from duckduckgo_search import DDGS
from typing import Dict, List, Optional, Tuple

class TextAnalyzer:
    def __init__(self):
        # Загружаем необходимые компоненты NLTK
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('sentiment/vader_lexicon')
        except LookupError:
            nltk.download('punkt')
            nltk.download('vader_lexicon')
        
        self.sia = SentimentIntensityAnalyzer()
        self.ddgs = DDGS()
        wikipedia.set_lang("ru")

    def analyze_message(self, text: str) -> Dict:
        """Анализирует сообщение и возвращает различные характеристики."""
        # Базовый анализ
        analysis = {
            "sentiment": self._analyze_sentiment(text),
            "is_question": self.is_question(text),
            "is_command": self.is_command(text),
            "possible_answers": {}
        }
        
        # Если это вопрос, пытаемся найти ответ
        if analysis["is_question"]:
            analysis["possible_answers"] = self._find_answers(text)
        
        return analysis

    def extract_user_info(self, text: str) -> Dict[str, Optional[str]]:
        """Извлекает информацию о пользователе из текста."""
        info = {
            "name": None,
            "interests": [],
            "facts": []
        }
        
        # Разбиваем текст на предложения и анализируем тональность
        sentences = sent_tokenize(text.lower())
        blob = TextBlob(text)
        
        # Ищем имя
        name_markers = ["меня зовут", "моё имя", "мое имя", "я"]
        for sentence in sentences:
            for marker in name_markers:
                if marker in sentence:
                    words = word_tokenize(sentence)
                    try:
                        name_index = words.index(marker.split()[-1]) + 1
                        if name_index < len(words):
                            # Берем следующее слово после маркера как имя
                            info["name"] = words[name_index].title()
                            break
                    except ValueError:
                        continue
        
        # Ищем интересы с учетом тональности
        interest_markers = ["люблю", "нравится", "увлекаюсь", "интересует", "обожаю"]
        for sentence in blob.sentences:
            sent_text = str(sentence).lower()
            for marker in interest_markers:
                if marker in sent_text and sentence.sentiment.polarity > 0:
                    words = word_tokenize(sent_text)
                    try:
                        marker_index = words.index(marker)
                        # Добавляем следующее слово как интерес
                        if marker_index + 1 < len(words):
                            info["interests"].append(words[marker_index + 1])
                    except ValueError:
                        continue
        
        # Собираем факты о пользователе
        fact_markers = ["я", "мой", "моя", "мне", "у меня"]
        for sentence in sentences:
            for marker in fact_markers:
                if marker in sentence:
                    info["facts"].append(sentence)
                    break
        
        return info

    def _analyze_sentiment(self, text: str) -> Dict:
        """Анализирует эмоциональную окраску текста."""
        blob = TextBlob(text)
        vader_scores = self.sia.polarity_scores(text)
        
        return {
            "polarity": blob.sentiment.polarity,
            "subjectivity": blob.sentiment.subjectivity,
            "compound": vader_scores["compound"],
            "positive": vader_scores["pos"],
            "negative": vader_scores["neg"],
            "neutral": vader_scores["neu"]
        }

    def _find_answers(self, question: str) -> Dict[str, str]:
        """Ищет возможные ответы на вопрос."""
        answers = {}
        
        # Пытае��ся найти ответ в Википедии
        try:
            wiki_results = wikipedia.search(question, results=1)
            if wiki_results:
                page = wikipedia.page(wiki_results[0])
                answers["wikipedia"] = page.summary[:500] + "..."
        except:
            pass
        
        # Ищем через DuckDuckGo
        try:
            ddg_results = list(self.ddgs.text(question, max_results=3))
            if ddg_results:
                answers["web_search"] = [
                    {
                        "title": result["title"],
                        "link": result["link"],
                        "snippet": result["body"]
                    }
                    for result in ddg_results
                ]
        except:
            pass
        
        return answers

    def is_question(self, text: str) -> bool:
        """Определяет, является ли текст вопросом."""
        text = text.lower().strip()
        
        # Проверяем знак вопроса
        if text.endswith("?"):
            return True
        
        # Проверяем вопросительные слова
        question_words = {"что", "кто", "где", "когда", "почему", "как", "зачем", "какой", "чей", "сколько"}
        words = word_tokenize(text)
        
        return any(word in question_words for word in words)

    def is_command(self, text: str) -> bool:
        """Определяет, является ли текст командой."""
        text = text.lower().strip()
        command_verbs = {
            "покажи", "расскажи", "найди", "открой", "запусти", 
            "включи", "выключи", "помоги", "объясни", "сделай"
        }
        
        words = word_tokenize(text)
        return any(word in command_verbs for word in words) 