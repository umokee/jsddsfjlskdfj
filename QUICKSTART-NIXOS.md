# 🚀 Быстрый старт для NixOS

## Шаг 1: Добавить в configuration.nix

```nix
{ config, pkgs, ... }:

{
  imports = [
    # Ваши существующие импорты...

    # Импорт модуля Task Manager (выберите один из вариантов)

    # ВАРИАНТ 1: Локальный путь (если склонировали репо)
    /home/username/umtask/deployment/nixos-module.nix

    # ВАРИАНТ 2: Напрямую из GitHub (рекомендуется)
    # (builtins.fetchGit {
    #   url = "https://github.com/umokee/umtask.git";
    #   ref = "claude/task-manager-fastapi-hYjWx";
    # } + "/deployment/nixos-module.nix")
  ];

  # Включить Task Manager
  services.task-manager = {
    enable = true;
  };
}
```

## Шаг 2: Применить конфигурацию

```bash
sudo nixos-rebuild switch
```

## Шаг 3: Получить API ключ

```bash
sudo cat /var/lib/task-manager-secrets/api-key
```

Скопируйте значение после `TASK_MANAGER_API_KEY=`

## Шаг 4: Открыть приложение

Откройте браузер: `http://your-server:8080`

Введите API ключ из шага 3.

## Готово! 🎉

---

## Дополнительные настройки (опционально)

### Изменить порт

```nix
services.task-manager = {
  enable = true;
  publicPort = 3000;  # вместо 8080
};
```

### Использовать Nginx вместо Caddy

```nix
services.task-manager = {
  enable = true;
  reverseProxy = "nginx";  # вместо "caddy"
};
```

### Интеграция с существующим fail2ban

Если у вас уже настроен fail2ban:

```nix
services.task-manager = {
  enable = true;
  enableFail2ban = false;  # отключить автоматическую интеграцию
};

# Добавить в ваш существующий fail2ban конфиг
environment.etc."fail2ban/filter.d/task-manager-api.conf".text = ''
  [Definition]
  failregex = ^.*Invalid API key attempt from <HOST>.*$
  ignoreregex =
'';

services.fail2ban.jails.task-manager-api = {
  settings = {
    enabled = true;
    filter = "task-manager-api";
    logpath = "/var/log/task-manager/app.log";
    action = "iptables-allports";
    maxretry = 2;
    findtime = "1d";
    bantime = "52w";
  };
};
```

---

## Проверка работы

### Статус сервисов

```bash
systemctl status task-manager-backend
systemctl status task-manager-frontend-build
systemctl status task-manager-git-sync
```

### Логи

```bash
# Backend
journalctl -u task-manager-backend -f

# Frontend build
journalctl -u task-manager-frontend-build

# Git sync
journalctl -u task-manager-git-sync
```

### Тест API

```bash
API_KEY=$(sudo cat /var/lib/task-manager-secrets/api-key | cut -d= -f2)

# Health check
curl http://localhost:8080/

# С аутентификацией
curl -H "X-API-Key: $API_KEY" http://localhost:8080/api/stats
```

---

## Обновление приложения

```bash
sudo systemctl restart task-manager-git-sync
sudo systemctl restart task-manager-frontend-build
sudo systemctl restart task-manager-backend
```

Или все сразу:

```bash
sudo systemctl restart task-manager-*
```

---

## Troubleshooting

### Приложение не открывается

1. Проверить статус backend:
   ```bash
   systemctl status task-manager-backend
   ```

2. Проверить логи:
   ```bash
   journalctl -u task-manager-backend -n 50
   ```

3. Проверить порт открыт:
   ```bash
   ss -tlnp | grep 8080
   ```

### API ключ не найден

Регенерировать:
```bash
sudo rm /var/lib/task-manager-secrets/api-key
sudo systemctl restart task-manager-api-key-init
sudo cat /var/lib/task-manager-secrets/api-key
```

### Frontend не собирается

Проверить логи сборки:
```bash
journalctl -u task-manager-frontend-build -n 100
```

---

## Полная документация

См. [`deployment/NIXOS-SETUP.md`](deployment/NIXOS-SETUP.md) для подробной информации.
