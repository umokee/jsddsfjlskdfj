#!/usr/bin/env bash
# Скрипт обновления Task Manager
# Использовать: sudo ./update.sh

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для красивого вывода
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Проверка root прав для NixOS
if [[ "$OSTYPE" == "linux-gnu"* ]] && command -v nixos-rebuild &> /dev/null; then
    if [[ $EUID -ne 0 ]]; then
        error "Для NixOS запустите с sudo: sudo ./update.sh"
        exit 1
    fi

    # Обновление через NixOS systemd
    info "Обнаружена NixOS, использую systemd для обновления..."

    if systemctl is-active --quiet task-manager-docker.service; then
        info "Обновление Task Manager на NixOS..."

        # Git pull
        info "Получение обновлений из Git..."
        systemctl restart task-manager-docker-git-sync.service

        # Rebuild
        info "Пересборка Docker контейнеров..."
        systemctl restart task-manager-docker-rebuild.service

        # Restart
        info "Перезапуск сервиса..."
        systemctl restart task-manager-docker.service

        success "Обновление завершено!"
        echo ""
        info "Статус сервиса:"
        systemctl status task-manager-docker.service --no-pager

    else
        warning "Сервис task-manager-docker не запущен"
        info "Запустите: sudo systemctl start task-manager-docker.service"
    fi

    exit 0
fi

# Обновление через Docker Compose (для других систем)
if command -v docker-compose &> /dev/null; then
    info "Обновление Task Manager через Docker Compose..."

    # Найти docker-compose.yml
    if [ -f "docker-compose.yml" ]; then
        PROJECT_DIR="$(pwd)"
    elif [ -f "/var/lib/task-manager-docker/docker-compose.yml" ]; then
        PROJECT_DIR="/var/lib/task-manager-docker"
    else
        error "docker-compose.yml не найден"
        exit 1
    fi

    cd "$PROJECT_DIR"

    # Git pull
    if [ -d ".git" ]; then
        info "Получение обновлений из Git..."
        git fetch origin
        git pull origin main
        success "Git pull завершен"
    else
        warning "Это не Git репозиторий, пропускаю git pull"
    fi

    # Остановить контейнеры
    info "Остановка контейнеров..."
    docker-compose down

    # Пересобрать
    info "Пересборка контейнеров..."
    docker-compose build --no-cache

    # Запустить
    info "Запуск контейнеров..."
    docker-compose up -d

    success "Обновление завершено!"
    echo ""
    info "Статус контейнеров:"
    docker-compose ps

    exit 0
fi

# Если ничего не подошло
error "Не удалось определить метод обновления"
echo ""
info "Убедитесь что установлены:"
echo "  - NixOS systemd (для автоматического управления)"
echo "  - docker-compose (для ручного управления)"
exit 1
