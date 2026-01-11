# NixOS Автоматизированный Деплой

Полностью автоматизированный модуль для деплоя Task Manager на NixOS.

## Что делает модуль автоматически

1. ✅ Клонирует репозиторий из Git
2. ✅ Генерирует случайный API ключ (если его нет)
3. ✅ Собирает React фронтенд (npm install + npm run build)
4. ✅ Запускает FastAPI backend через systemd
5. ✅ Настраивает reverse proxy (Caddy или Nginx)
6. ✅ Интегрируется с fail2ban
7. ✅ Автоматически открывает нужные порты
8. ✅ Создает пользователя и группу
9. ✅ Настраивает логирование

## Минимальная конфигурация

Добавьте в ваш `configuration.nix`:

```nix
{ config, pkgs, ... }:

{
  # Импортировать модуль
  imports = [
    /путь/к/umtask/deployment/nixos-module.nix
  ];

  # Включить Task Manager
  services.task-manager = {
    enable = true;
  };
}
```

**ВСЁ!** После `nixos-rebuild switch` приложение будет доступно на `http://your-server:8080`

## Полная конфигурация с настройками

```nix
{ config, pkgs, ... }:

{
  imports = [
    /путь/к/umtask/deployment/nixos-module.nix
  ];

  services.task-manager = {
    enable = true;

    # Git настройки
    gitRepo = "https://github.com/umokee/umtask.git";
    gitBranch = "claude/task-manager-fastapi-hYjWx";

    # Порты
    publicPort = 8080;      # Публичный порт (фронтенд + API)
    port = 8000;            # Backend (внутренний)
    host = "127.0.0.1";     # Backend слушает только локально

    # Пути
    dataDir = "/var/lib/task-manager";          # Код и БД
    secretsDir = "/var/lib/task-manager-secrets";  # API ключ
    logDir = "/var/log/task-manager";           # Логи

    # Reverse proxy (caddy, nginx, или none)
    reverseProxy = "caddy";

    # Fail2ban защита
    enableFail2ban = true;
    fail2banMaxRetry = 2;     # Попыток до бана
    fail2banFindTime = "1d";   # За какой период
    fail2banBanTime = "52w";   # Длительность бана

    # Пользователь
    user = "task-manager";
    group = "task-manager";
  };
}
```

## Что нужно изменить для вашей установки

### 1. Путь к модулю

**Найти:** Путь где у вас лежит репозиторий umtask

**Способ 1 - Локальный путь:**
```nix
imports = [
  /home/username/umtask/deployment/nixos-module.nix
];
```

**Способ 2 - Через fetchGit (рекомендуется):**
```nix
imports = [
  (builtins.fetchGit {
    url = "https://github.com/umokee/umtask.git";
    ref = "claude/task-manager-fastapi-hYjWx";
  } + "/deployment/nixos-module.nix")
];
```

### 2. Git репозиторий и ветка (если форкнули)

По умолчанию:
```nix
gitRepo = "https://github.com/umokee/umtask.git";
gitBranch = "claude/task-manager-fastapi-hYjWx";
```

Если ваш форк:
```nix
gitRepo = "https://github.com/YOUR_USERNAME/umtask.git";
gitBranch = "main";  # или ваша ветка
```

### 3. Публичный порт

По умолчанию `8080`. Если нужен другой:
```nix
publicPort = 3000;  # или любой другой
```

### 4. Reverse Proxy

Выберите `caddy`, `nginx` или `none`:
```nix
reverseProxy = "caddy";  # Рекомендуется Caddy (проще)
# reverseProxy = "nginx";  # Или Nginx
# reverseProxy = "none";   # Без прокси (только backend на :8000)
```

## Как узнать сгенерированный API ключ

После деплоя API ключ хранится в:
```
/var/lib/task-manager-secrets/api-key
```

Прочитать его:
```bash
sudo cat /var/lib/task-manager-secrets/api-key
```

Вывод будет:
```
TASK_MANAGER_API_KEY=ваш_случайный_ключ_здесь
```

**Скопируйте ключ** и используйте его в веб-интерфейсе или API запросах.

## Структура сервисов

После деплоя у вас будут 4 systemd сервиса:

1. **task-manager-git-sync.service** - синхронизация кода из Git
2. **task-manager-api-key-init.service** - генерация API ключа
3. **task-manager-frontend-build.service** - сборка фронтенда
4. **task-manager-backend.service** - основной backend сервис

Проверка статуса:
```bash
systemctl status task-manager-backend
systemctl status task-manager-frontend-build
systemctl status task-manager-git-sync
```

Логи:
```bash
journalctl -u task-manager-backend -f
journalctl -u task-manager-frontend-build
```

## Обновление приложения

Просто перезапустите git-sync сервис:
```bash
sudo systemctl restart task-manager-git-sync
sudo systemctl restart task-manager-frontend-build
sudo systemctl restart task-manager-backend
```

Или все сразу:
```bash
sudo systemctl restart task-manager-*
```

## Интеграция с вашим существующим fail2ban

Если у вас уже настроен fail2ban (как в вашем примере), добавьте:

```nix
services.task-manager = {
  enable = true;
  enableFail2ban = false;  # Отключить автоматическую интеграцию
  # ... остальные настройки
};

# Ваш существующий fail2ban
services.fail2ban = {
  enable = true;

  # ... ваши настройки ...

  jails = {
    # ... ваши существующие jails ...

    # Добавить Task Manager
    task-manager-api = {
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
  };
};

# Фильтр для fail2ban
environment.etc."fail2ban/filter.d/task-manager-api.conf".text = ''
  [Definition]
  failregex = ^.*Invalid API key attempt from <HOST>.*$
  ignoreregex =
'';
```

## Пример использования в вашем стиле

Основываясь на вашем примере с `cassettes-site`, вот аналогичная конфигурация:

```nix
{
  pkgs,
  lib,
  conf,
  helpers,
  ...
}:

let
  enable = helpers.hasIn "services" "task-manager";
in
{
  imports = [
    (builtins.fetchGit {
      url = "https://github.com/umokee/umtask.git";
      ref = "claude/task-manager-fastapi-hYjWx";
    } + "/deployment/nixos-module.nix")
  ];

  config = lib.mkIf enable {
    services.task-manager = {
      enable = true;
      publicPort = 8080;
      reverseProxy = "caddy";
      enableFail2ban = false;  # Используем ваш существующий fail2ban
    };

    # Добавить в ваш существующий fail2ban
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
  };
}
```

## Проверка работы

### 1. Приложение доступно
```bash
curl http://localhost:8080/
# Должно вернуть: {"message":"Task Manager API","status":"active"}
```

### 2. API работает (с ключом)
```bash
API_KEY=$(sudo cat /var/lib/task-manager-secrets/api-key | cut -d= -f2)
curl -H "X-API-Key: $API_KEY" http://localhost:8080/api/stats
```

### 3. Фронтенд собран
```bash
ls -la /var/lib/task-manager/frontend/dist/
```

### 4. Fail2ban активен
```bash
fail2ban-client status task-manager-api
```

## Troubleshooting

### Frontend не собирается
Проверьте логи:
```bash
journalctl -u task-manager-frontend-build -n 50
```

### Backend не запускается
Проверьте:
```bash
journalctl -u task-manager-backend -n 50
```

### API ключ не найден
Регенерировать:
```bash
sudo rm /var/lib/task-manager-secrets/api-key
sudo systemctl restart task-manager-api-key-init
sudo cat /var/lib/task-manager-secrets/api-key
```

### Git sync не работает
```bash
journalctl -u task-manager-git-sync -n 50
```

## Безопасность

1. **API ключ:** Автоматически генерируется случайный 32-байтный ключ
2. **Fail2ban:** Бан после 2 неудачных попыток
3. **Firewall:** Открыт только publicPort
4. **Пользователь:** Приложение работает от непривилегированного пользователя
5. **Права:** Секреты с правами 0600, логи 0750
6. **Security hardening:** NoNewPrivileges, PrivateTmp, ProtectSystem

## Дополнительно

### Сменить API ключ на кастомный

Если хотите свой ключ вместо случайного:

```bash
# Остановить backend
sudo systemctl stop task-manager-backend

# Установить свой ключ
echo "TASK_MANAGER_API_KEY=my-super-secret-key" | \
  sudo tee /var/lib/task-manager-secrets/api-key

# Выставить права
sudo chmod 600 /var/lib/task-manager-secrets/api-key
sudo chown task-manager:task-manager /var/lib/task-manager-secrets/api-key

# Запустить backend
sudo systemctl start task-manager-backend
```

### Использовать HTTPS

Рекомендуется добавить Caddy с автоматическими сертификатами:

```nix
services.caddy.virtualHosts."tasks.yourdomain.com" = {
  extraConfig = ''
    reverse_proxy localhost:8080
  '';
};
```

Или настроить Nginx с Let's Encrypt.
