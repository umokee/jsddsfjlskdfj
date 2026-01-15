#!/bin/bash
# Скрипт для запуска Task Manager API с внешним доступом

cd "$(dirname "$0")/.."

# Проверка API ключа
if [ -z "$TASK_MANAGER_API_KEY" ]; then
    echo "⚠️  ВНИМАНИЕ: TASK_MANAGER_API_KEY не установлен!"
    echo "Используется дефолтный ключ (НЕ БЕЗОПАСНО для продакшена)"
    echo ""
    echo "Установите безопасный ключ:"
    echo "  export TASK_MANAGER_API_KEY=\"\$(openssl rand -hex 32)\""
    echo ""
    read -p "Продолжить с дефолтным ключом? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Показать IP адреса
echo "========================================="
echo "🌐 Task Manager API - Внешний доступ"
echo "========================================="
echo ""
echo "📍 Локальный IP адрес:"
hostname -I | awk '{print "   http://"$1":8000"}'
echo ""
echo "📍 Внешний IP адрес:"
curl -s ifconfig.me | awk '{print "   http://"$1":8000"}'
echo ""
echo "🔑 API Key: ${TASK_MANAGER_API_KEY:-your-secret-key-change-me}"
echo ""
echo "========================================="
echo ""

# Запуск сервера
cd backend
echo "🚀 Запуск сервера на 0.0.0.0:8000..."
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
