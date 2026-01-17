# 🐳 Docker Setup для Task Manager

Полная инструкция по запуску Task Manager в Docker контейнере, особенно для NixOS.

## Быстрый старт

### 1. Подготовка

```bash
# Клонировать репозиторий (если ещё не сделали)
git clone https://github.com/umokee/umtask.git
cd umtask

# Создать .env файл
cp .env.docker .env

# Сгенерировать безопасный API ключ
openssl rand -hex 32
```

### 2. Настройка .env

Откройте файл `.env` и измените:

```env
# Установите свой API ключ
TASK_MANAGER_API_KEY=ваш-сгенерированный-ключ

# Порт для доступа (443 занят VPN, используем 8080)
PUBLIC_PORT=8080
```

### 3. Запуск

```bash
# Собрать и запустить контейнеры
docker-compose up -d

# Проверить статус
docker-compose ps

# Посмотреть логи
docker-compose logs -f
```

### 4. Открыть приложение

Откройте браузер: `http://localhost:8080`

Введите API ключ из `.env` файла.

## Архитектура

```
┌─────────────────────────────────────┐
│     Host Machine (NixOS)            │
│                                     │
│  Port 8080 (настраиваемый)         │
│         ↓                           │
│  ┌──────────────────────┐          │
│  │  Frontend (Nginx)    │          │
│  │  - Статические файлы │          │
│  │  - Proxy /api/*      │          │
│  └──────────┬───────────┘          │
│             │                       │
│             ↓                       │
│  ┌──────────────────────┐          │
│  │  Backend (FastAPI)   │          │
│  │  - Port 8000         │          │
│  │  - SQLite DB         │          │
│  └──────────────────────┘          │
│                                     │
│  Volumes:                           │
│  - ./data → /app/data              │
│  - ./logs → /var/log/task-manager  │
└─────────────────────────────────────┘
```

## Установка Docker на NixOS

### Вариант 1: Через configuration.nix (Рекомендуется)

```nix
{ config, pkgs, ... }:

{
  # Включить Docker
  virtualisation.docker = {
    enable = true;
    autoPrune = {
      enable = true;
      dates = "weekly";
    };
  };

  # Добавить пользователя в группу docker
  users.users.ваш-юзер = {
    extraGroups = [ "docker" ];
  };

  # Опционально: docker-compose
  environment.systemPackages = with pkgs; [
    docker-compose
  ];
}
```

Применить конфигурацию:

```bash
sudo nixos-rebuild switch
```

Перелогиньтесь для применения прав группы `docker`.

### Вариант 2: Временно (без rebuild)

```bash
# Запустить Docker сервис
sudo systemctl start docker

# Добавить себя в группу docker
sudo usermod -aG docker $USER

# Перелогиниться
```

## Управление контейнерами

### Запуск

```bash
# Запустить в фоне
docker-compose up -d

# Запустить с пересборкой
docker-compose up -d --build

# Запустить и показать логи
docker-compose up
```

### Остановка

```bash
# Остановить контейнеры
docker-compose stop

# Остановить и удалить контейнеры
docker-compose down

# Остановить и удалить контейнеры + volumes
docker-compose down -v
```

### Логи

```bash
# Все логи
docker-compose logs

# Следить за логами в реальном времени
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs backend
docker-compose logs frontend
```

### Перезапуск

```bash
# Перезапустить все сервисы
docker-compose restart

# Перезапустить конкретный сервис
docker-compose restart backend
```

## Изменение порта

По умолчанию используется порт `8080`, так как `443` занят VPN.

Если `8080` тоже занят, измените в `.env`:

```env
PUBLIC_PORT=8081
```

И перезапустите:

```bash
docker-compose down
docker-compose up -d
```

## Проверка работы

### Health Check

```bash
# Проверить статус контейнеров
docker-compose ps

# Должно быть:
# taskmanager-backend    healthy
# taskmanager-frontend   healthy
```

### API Test

```bash
# Health endpoint
curl http://localhost:8080/

# Статистика (с API ключом)
curl -H "X-API-Key: ваш-ключ" http://localhost:8080/api/stats
```

## Обновление приложения

```bash
# Остановить контейнеры
docker-compose down

# Получить последние изменения
git pull

# Пересобрать и запустить
docker-compose up -d --build
```

## Бэкапы

### База данных

База данных находится в `./data/task_manager.db`.

```bash
# Создать бэкап
cp ./data/task_manager.db ./data/task_manager.db.backup-$(date +%Y%m%d)

# Или использовать встроенную систему бэкапов через API
curl -X POST -H "X-API-Key: ваш-ключ" http://localhost:8080/api/backups/create
```

### Автоматические бэкапы

Бэкапы автоматически создаются согласно настройкам в Settings UI:
- По умолчанию: каждый день в 3:00
- Хранится последние 10 бэкапов
- Папка: `./data/backups/`

## Troubleshooting

### Порт уже занят

Если видите ошибку `bind: address already in use`:

```bash
# Проверить какой процесс использует порт
sudo ss -tlnp | grep 8080

# Изменить порт в .env
PUBLIC_PORT=8081

# Перезапустить
docker-compose down
docker-compose up -d
```

### Контейнер не стартует

```bash
# Посмотреть логи
docker-compose logs backend
docker-compose logs frontend

# Проверить статус
docker-compose ps

# Пересобрать с нуля
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### База данных повреждена

```bash
# Остановить контейнеры
docker-compose down

# Восстановить из бэкапа
cp ./data/task_manager.db.backup-YYYYMMDD ./data/task_manager.db

# Запустить снова
docker-compose up -d
```

### Нет прав на Docker (NixOS)

```bash
# Добавить себя в группу docker
sudo usermod -aG docker $USER

# Перелогиниться
logout

# Или перезагрузить
sudo reboot
```

## Продакшен настройки

### HTTPS с Caddy (Рекомендуется)

Создайте `Caddyfile`:

```
tasks.yourdomain.com {
    reverse_proxy localhost:8080
}
```

Запустите Caddy:

```bash
caddy run
```

### HTTPS с Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name tasks.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### Автозапуск при загрузке (NixOS)

Создайте systemd сервис:

```nix
# /etc/nixos/task-manager-docker.nix
{ config, pkgs, ... }:

{
  systemd.services.task-manager-docker = {
    description = "Task Manager Docker Compose";
    after = [ "docker.service" "network.target" ];
    requires = [ "docker.service" ];

    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = "yes";
      WorkingDirectory = "/path/to/umtask";
      ExecStart = "${pkgs.docker-compose}/bin/docker-compose up -d";
      ExecStop = "${pkgs.docker-compose}/bin/docker-compose down";
      User = "your-user";
    };

    wantedBy = [ "multi-user.target" ];
  };
}
```

Импортируйте в `configuration.nix`:

```nix
imports = [
  ./task-manager-docker.nix
];
```

Примените:

```bash
sudo nixos-rebuild switch
```

## Мониторинг

### Использование ресурсов

```bash
# Статистика контейнеров
docker stats

# Использование диска
docker system df
```

### Очистка

```bash
# Очистить неиспользуемые образы
docker image prune -a

# Очистить всё неиспользуемое
docker system prune -a --volumes
```

## FAQ

### Q: Можно ли использовать другую БД вместо SQLite?

A: Пока приложение использует только SQLite. Для продакшена рекомендуется регулярные бэкапы.

### Q: Как изменить API ключ?

A:
1. Измените в `.env`
2. Перезапустите: `docker-compose restart backend`

### Q: Как получить доступ из локальной сети?

A: Замените `localhost` на IP адрес вашего сервера:
- Узнать IP: `ip addr show`
- Открыть: `http://192.168.1.X:8080`

### Q: Работает ли с Podman?

A: Да! Замените `docker-compose` на `podman-compose`.

## Дополнительные ресурсы

- [Docker на NixOS Wiki](https://nixos.wiki/wiki/Docker)
- [Docker Compose документация](https://docs.docker.com/compose/)
- [Основная документация](README.md)
- [NixOS деплой](QUICKSTART-NIXOS.md)

## Поддержка

Если возникли проблемы, проверьте:
1. Логи: `docker-compose logs -f`
2. Статус: `docker-compose ps`
3. Health checks: все должны быть `healthy`

Для вопросов создайте issue на GitHub.
