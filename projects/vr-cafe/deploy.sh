#!/bin/bash
# Передеплой VR Cafe на VPS. Запускать из любой директории:
#   /root/my-portfolio/projects/vr-cafe/deploy.sh
set -e

cd /root/my-portfolio
echo "== git pull =="
git pull origin main

cd projects/vr-cafe
echo "== npm install (на случай новых зависимостей) =="
npm install --production

echo "== restart vr-cafe =="
systemctl restart vr-cafe

echo "== готово, статус сервиса =="
systemctl status vr-cafe --no-pager -l | head -10
