#!/usr/bin/env bash
set -e

echo "=== Task Manager Update Script ==="

# 1. Остановить backend (APScheduler корректно завершится)
echo "[1/7] Остановка backend..."
sudo systemctl stop task-manager-backend

# 2. Обновить код из Git
echo "[2/7] Обновление кода из Git..."
sudo systemctl restart task-manager-git-sync
sudo systemctl status task-manager-git-sync --no-pager

# 3. Пересоздать venv (чтобы избежать конфликтов зависимостей)
echo "[3/7] Обновление Python окружения..."
if [ -d /var/lib/task-manager/venv ]; then
    echo "Удаление старого venv..."
    sudo -u task-manager rm -rf /var/lib/task-manager/venv
fi

# 4. Пересобрать frontend
echo "[4/7] Пересборка frontend..."
sudo systemctl restart task-manager-frontend-build
sleep 2
sudo systemctl status task-manager-frontend-build --no-pager

# 5. Запустить backend (venv создастся автоматически в preStart)
echo "[5/7] Запуск backend..."
sudo systemctl start task-manager-backend
sleep 3

# 6. Проверить статус backend
echo "[6/7] Проверка статуса backend..."
sudo systemctl status task-manager-backend --no-pager

# 7. Перезагрузить reverse proxy
echo "[7/7] Перезагрузка Caddy..."
sudo systemctl reload caddy

echo ""
echo "✅ Обновление завершено!"
echo ""
echo "Проверка логов backend:"
echo "  sudo journalctl -u task-manager-backend -n 50 --no-pager"
echo ""
echo "Проверка APScheduler:"
echo "  sudo journalctl -u task-manager-backend | grep -i scheduler"
