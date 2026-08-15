#!/bin/bash
# Передеплой Telegram Bazar Bot на VPS. Запускать из любой директории:
#   /root/my-portfolio/projects/telegram-bazar-bot/deploy.sh
set -e

cd /root/my-portfolio
echo "== git pull =="
git pull origin main

cd projects/telegram-bazar-bot
echo "== pip install (на случай новых зависимостей) =="
source venv/bin/activate
pip install -r requirements.txt
deactivate

echo "== restart telegram-bazar-bot =="
systemctl restart telegram-bazar-bot

echo "== готово, статус сервиса =="
systemctl status telegram-bazar-bot --no-pager -l | head -10
