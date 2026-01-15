# Обновление Task Manager в NixOS

## Быстрое обновление

```bash
# 1. Пуш изменений в Git (если еще не сделано)
cd /home/user/umtask
git push origin claude/task-manager-fastapi-hYjWx

# 2. Применить обновленную конфигурацию NixOS
sudo nixos-rebuild switch

# 3. Проверить статус сервисов
sudo systemctl status task-manager-backend
sudo systemctl status task-manager-db-migrate
```

## Что изменилось

### В NixOS модуле (`deployment/nixos-module.nix`):

1. **Добавлен APScheduler** в Python окружение
   - Требуется для фонового планировщика

2. **Новый сервис: `task-manager-db-migrate`**
   - Автоматически применяет миграции БД при обновлении
   - Запускается перед backend
   - Безопасно: если миграция не нужна - пропускается

### Новые возможности

Система автоматического управления временем:
- Настройка времени доступности Roll
- Автоматические штрафы в полночь
- Автоматический Roll в заданное время
- Все настраивается через веб-интерфейс в Settings

## Troubleshooting

### Backend не запускается

```bash
# Проверить логи
sudo journalctl -u task-manager-backend -f

# Проверить что миграция прошла
sudo journalctl -u task-manager-db-migrate

# Перезапустить сервисы
sudo systemctl restart task-manager-git-sync
sudo systemctl restart task-manager-db-migrate
sudo systemctl restart task-manager-backend
```

### Миграция не применилась

```bash
# Проверить что код синхронизирован
ls -la /var/lib/task-manager/backend/migrate_time_settings.py

# Запустить миграцию вручную
sudo -u task-manager python /var/lib/task-manager/backend/migrate_time_settings.py /var/lib/task-manager/task_manager.db

# Перезапустить backend
sudo systemctl restart task-manager-backend
```

### "Failed to load data" в веб-интерфейсе

```bash
# Проверить что backend работает
curl http://localhost:8000/

# Проверить логи
sudo journalctl -u task-manager-backend -n 50

# Проверить reverse proxy
sudo systemctl status caddy  # или nginx
```

## Структура сервисов

```
task-manager-git-sync        # Синхронизация из Git
  └─> task-manager-db-migrate       # Миграция БД
       └─> task-manager-backend      # Backend API
            ├─> caddy/nginx           # Reverse proxy
            └─> task-manager-frontend-build  # Собранный фронтенд
```

## Логи

- Backend: `sudo journalctl -u task-manager-backend -f`
- Миграция: `sudo journalctl -u task-manager-db-migrate`
- Планировщик: `/var/log/task-manager/app.log`
- Caddy: `sudo journalctl -u caddy -f`

## Откат

Если что-то пошло не так:

```bash
# Откатить Git на предыдущий коммит
cd /var/lib/task-manager
sudo -u task-manager git reset --hard <предыдущий-commit>

# Перезапустить
sudo systemctl restart task-manager-backend
```
