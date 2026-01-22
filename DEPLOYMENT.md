# Task Manager Deployment Guide

## Проблема с APScheduler после обновления

**Симптом:** После `git pull` и миграции APScheduler перестает работать.

**Причина:** Старые зависимости Python в venv конфликтуют с новым кодом и новой схемой БД.

**Решение:** Полностью пересоздавать venv при обновлении.

---

## Команды для обновления

### Вариант 1: Systemd сервис (рекомендуется)

```bash
# Обновить Task Manager (pull + rebuild + restart)
sudo systemctl start task-manager-update

# Проверить логи обновления
sudo journalctl -u task-manager-update -n 100 --no-pager

# Проверить что backend запустился
sudo systemctl status task-manager-backend
```

### Вариант 2: Bash скрипт

```bash
# Запустить скрипт обновления
bash /var/lib/task-manager/scripts/update.sh

# Или сделать его исполняемым
chmod +x /var/lib/task-manager/scripts/update.sh
/var/lib/task-manager/scripts/update.sh
```

---

## Что делает обновление

1. **Останавливает backend** - APScheduler корректно завершается
2. **Пуллит код из Git** - обновляет до последней версии ветки
3. **Удаляет старый venv** - убирает конфликты зависимостей
4. **Пересобирает frontend** - обновляет React приложение
5. **Запускает backend** - venv пересоздается, миграции БД применяются автоматически
6. **Проверяет статус** - убеждается что все запустилось
7. **Перезагружает Caddy** - обновляет reverse proxy

---

## Проверка APScheduler

```bash
# Проверить что APScheduler запустился
sudo journalctl -u task-manager-backend | grep -i "apscheduler started"

# Должно быть:
# >>> APScheduler STARTED <<<
# Scheduled jobs: ['auto_roll', 'auto_penalties', 'auto_backup']

# Проверить что джобы работают
sudo journalctl -u task-manager-backend | tail -100 | grep -E "\[AUTO_BACKUP\]|\[AUTO_ROLL\]|penalties"
```

---

## Проверка логов

```bash
# Последние 50 строк backend логов
sudo journalctl -u task-manager-backend -n 50 --no-pager

# Следить за логами в реальном времени
sudo journalctl -u task-manager-backend -f

# Логи миграций БД
sudo journalctl -u task-manager-backend | grep -i migration

# Логи ошибок
sudo journalctl -u task-manager-backend -p err
```

---

## Обновление NixOS конфигурации

Если ты используешь NixOS, замени старый конфиг на новый:

```bash
# 1. Скопировать новый конфиг
cp /var/lib/task-manager/nix-config-updated.nix /path/to/your/nixos/modules/task-manager.nix

# 2. Пересобрать NixOS
sudo nixos-rebuild switch

# 3. Проверить что сервисы запустились
sudo systemctl status task-manager-backend
sudo systemctl status task-manager-frontend-build
```

---

## Ручная очистка (если что-то пошло не так)

```bash
# 1. Остановить все сервисы
sudo systemctl stop task-manager-backend

# 2. Удалить venv
sudo rm -rf /var/lib/task-manager/venv

# 3. Сбросить миграции (ТОЛЬКО если БД сломалась!)
# ВНИМАНИЕ: Это удалит все данные!
sudo rm -f /var/lib/task-manager/tasks.db

# 4. Запустить backend (все пересоздастся)
sudo systemctl start task-manager-backend
```

---

## FAQ

### Q: Почему APScheduler перестает работать?

**A:** При обновлении кода меняется структура БД (миграции). Старые зависимости Python могут не поддерживать новую схему. Решение - пересоздать venv.

### Q: Можно ли обновляться без остановки backend?

**A:** Нет. APScheduler должен корректно завершиться перед обновлением, иначе могут быть конфликты.

### Q: Как часто нужно обновляться?

**A:** При каждом `git pull` с изменениями в backend. Если только frontend - можно просто пересобрать frontend.

### Q: Безопасно ли удалять venv?

**A:** Да. Venv пересоздастся автоматически из `requirements.txt` при следующем запуске.

---

## Troubleshooting

### Backend не запускается

```bash
# Проверить логи
sudo journalctl -u task-manager-backend -n 200 --no-pager

# Проверить что venv создался
ls -la /var/lib/task-manager/venv

# Проверить что зависимости установились
/var/lib/task-manager/venv/bin/pip list
```

### APScheduler не создает джобы

```bash
# Проверить что scheduler запустился
sudo journalctl -u task-manager-backend | grep "APScheduler"

# Проверить что джобы добавились
sudo journalctl -u task-manager-backend | grep "Scheduled jobs"

# Ожидаемый вывод:
# Scheduled jobs: ['auto_roll', 'auto_penalties', 'auto_backup']
```

### База данных сломалась

```bash
# ВНИМАНИЕ: Это удалит все данные!
sudo systemctl stop task-manager-backend
sudo rm -f /var/lib/task-manager/tasks.db
sudo systemctl start task-manager-backend

# БД пересоздастся с нуля
```
