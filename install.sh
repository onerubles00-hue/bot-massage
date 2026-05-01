#!/bin/bash

echo "🚀 Установка бота..."

# Клонирование проекта
git clone https://github.com/onerubles00-hue/bot-massage.git

cd bot-massage || exit

# Создание виртуального окружения
python3 -m venv venv

# Активация
source venv/bin/activate

# Обновление pip
pip install --upgrade pip

# Установка зависимостей
pip install -r requirements.txt

echo "✅ Установка завершена"
echo "👉 Запуск: cd bot-massage && source venv/bin/activate && python bot-massage.py"
