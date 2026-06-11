# ИСПОЛЬЗУЕМ СТАБИЛЬНЫЙ ОБРАЗ PYTHON
FROM python:3.11-slim

# УСТАНАВЛИВАЕМ LIBREOFFICE И ШРИФТЫ ДЛЯ ПОДДЕРЖКИ КИРИЛЛИЦЫ
RUN apt-get update && apt-get install -y \
    libreoffice \
    fonts-dejavu \
    fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# СОЗДАЕМ РАБОЧУЮ ПАПКУ И КОПИРУЕМ ПРОЕКТ
WORKDIR /app
COPY . /app

# УСТАНАВЛИВАЕМ БИБЛИОТЕКИ PYTHON
RUN pip install --no-cache-dir -r requirements.txt

# СТАНДАРТНАЯ СИСТЕМНАЯ КОМАНДА ЗАПУСКА
CMD ["python", "main.py"]

