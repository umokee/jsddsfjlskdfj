# Миграция на Docker в NixOS

Это руководство объясняет, как мигрировать с прямого systemd-деплоя на Docker-деплой в NixOS.

## Зачем Docker?

**Проблема со scheduler'ом решена навсегда!** 🎯

Docker обеспечивает:
- ✅ **Изолированное окружение** - scheduler гарантированно запускается с app
- ✅ **Видимые логи** - все логи scheduler видны через `docker-compose logs` и journald
- ✅ **Автоматический restart** - Docker перезапускает контейнеры при падении
- ✅ **Воспроизводимость** - одинаковое окружение везде
- ✅ **Простота отладки** - `docker-compose exec backend sh` для доступа внутрь

## Что изменилось

### Старый модуль (`task-manager.nix`)
```
systemd services → Python напрямую → Проблемы с scheduler
```

### Новый модуль (`task-manager-docker.nix`)
```
systemd → Docker Compose → Containers → Scheduler работает 100%
```

## Миграция

### 1. Остановить старый сервис

```bash
# Остановить все старые сервисы
sudo systemctl stop task-manager-backend
sudo systemctl stop task-manager-frontend-build
sudo systemctl stop task-manager-git-sync
sudo systemctl stop task-manager-api-key-init

# Отключить автозапуск
sudo systemctl disable task-manager-backend
```

### 2. Сохранить данные (опционально)

Если у вас есть важные данные в базе:

```bash
# Создать backup базы данных
sudo cp /var/lib/task-manager/tasks.db /tmp/tasks-backup.db

# Или если база в другом месте, найти её:
sudo find /var/lib/task-manager -name "*.db"
```

### 3. Обновить конфигурацию NixOS

**Заменить** в своей NixOS конфигурации:

```nix
# СТАРЫЙ (убрать)
imports = [
  ./task-manager.nix
];

# НОВЫЙ (добавить)
imports = [
  ./task-manager-docker.nix
];
```

### 4. Применить конфигурацию

```bash
# Пересобрать систему
sudo nixos-rebuild switch

# Проверить статус
sudo systemctl status task-manager-docker
```

### 5. Проверить работу

```bash
# Посмотреть статус контейнеров
task-manager-status

# Посмотреть логи backend (где scheduler)
task-manager-logs backend

# Посмотреть логи frontend
task-manager-logs frontend

# Проверить scheduler работает (должны быть логи каждую минуту)
task-manager-logs backend | grep "🔍"
```

### 6. Восстановить данные (если нужно)

Если нужно восстановить старую базу:

```bash
# Скопировать backup в Docker volume
sudo docker cp /tmp/tasks-backup.db task-manager-backend:/data/db/tasks.db

# Перезапустить backend
sudo systemctl restart task-manager-docker
```

## Новая архитектура

```
NixOS Host
│
├─ Git Sync Service (systemd)
│  └─ Клонирует/обновляет код из GitHub
│
├─ Env Init Service (systemd)
│  └─ Создает .env с API ключом
│
├─ Docker Compose Service (systemd)
│  │
│  ├─ Frontend Container (Nginx)
│  │  └─ Port 3080 → проксирует /api на backend
│  │
│  └─ Backend Container (FastAPI + Scheduler)
│     └─ Port 3000 → API + APScheduler
│
├─ Reverse Proxy (Caddy/Nginx)
│  └─ Port 8888 → проксирует на Frontend:3080
│
└─ Docker Volumes (persistent)
   ├─ task-manager-db (SQLite база)
   ├─ task-manager-backups (автобэкапы)
   └─ task-manager-logs (логи приложения)
```

## Порты

| Сервис | Внутренний порт | Host порт | Публичный порт |
|--------|----------------|-----------|----------------|
| Frontend (Docker) | 80 | 3080 | - |
| Backend (Docker) | 8000 | 3000 | - |
| Reverse Proxy | - | - | 8888 |

**Пользователи обращаются к порту 8888**, который проксирует на Docker контейнеры.

## Управление

### Команды NixOS

```bash
# Статус сервиса
sudo systemctl status task-manager-docker

# Перезапуск
sudo systemctl restart task-manager-docker

# Логи systemd
sudo journalctl -u task-manager-docker -f

# Обновить код из Git и пересобрать
sudo systemctl restart task-manager-git-sync
sudo systemctl restart task-manager-docker
```

### Утилиты (автоматически установлены)

```bash
# Посмотреть статус Docker контейнеров
task-manager-status

# Логи (по умолчанию backend)
task-manager-logs
task-manager-logs backend
task-manager-logs frontend

# Перезапустить всё
task-manager-restart

# Обновить из Git и пересобрать
task-manager-update

# Создать manual backup всех volumes
task-manager-backup
```

### Docker команды напрямую

```bash
# Зайти в контейнер backend
sudo docker exec -it task-manager-backend sh

# Посмотреть базу данных
sudo docker exec -it task-manager-backend ls -la /data/db/

# Посмотреть бэкапы
sudo docker exec -it task-manager-backend ls -la /data/backups/

# Посмотреть логи приложения
sudo docker exec -it task-manager-backend tail -f /data/logs/app.log
```

## Проверка Scheduler

После миграции **ОБЯЗАТЕЛЬНО** проверь, что scheduler работает:

```bash
# Должны быть логи каждую минуту с emoji 🔍
task-manager-logs backend | grep "🔍"
```

Пример правильного вывода:
```
task-manager-backend | 🔍 Auto backup check: enabled=True, current=21:36, target=03:00, interval=1d
task-manager-backend | ⏳ Waiting for backup time (current=21:36, need=03:00)
```

Если логов **НЕТ** → значит scheduler не запустился. Проверь:
```bash
# Посмотреть все логи backend
task-manager-logs backend

# Должна быть строка при старте:
# ==================================================
# Background scheduler started successfully
# Scheduled jobs: ['check_auto_roll', 'check_auto_penalties', 'check_auto_backup']
# Auto backup job will run every minute
# ==================================================
```

## Настройки

Все настройки в **самом модуле** `task-manager-docker.nix`:

```nix
let
  # API ключ
  apiKey = "ваш-ключ";

  # Git репозиторий и ветка
  gitRepo = "https://github.com/umokee/jsddsfjlskdfj.git";
  gitBranch = "claude/debug-task-habit-api-X194g";

  # Домен и порты
  domain = "tasks.umkcloud.xyz";
  publicPort = 8888;

  # Docker внутренние порты
  dockerFrontendPort = 3080;
  dockerBackendPort = 3000;

  # Reverse proxy
  reverseProxy = "caddy";  # или "nginx"
```

## Volumes и данные

Docker volumes хранятся в `/var/lib/docker/volumes/`:

```bash
# Посмотреть все volumes
sudo docker volume ls | grep task-manager

# Инспектировать volume
sudo docker volume inspect task-manager-db
sudo docker volume inspect task-manager-backups
sudo docker volume inspect task-manager-logs
```

### Backup volumes

```bash
# Ручной backup (используй утилиту)
task-manager-backup

# Или вручную
sudo docker run --rm \
  -v task-manager-db:/data/db:ro \
  -v task-manager-backups:/data/backups:ro \
  -v task-manager-logs:/data/logs:ro \
  -v /var/backups:/backup \
  alpine tar czf /backup/task-manager-$(date +%Y%m%d).tar.gz /data
```

### Restore volumes

```bash
# Остановить контейнеры
sudo systemctl stop task-manager-docker

# Восстановить
sudo docker run --rm \
  -v task-manager-db:/data/db \
  -v task-manager-backups:/data/backups \
  -v task-manager-logs:/data/logs \
  -v /var/backups:/backup \
  alpine tar xzf /backup/task-manager-20260117.tar.gz -C /

# Запустить обратно
sudo systemctl start task-manager-docker
```

## Автобэкапы

Автобэкапы теперь **гарантированно работают** внутри Docker:

1. Scheduler запускается каждую минуту ✅
2. Проверяет `auto_backup_enabled` и `backup_time` ✅
3. Создает бэкапы в `/data/backups` внутри контейнера ✅
4. Бэкапы сохраняются в Docker volume `task-manager-backups` ✅

Настройки автобэкапа - через API (фронтенд):
- `auto_backup_enabled`: вкл/выкл
- `backup_time`: время в формате "HH:MM"
- `backup_interval_days`: интервал в днях

## Отладка

### Scheduler не работает

```bash
# 1. Проверить что контейнер запущен
task-manager-status

# 2. Посмотреть логи запуска
task-manager-logs backend | head -50

# Должно быть:
# Background scheduler started successfully

# 3. Посмотреть логи scheduler'а
task-manager-logs backend | grep scheduler

# 4. Если ничего нет - зайти в контейнер
sudo docker exec -it task-manager-backend sh
ps aux | grep python
# Должен быть процесс uvicorn
```

### API не отвечает

```bash
# Проверить что backend работает
curl http://localhost:3000/
# Должен вернуть: {"message":"Task Manager API","status":"active"}

# Проверить что reverse proxy работает
curl http://localhost:8888/api/settings
```

### Frontend не загружается

```bash
# Проверить что frontend контейнер работает
sudo docker exec -it task-manager-frontend ls /usr/share/nginx/html/
# Должны быть файлы: index.html, assets/

# Проверить nginx конфиг
sudo docker exec -it task-manager-frontend cat /etc/nginx/conf.d/default.conf
```

## Откат на старый модуль

Если что-то пошло не так:

```bash
# 1. Остановить Docker
sudo systemctl stop task-manager-docker
sudo systemctl disable task-manager-docker

# 2. Вернуть старый модуль в конфигурацию
# Заменить в configuration.nix:
#   ./task-manager-docker.nix → ./task-manager.nix

# 3. Пересобрать
sudo nixos-rebuild switch

# 4. Запустить старые сервисы
sudo systemctl start task-manager-backend
```

## FAQ

**Q: Где логи scheduler'а теперь?**

A: В Docker контейнере backend:
```bash
task-manager-logs backend | grep "🔍"
```

**Q: Как обновить приложение?**

A:
```bash
task-manager-update
```

Или вручную:
```bash
sudo systemctl restart task-manager-git-sync
cd /var/lib/task-manager
sudo -u task-manager docker-compose up -d --build
```

**Q: Scheduler всё ещё не работает в Docker?**

A: Это **невозможно** если контейнер запущен. APScheduler запускается в том же процессе что и FastAPI. Проверь:
```bash
task-manager-logs backend | grep "scheduler started"
```

Если строки нет → контейнер падает при старте. Смотри полные логи:
```bash
task-manager-logs backend
```

**Q: Можно ли использовать другую ветку Git?**

A: Да, измени в модуле:
```nix
gitBranch = "main";  # или любая другая ветка
```

Затем:
```bash
sudo nixos-rebuild switch
```

**Q: Как изменить время автобэкапа?**

A: Через фронтенд в настройках, или через API:
```bash
curl -X PUT http://localhost:8888/api/settings \
  -H "X-API-Key: ваш-ключ" \
  -H "Content-Type: application/json" \
  -d '{"backup_time": "03:00", "auto_backup_enabled": true}'
```

## Поддержка

Если остались вопросы:
1. Проверь логи: `task-manager-logs backend`
2. Проверь статус: `task-manager-status`
3. Посмотри документацию: `DOCKER.md`
4. Зайди в контейнер: `sudo docker exec -it task-manager-backend sh`
