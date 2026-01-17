# NixOS Deployment Modules

Эта директория содержит модули для развертывания Task Manager на NixOS.

## Рекомендуемый модуль (Docker) ⭐

**`task-manager-docker.nix`** - Используй этот модуль для production!

### Преимущества Docker-деплоя:
- ✅ **Scheduler работает 100%** - гарантированно запускается с приложением
- ✅ **Простая отладка** - все логи видны через `docker-compose logs`
- ✅ **Изолированное окружение** - нет конфликтов зависимостей
- ✅ **Автоматический restart** - Docker перезапускает при падении
- ✅ **Воспроизводимость** - одинаково работает везде
- ✅ **Удобные утилиты** - `task-manager-logs`, `task-manager-status` и др.

### Быстрый старт:

1. Импортируй модуль в `configuration.nix`:
```nix
imports = [
  ./path/to/deployment/task-manager-docker.nix
];
```

2. Настрой параметры в `task-manager-docker.nix`:
```nix
let
  apiKey = "твой-секретный-ключ";  # Сгенерируй через: openssl rand -hex 32
  gitBranch = "main";  # или другая ветка
  publicPort = 8888;
  reverseProxy = "caddy";  # или "nginx"
in
```

3. Примени конфигурацию:
```bash
sudo nixos-rebuild switch
```

4. Проверь работу:
```bash
task-manager-status
task-manager-logs backend
```

### Документация:
- **NIXOS-DOCKER-MIGRATION.md** - Полное руководство по миграции
- **../DOCKER.md** - Docker документация

---

## Альтернативный модуль (Legacy)

**`nixos-module.nix`** - Старый модуль без Docker

⚠️ **Не рекомендуется** - имеет проблемы с scheduler'ом!

### Проблемы:
- ❌ Scheduler может не запускаться
- ❌ Логи теряются из-за конфликта logging config
- ❌ Сложная отладка
- ❌ Зависимости могут конфликтовать

Используй только если Docker невозможен по каким-то причинам.

---

## Другие файлы

- **caddy-sni-router.nix** - SNI роутер для множественных доменов
- **systemd-service.example** - Пример systemd сервиса
- **FAIL2BAN.md** - Настройка fail2ban
- **NIXOS-SETUP.md** - Общая инструкция по NixOS
- **NIXOS-UPDATE.md** - Как обновлять приложение

---

## Утилиты (автоматически устанавливаются с Docker-модулем)

После установки `task-manager-docker.nix` доступны команды:

```bash
# Посмотреть статус
task-manager-status

# Логи (backend по умолчанию)
task-manager-logs
task-manager-logs backend
task-manager-logs frontend

# Перезапустить
task-manager-restart

# Обновить из Git
task-manager-update

# Создать backup volumes
task-manager-backup
```

---

## Архитектура

### Docker-деплой (`task-manager-docker.nix`)

```
NixOS Host
│
├─ systemd: task-manager-git-sync
│  └─ Клонирует код из GitHub
│
├─ systemd: task-manager-env-init
│  └─ Создает .env файл
│
├─ systemd: task-manager-docker
│  └─ Запускает docker-compose
│     │
│     ├─ Container: Frontend (Nginx)
│     │  └─ Port 3080
│     │
│     └─ Container: Backend (FastAPI + Scheduler)
│        └─ Port 3000
│
├─ Reverse Proxy (Caddy/Nginx)
│  └─ Port 8888 → Frontend:3080
│
└─ Docker Volumes
   ├─ task-manager-db
   ├─ task-manager-backups
   └─ task-manager-logs
```

### Legacy-деплой (`nixos-module.nix`)

```
NixOS Host
│
├─ systemd: task-manager-git-sync
│
├─ systemd: task-manager-frontend-build
│  └─ npm build
│
├─ systemd: task-manager-backend
│  └─ Python uvicorn (⚠️ scheduler может не работать)
│
└─ Reverse Proxy
   └─ Port 8888
```

---

## Выбор модуля

| Критерий | Docker | Legacy |
|----------|--------|--------|
| Scheduler работает | ✅ 100% | ⚠️ Нестабильно |
| Простота отладки | ✅ Легко | ❌ Сложно |
| Логирование | ✅ Видно всё | ⚠️ Теряются |
| Изоляция | ✅ Полная | ❌ Нет |
| Требует Docker | ❌ Да | ✅ Нет |

**Рекомендация:** Используй **`task-manager-docker.nix`** если только нет жестких ограничений на Docker.

---

## Поддержка

Проблемы или вопросы?

1. Проверь логи: `task-manager-logs backend`
2. Посмотри статус: `task-manager-status`
3. Читай документацию: **NIXOS-DOCKER-MIGRATION.md**
4. Проверь GitHub Issues: https://github.com/umokee/jsddsfjlskdfj/issues
