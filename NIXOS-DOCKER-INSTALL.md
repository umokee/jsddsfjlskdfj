# 🚀 NixOS Docker - Автоматическая Установка

Полностью автоматизированный деплой Task Manager на NixOS через Docker.

**Всё делается автоматически:**
- ✅ Клонирование из Git
- ✅ Сборка Docker контейнеров
- ✅ Автозапуск при загрузке системы
- ✅ Обновление одной командой
- ✅ Автоматическое обновление по расписанию (опционально)

## Быстрая Установка

### Шаг 1: Скопировать и настроить модуль

```bash
# Скопировать модуль в /etc/nixos/
sudo cp deployment/nixos-docker-module.nix /etc/nixos/task-manager-docker.nix

# Отредактировать настройки в модуле
sudo nano /etc/nixos/task-manager-docker.nix
```

В файле `task-manager-docker.nix` измените настройки в секции `let`:

```nix
let
  # Включить сервис (true/false)
  enable = true;

  # API ключ - ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ!
  apiKey = "ваш-супер-секретный-ключ-измените-меня";

  # Git репозиторий
  gitRepo = "https://github.com/umokee/jsddsfjlskdfj.git";
  gitBranch = "main";  # или ваша ветка

  # Порты
  publicPort = 8080;  # 443 занят VPN

  # Автообновление (true/false)
  autoUpdate = false;  # true для включения

  # Остальные настройки можно не менять
```

### Шаг 2: Добавить в configuration.nix

Отредактируйте `/etc/nixos/configuration.nix`:

```nix
{ config, pkgs, ... }:

{
  imports = [
    ./hardware-configuration.nix
    ./task-manager-docker.nix  # <-- Добавить эту строку
  ];

  # Остальная конфигурация...
}
```

### Шаг 3: Применить конфигурацию

```bash
# Пересобрать систему
sudo nixos-rebuild switch

# Готово! Приложение запустится автоматически
```

### Шаг 4: Открыть приложение

```
http://localhost:8080
```

Введите API ключ из конфигурации.

## 🔄 Обновление

### Вариант 1: Команда (Рекомендуется)

После установки доступна команда `task-manager-update`:

```bash
# Обновить до последней версии из Git
sudo task-manager-update
```

Команда автоматически:
1. Делает `git pull`
2. Пересобирает Docker контейнеры
3. Перезапускает сервис

### Вариант 2: Через systemd

```bash
# Обновить вручную
sudo systemctl restart task-manager-docker-git-sync.service
sudo systemctl restart task-manager-docker-rebuild.service
sudo systemctl restart task-manager-docker.service
```

### Вариант 3: Автоматическое обновление

Включите в `configuration.nix`:

```nix
services.task-manager-docker = {
  enable = true;
  autoUpdate = true;  # <-- Включить автообновление
  # ... остальные настройки
};
```

Пересоберите:

```bash
sudo nixos-rebuild switch
```

Теперь каждый день в 3:00 будет автоматическое обновление из Git.

## 📊 Управление

### Статус сервиса

```bash
# Проверить статус
sudo systemctl status task-manager-docker.service

# Проверить логи
sudo journalctl -u task-manager-docker.service -f

# Проверить статус контейнеров
sudo docker ps
```

### Перезапуск

```bash
# Перезапустить сервис
sudo systemctl restart task-manager-docker.service

# Или через docker-compose
cd /var/lib/task-manager-docker
sudo docker-compose restart
```

### Остановка

```bash
# Остановить сервис
sudo systemctl stop task-manager-docker.service

# Отключить автозапуск
sudo systemctl disable task-manager-docker.service
```

### Логи Docker

```bash
# Все логи
cd /var/lib/task-manager-docker
sudo docker-compose logs

# Следить в реальном времени
sudo docker-compose logs -f

# Только backend
sudo docker-compose logs backend

# Только frontend
sudo docker-compose logs frontend
```

## 🔧 Настройки

Все настройки находятся в модуле `/etc/nixos/task-manager-docker.nix` в секции `let`:

```nix
let
  # Включить сервис (true/false)
  enable = true;

  # API ключ - ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ!
  apiKey = "your-super-secret-api-key-change-me";

  # Git репозиторий
  gitRepo = "https://github.com/umokee/jsddsfjlskdfj.git";
  gitBranch = "main";

  # Порты
  publicPort = 8080;  # Публичный порт (443 занят VPN)

  # Пути
  projectPath = "/var/lib/task-manager-docker";
  secretsDir = "/var/lib/task-manager-secrets";

  # Пользователь
  user = "task-manager";
  group = "task-manager";

  # Автообновление (true/false)
  autoUpdate = false;  # true для включения
```

После изменения настроек:

```bash
sudo nixos-rebuild switch
```

## 🔐 Безопасность

### Изменить API ключ

1. Сгенерировать новый ключ:

```bash
openssl rand -hex 32
```

2. Обновить в `/etc/nixos/task-manager-docker.nix`:

```nix
let
  apiKey = "новый-ключ-сюда";
  # ...
```

3. Применить:

```bash
sudo nixos-rebuild switch
```

### Fail2ban (опционально)

Добавьте в `configuration.nix`:

```nix
services.fail2ban = {
  enable = true;

  jails.task-manager-api = {
    settings = {
      enabled = true;
      filter = "task-manager-api";
      logpath = "/var/lib/task-manager-docker/logs/app.log";
      maxretry = 2;
      findtime = "1d";
      bantime = "52w";
      action = "iptables-allports";
    };
  };
};

environment.etc."fail2ban/filter.d/task-manager-api.conf".text = ''
  [Definition]
  failregex = ^.*Invalid API key attempt from <HOST>.*$
  ignoreregex =
'';
```

## 🌐 Внешний Доступ

### Вариант 1: Caddy (HTTPS автоматически)

Добавьте в `configuration.nix`:

```nix
services.caddy = {
  enable = true;

  virtualHosts."tasks.yourdomain.com" = {
    extraConfig = ''
      reverse_proxy localhost:8080
    '';
  };
};

# Открыть порты для HTTPS
networking.firewall.allowedTCPPorts = [ 80 443 ];
```

### Вариант 2: Nginx

```nix
services.nginx = {
  enable = true;

  virtualHosts."tasks.yourdomain.com" = {
    forceSSL = true;
    enableACME = true;

    locations."/" = {
      proxyPass = "http://localhost:8080";
      proxyWebsockets = true;
    };
  };
};

security.acme = {
  acceptTerms = true;
  defaults.email = "your-email@example.com";
};

networking.firewall.allowedTCPPorts = [ 80 443 ];
```

### Вариант 3: Tailscale (Рекомендуется для личного использования)

```nix
services.tailscale.enable = true;

# После установки:
# sudo tailscale up
# Теперь доступ через: http://nixos-hostname:8080
```

## 📁 Структура файлов

```
/var/lib/task-manager-docker/
├── .git/                    # Git репозиторий
├── .env                     # Environment переменные (AUTO)
├── docker-compose.yml       # Docker Compose конфигурация
├── backend/                 # Backend код
│   └── Dockerfile
├── frontend/                # Frontend код
│   └── Dockerfile
├── data/                    # SQLite база данных (persistent)
│   └── task_manager.db
└── logs/                    # Логи приложения (persistent)
    └── app.log

/var/lib/task-manager-secrets/
└── (empty, зарезервировано для будущих секретов)
```

## 🐛 Troubleshooting

### Сервис не стартует

```bash
# Проверить статус всех компонентов
sudo systemctl status task-manager-docker-git-sync.service
sudo systemctl status task-manager-docker-env-setup.service
sudo systemctl status task-manager-docker-rebuild.service
sudo systemctl status task-manager-docker.service

# Проверить логи
sudo journalctl -u task-manager-docker.service -n 50
```

### Порт занят

Если порт 8080 занят, измените в `configuration.nix`:

```nix
services.task-manager-docker.publicPort = 8081;
```

И пересоберите:

```bash
sudo nixos-rebuild switch
```

### Docker ошибки

```bash
# Проверить Docker
sudo systemctl status docker.service

# Проверить пользователя
sudo groups task-manager
# Должно быть: task-manager docker

# Пересоздать контейнеры
cd /var/lib/task-manager-docker
sudo docker-compose down
sudo docker-compose up -d --build
```

### Git ошибки

```bash
# Проверить репозиторий
cd /var/lib/task-manager-docker
sudo -u task-manager git status
sudo -u task-manager git log -1

# Переклонировать
sudo rm -rf /var/lib/task-manager-docker/*
sudo systemctl restart task-manager-docker-git-sync.service
```

### База данных повреждена

```bash
# Остановить сервис
sudo systemctl stop task-manager-docker.service

# Бэкапы находятся в
ls -la /var/lib/task-manager-docker/data/backups/

# Восстановить из бэкапа
cd /var/lib/task-manager-docker/data
sudo cp task_manager.db task_manager.db.broken
sudo cp backups/task_manager_backup_YYYYMMDD_HHMMSS.db task_manager.db

# Запустить снова
sudo systemctl start task-manager-docker.service
```

## 📋 Примеры использования

### Полная установка с нуля

```bash
# 1. Скопировать модуль
sudo cp deployment/nixos-docker-module.nix /etc/nixos/

# 2. Отредактировать configuration.nix
sudo nano /etc/nixos/configuration.nix

# Добавить:
# imports = [ ./task-manager-docker.nix ];
# services.task-manager-docker.enable = true;
# services.task-manager-docker.apiKey = "ваш-ключ";

# 3. Применить
sudo nixos-rebuild switch

# 4. Проверить
curl http://localhost:8080
```

### Обновление до новой версии

```bash
# Обновить одной командой
sudo task-manager-update

# Проверить версию
cd /var/lib/task-manager-docker
sudo -u task-manager git log -1
```

### Смена ветки Git

Отредактируйте `/etc/nixos/task-manager-docker.nix`:

```nix
let
  gitBranch = "develop";  # <-- Измените здесь
  # ...
```

```bash
# Применить
sudo nixos-rebuild switch

# Git sync автоматически переключится на новую ветку
```

### Переключение на другой порт

Отредактируйте `/etc/nixos/task-manager-docker.nix`:

```nix
let
  publicPort = 9000;  # <-- Измените здесь
  # ...
```

```bash
sudo nixos-rebuild switch
# Теперь доступ: http://localhost:9000
```

## 🎯 Что происходит при загрузке

NixOS автоматически:

1. **task-manager-docker-git-sync.service**
   - Клонирует репозиторий (или делает git pull)
   - Переключается на нужную ветку

2. **task-manager-docker-env-setup.service**
   - Создаёт `.env` файл с вашими настройками
   - Создаёт директории для данных и логов

3. **task-manager-docker-rebuild.service**
   - Собирает Docker контейнеры (`docker-compose build`)

4. **task-manager-docker.service**
   - Запускает контейнеры (`docker-compose up -d`)

Всё происходит автоматически при каждой загрузке!

## ⚡ Команды для копирования

```bash
# Установка
sudo cp deployment/nixos-docker-module.nix /etc/nixos/
sudo nano /etc/nixos/configuration.nix  # Добавить imports и настройки
sudo nixos-rebuild switch

# Управление
sudo systemctl status task-manager-docker
sudo systemctl restart task-manager-docker
sudo journalctl -u task-manager-docker -f

# Обновление
sudo task-manager-update

# Логи
cd /var/lib/task-manager-docker
sudo docker-compose logs -f

# Проверка
curl http://localhost:8080
```

## 💡 Рекомендации

1. **Обязательно измените API ключ** - не используйте дефолтный
2. **Включите Tailscale** для безопасного удалённого доступа
3. **Настройте бэкапы** через Settings UI в приложении
4. **Используйте автообновление** если хотите всегда быть на последней версии
5. **Мониторьте логи** первое время: `sudo journalctl -u task-manager-docker -f`

## 🆘 Поддержка

Если что-то не работает:

1. Проверьте логи: `sudo journalctl -u task-manager-docker.service -n 100`
2. Проверьте Docker: `sudo docker ps`
3. Проверьте файлы: `ls -la /var/lib/task-manager-docker/`
4. Создайте issue на GitHub с выводом команд выше

## 📚 Дополнительные ресурсы

- [Docker Setup](DOCKER-SETUP.md) - Подробности о Docker конфигурации
- [NixOS Docker Wiki](https://nixos.wiki/wiki/Docker)
- [README.md](README.md) - Основная документация проекта
