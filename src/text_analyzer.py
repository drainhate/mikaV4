import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.sentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
import spacy
import wikipedia
from duckduckgo_search import ddg
from typing import List, Dict, Optional, Tuple

# Загружаем необходимые компоненты NLTK
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('sentiment/vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon')

# Загружаем модель SpaCy для русского языка
try:
    nlp = spacy.load("ru_core_news_sm")
except OSError:
    spacy.cli.download("ru_core_news_sm")
    nlp = spacy.load("ru_core_news_sm")

class TextAnalyzer:
    def __init__(self):
        self.sia = SentimentIntensityAnalyzer()
        wikipedia.set_lang("ru")

    def analyze_message(self, text: str) -> Dict:
        """Анализирует сообщение и возвращает различные характеристики."""
        doc = nlp(text)
        
        # Базовый анализ
        analysis = {
            "entities": self._extract_entities(doc),
            "sentiment": self._analyze_sentiment(text),
            "topics": self._extract_topics(doc),
            "question": self._is_question(doc),
            "command": self._is_command(doc)
        }
        
        # Если это вопрос, пытаемся найти ответ
        if analysis["question"]:
            analysis["possible_answers"] = self._find_answers(text)
        
        return analysis

    def _extract_entities(self, doc) -> Dict[str, List[str]]:
        """Извлекает именованные сущности из текста."""
        entities = {
            "names": [],
            "locations": [],
            "organizations": [],
            "dates": [],
            "other": []
        }
        
        for ent in doc.ents:
            if ent.label_ == "PER":
                entities["names"].append(ent.text)
            elif ent.label_ == "LOC":
                entities["locations"].append(ent.text)
            elif ent.label_ == "ORG":
                entities["organizations"].append(ent.text)
            elif ent.label_ == "DATE":
                entities["dates"].append(ent.text)
            else:
                entities["other"].append((ent.text, ent.label_))
        
        return entities

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

    def _extract_topics(self, doc) -> List[str]:
        """Извлекает основные темы из текста."""
        topics = []
        
        # Извлекаем существительные и именованные сущности
        for token in doc:
            if token.pos_ == "NOUN" and len(token.text) > 3:
                topics.append(token.text.lower())
        
        # Добавляем именованные сущности
        for ent in doc.ents:
            if ent.label_ in ["LOC", "ORG", "PRODUCT", "EVENT"]:
                topics.append(ent.text.lower())
        
        return list(set(topics))

    def _is_question(self, doc) -> bool:
        """Определяет, является ли текст вопросом."""
        # Проверяем наличие вопросительных слов
        question_words = {"что", "кто", "где", "когда", "почему", "как", "зачем", "какой", "чей"}
        
        # Проверяем первое слово
        if doc[0].text.lower() in question_words:
            return True
        
        # Проверяем знаки препинания
        if doc[-1].text == "?":
            return True
        
        return False

    def _is_command(self, doc) -> bool:
        """Определяет, является ли текст командой."""
        # Проверяем наличие глаголов в повелительном наклонении
        command_verbs = {"покажи", "расскажи", "найди", "открой", "запусти", "включи", "выключи"}
        
        if doc[0].text.lower() in command_verbs:
            return True
        
        return False

    def _find_answers(self, question: str) -> Dict[str, str]:
        """Ищет возможные ответы на вопрос."""
        answers = {}
        
        # Пытаемся най��и ответ в Википедии
        try:
            wiki_results = wikipedia.search(question, results=1)
            if wiki_results:
                page = wikipedia.page(wiki_results[0])
                answers["wikipedia"] = page.summary[:500] + "..."
        except:
            pass
        
        # Ищем через DuckDuckGo
        try:
            ddg_results = ddg(question, max_results=3)
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

    def extract_user_info(self, text: str) -> Dict[str, Optional[str]]:
        """Извлекает информацию о пользователе из текста."""
        doc = nlp(text)
        info = {
            "name": None,
            "interests": [],
            "facts": []
        }
        
        # Ищем имя
        if "меня зовут" in text.lower():
            for token in doc:
                if token.pos_ == "PROPN":
                    info["name"] = token.text
                    break
        
        # Ищем интересы
        interest_markers = ["люблю", "нравится", "увлекаюсь", "интересует"]
        for sent in doc.sents:
            sent_text = sent.text.lower()
            for marker in interest_markers:
                if marker in sent_text:
                    for token in sent:
                        if token.pos_ == "NOUN":
                            info["interests"].append(token.text.lower())
        
        # Ищем факты
        fact_markers = ["я", "мой", "моя", "мне"]
        for sent in doc.sents:
            for token in sent:
                if token.text.lower() in fact_markers:
                    info["facts"].append(sent.text)
        
        return info 