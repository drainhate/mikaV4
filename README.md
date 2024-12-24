# Мика - Ваш ИИ-ассистент

Мика - это дружелюбный ИИ-ассистент, созданный для общения и помощи. Использует модель marcoo1 через Ollama для генерации ответов.

## Требования

- Python 3.8+
- Ollama с установленной моделью marcoo1:latest
- Работающий сервис Ollama на порту 11434

## Установка

1. Создайте виртуальное окружение:
```bash
python -m venv venv
```

2. Активируйте виртуальное окружение:
- Windows:
```bash
.\venv\Scripts\activate
```
- Linux/Mac:
```bash
source venv/bin/activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Запуск

Для запуска Мики выполните:
```bash
python run.py
```

## Использование

- Просто общайтесь с Микой на русском языке
- Для выхода введите "выход", "пока", "exit" или "quit"
- Для принудительного завершения используйте Ctrl+C

## Разработка

- Используйте `black` для форматирования кода:
```bash
black .
```

- Запуск тестов:
```bash
pytest
```
