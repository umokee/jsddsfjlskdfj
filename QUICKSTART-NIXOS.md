# 🚀 Быстрый старт для NixOS

## Шаг 1: Скопировать модуль к себе

```bash
# Клонировать репо или скопировать файл модуля
cp /path/to/umtask/deployment/nixos-module.nix /путь/к/вашим/модулям/task-manager.nix
```

## Шаг 2: Настроить модуль

Откройте `/путь/к/вашим/модулям/task-manager.nix` и измените настройки в блоке `let`:

```nix
let
  enable = helpers.hasIn "services" "task-manager";

  # ==== НАСТРОЙКИ - ИЗМЕНИТЕ ПОД СЕБЯ ====

  # API ключ - ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ!
  apiKey = "ваш-супер-секретный-ключ";  # <--- ИЗМЕНИТЬ!

  # Git репозиторий (если форкнули)
  gitRepo = "https://github.com/umokee/umtask.git";
  gitBranch = "claude/task-manager-fastapi-hYjWx";

  # Порты (при необходимости)
  publicPort = 8080;

  # Reverse proxy (caddy, nginx или none)
  reverseProxy = "caddy";

  # Остальные настройки можно оставить по умолчанию
  # ...
```

## Шаг 3: Импортировать в configuration.nix

```nix
{
  pkgs,
  lib,
  helpers,
  ...
}:

{
  imports = [
    # Ваши существующие импорты...

    # Импорт Task Manager
    ./path/to/task-manager.nix
  ];

  # Добавить в список сервисов
  services = {
    # ... ваши существующие сервисы ...
    task-manager = {};  # <--- просто добавить пустой атрибут
  };
}
```

## Шаг 4: Применить конфигурацию

```bash
sudo nixos-rebuild switch
```

## Шаг 5: Открыть приложение

Откройте браузер: `http://your-server:8080`

Введите API ключ который вы указали в модуле (строка 17).

## Готово! 🎉

---

## Альтернативный способ активации

Если у вас есть `helpers.hasIn`, можете активировать просто добавив в список:

```nix
services = {
  nginx = {};
  postgresql = {};
  task-manager = {};  # <--- просто добавить
};
```

Модуль автоматически включится.

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
# Health check
curl http://localhost:8080/

# С аутентификацией
curl -H "X-API-Key: ваш-ключ" http://localhost:8080/api/stats
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

## Изменить API ключ

1. Изменить в модуле (`task-manager.nix` строка 17)
2. Пересобрать конфиг:
   ```bash
   sudo nixos-rebuild switch
   ```
3. Перезапустить backend:
   ```bash
   sudo systemctl restart task-manager-api-key-init
   sudo systemctl restart task-manager-backend
   ```

---

## Настройки в модуле

Все настройки в блоке `let` модуля:

```nix
# API ключ (ОБЯЗАТЕЛЬНО ИЗМЕНИТЬ!)
apiKey = "your-super-secret-api-key-change-me";

# Git репозиторий и ветка
gitRepo = "https://github.com/umokee/umtask.git";
gitBranch = "claude/task-manager-fastapi-hYjWx";

# Порты
publicPort = 8080;      # Публичный порт приложения
backendPort = 8000;     # Backend (внутренний)
backendHost = "127.0.0.1";

# Пути (обычно не нужно менять)
projectPath = "/var/lib/task-manager";
secretsDir = "/var/lib/task-manager-secrets";
logDir = "/var/log/task-manager";

# Reverse proxy
reverseProxy = "caddy";  # "caddy", "nginx" или "none"

# Fail2ban
enableFail2ban = true;
fail2banMaxRetry = 2;
fail2banFindTime = "1d";
fail2banBanTime = "52w";

# Пользователь (обычно не нужно менять)
user = "task-manager";
group = "task-manager";
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

### Frontend не собирается

Проверить логи сборки:
```bash
journalctl -u task-manager-frontend-build -n 100
```

### API ключ не работает

Убедитесь что:
1. Вы изменили `apiKey` в модуле (строка 17)
2. Пересобрали конфиг (`nixos-rebuild switch`)
3. Перезапустили сервисы

Проверить какой ключ используется:
```bash
sudo cat /var/lib/task-manager-secrets/api-key
```

---

## Интеграция с существующим fail2ban

Если у вас уже настроен fail2ban, установите в модуле:

```nix
enableFail2ban = false;
```

И добавьте в ваш существующий fail2ban конфиг:

```nix
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

## Полная документация

См. [`deployment/NIXOS-SETUP.md`](deployment/NIXOS-SETUP.md) для подробной информации.
