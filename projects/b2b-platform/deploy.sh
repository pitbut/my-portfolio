#!/bin/bash
# Передеплой B2B Platform UZ на VPS. Запускать из любой директории:
#   /root/my-portfolio/projects/b2b-platform/deploy.sh
set -e

cd /root/my-portfolio
echo "== git pull =="
git pull origin main

cd projects/b2b-platform
echo "== flask db upgrade =="
source venv/bin/activate
flask db upgrade
deactivate

echo "== restart b2b-platform =="
systemctl restart b2b-platform

echo "== готово, статус сервиса =="
systemctl status b2b-platform --no-pager -l | head -10
