#!/bin/bash
# Передеплой VR Shop на VPS. Запускать из любой директории:
#   /root/my-portfolio/projects/vr-shop/deploy.sh
set -e

cd /root/my-portfolio
echo "== git pull =="
git pull origin main

cd projects/vr-shop/backend
echo "== pip install (на случай новых зависимостей) =="
source venv/bin/activate
pip install -r requirements.txt
deactivate

echo "== restart vr-shop =="
systemctl restart vr-shop

echo "== готово, статус сервиса =="
systemctl status vr-shop --no-pager -l | head -10
