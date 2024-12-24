import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
import wikipediaapi
import logging
from typing import List, Dict, Optional
import re
from textblob import TextBlob

# Загружаем необходимые ресурсы NLTK
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except Exception as e:
    logging.warning(f"Не удалось загрузить ресурсы NLTK: {str(e)}")

class TextProcessor:
    def __init__(self):
        self.wiki = wikipediaapi.Wikipedia(
            language='ru',
            extract_format=wikipediaapi.ExtractFormat.WIKI,
            user_agent='MikaAssistant/1.0 (daniil@example.com)'
        )
        try:
            self.stop_words = set(stopwords.words('russian'))
        except:
            self.stop_words = set()
            logging.warning("Не удалось загрузить стоп-слова, используем пустой список")
        
        # Добавляем базовые стоп-слова
        self.stop_words.update({
            'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как',
            'а', 'то', 'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к',
            'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне',
            'было', 'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из', 'ему'
        })
        
    def analyze_text(self, text: str) -> Dict:
        """Комплексный анализ текста."""
        # Используем TextBlob для анализа тональности
        blob = TextBlob(text)
        
        return {
            'sentiment': self._analyze_sentiment(text),
            'keywords': self.extract_keywords(text),
            'is_question': self._is_question(text)
        }
    
    def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Анализ тона��ьности текста."""
        # Простой анализ на основе ключевых слов
        positive_words = {
            'хорошо', 'отлично', 'замечательно', 'прекрасно', 'великолепно',
            'рад', 'счастлив', 'доволен', 'люблю', 'нравится', 'спасибо'
        }
        negative_words = {
            'плохо', 'ужасно', 'отвратительно', 'грустно', 'печально',
            'жаль', 'жалко', 'обидно', 'ненавижу', 'злюсь', 'раздражает'
        }
        
        words = set(word.lower() for word in word_tokenize(text))
        pos_count = len(words.intersection(positive_words))
        neg_count = len(words.intersection(negative_words))
        total = pos_count + neg_count if pos_count + neg_count > 0 else 1
        
        return {
            'polarity': (pos_count - neg_count) / total,
            'subjectivity': (pos_count + neg_count) / len(words) if words else 0
        }
    
    def extract_keywords(self, text: str, limit: int = 5) -> List[str]:
        """Извлечение ключевых слов из текста."""
        # Токенизация и приведение к нижнему регистру
        tokens = word_tokenize(text.lower())
        
        # Удаление стоп-слов и пунктуации
        words = [word for word in tokens 
                if word.isalnum() and 
                word not in self.stop_words and 
                len(word) > 2]
        
        # Подсчет частоты слов
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Сортировка по частоте и возврат топ-N слов
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:limit]]
    
    def _is_question(self, text: str) -> bool:
        """Определяет, является ли текст вопросом."""
        # Проверяем наличие вопросительного знака
        if '?' in text:
            return True
        
        # Проверяем наличие вопросительных слов
        question_words = {'что', 'где', 'когда', 'почему', 'зачем', 'как', 'кто', 'чей', 'какой'}
        words = set(word.lower() for word in word_tokenize(text))
        return bool(words.intersection(question_words))
    
    def get_wiki_info(self, query: str, sentences: int = 3) -> Optional[str]:
        """Получение информации из Wikipedia."""
        try:
            page = self.wiki.page(query)
            if page.exists():
                # Получаем первые N предложений
                text = ' '.join(sent_tokenize(page.summary)[:sentences])
                return text
            return None
        except Exception as e:
            logging.error(f"Ошибка при получении информации из Wikipedia: {str(e)}")
            return None
    
    def find_entities(self, text: str) -> Dict[str, List[str]]:
        """Находит именованные сущности в тексте."""
        # Простой поиск сущностей на основе заглавных букв
        words = text.split()
        proper_nouns = []
        
        for word in words:
            if word and word[0].isupper() and not word.isupper():
                # Убираем знаки препинания
                clean_word = re.sub(r'[^\w\s]', '', word)
                if clean_word:
                    proper_nouns.append(clean_word)
        
        return {
            'proper_nouns': proper_nouns
        }
    
    def clean_text(self, text: str) -> str:
        """Очищает текст от специальных символов и лишних пробелов."""
        # Удаляем специальные символы
        text = re.sub(r'[^\w\s\.\,\!\?\-]', '', text)
        # Заменяем множественные пробелы на один
        text = re.sub(r'\s+', ' ', text)
        return text.strip() 