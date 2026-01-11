# NixOS Автоматизированный Деплой

Полностью автоматизированный модуль для деплоя Task Manager на NixOS.

**Стиль модуля:** Все настройки через `let in`, без `options`, включается автоматически при импорте.

## Что делает модуль автоматически

1. ✅ Клонирует репозиторий из Git
2. ✅ Записывает ваш API ключ в секретный файл
3. ✅ Собирает React фронтенд (npm install + npm run build)
4. ✅ Запускает FastAPI backend через systemd
5. ✅ Настраивает reverse proxy (Caddy или Nginx)
6. ✅ Интегрируется с fail2ban
7. ✅ Автоматически открывает нужные порты
8. ✅ Создает пользователя и группу
9. ✅ Настраивает логирование

## Установка

### Шаг 1: Скопировать модуль

```bash
# Вариант 1: Скопировать из клонированного репо
cp /path/to/umtask/deployment/nixos-module.nix /etc/nixos/modules/task-manager.nix

# Вариант 2: Скачать напрямую
curl -o /etc/nixos/modules/task-manager.nix \
  https://raw.githubusercontent.com/umokee/umtask/claude/task-manager-fastapi-hYjWx/deployment/nixos-module.nix
```

### Шаг 2: Настроить модуль

Откройте `/etc/nixos/modules/task-manager.nix` и измените настройки в блоке `let`:

```nix
let
  enable = helpers.hasIn "services" "task-manager";

  # ==== НАСТРОЙКИ - ИЗМЕНИТЕ ПОД СЕБЯ ====

  # API ключ - ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ!
  apiKey = "ваш-супер-секретный-api-ключ-здесь";

  # Git репозиторий (если форкнули, измените на свой)
  gitRepo = "https://github.com/umokee/umtask.git";
  gitBranch = "claude/task-manager-fastapi-hYjWx";

  # Порты
  publicPort = 8080;      # Публичный порт (где будет доступно приложение)
  backendPort = 8000;     # Backend (внутренний, не нужно менять)
  backendHost = "127.0.0.1";

  # Пути (обычно не нужно менять)
  projectPath = "/var/lib/task-manager";
  secretsDir = "/var/lib/task-manager-secrets";
  logDir = "/var/log/task-manager";
  apiKeyFile = "${secretsDir}/api-key";
  frontendBuildDir = "${projectPath}/frontend/dist";

  # Reverse proxy: "caddy", "nginx" или "none"
  reverseProxy = "caddy";

  # Fail2ban
  enableFail2ban = true;
  fail2banMaxRetry = 2;
  fail2banFindTime = "1d";
  fail2banBanTime = "52w";

  # Пользователь (обычно не нужно менять)
  user = "task-manager";
  group = "task-manager";

  # ==== КОНЕЦ НАСТРОЕК ====
```

**ВАЖНО:** Обязательно измените `apiKey` на свой секретный ключ!

### Шаг 3: Импортировать в configuration.nix

```nix
{
  pkgs,
  lib,
  helpers,  # Убедитесь что helpers доступны
  ...
}:

{
  imports = [
    # Ваши существующие импорты...
    ./hardware-configuration.nix
    # ...

    # Импорт Task Manager
    ./modules/task-manager.nix
  ];

  # Активировать модуль
  services = {
    # ... ваши существующие сервисы ...
    task-manager = {};  # Просто добавить пустой атрибут
  };
}
```

**Модуль автоматически активируется** когда находит `task-manager` в списке сервисов через `helpers.hasIn`.

### Шаг 4: Применить конфигурацию

```bash
sudo nixos-rebuild switch
```

Модуль автоматически:
1. Создаст пользователя `task-manager`
2. Склонирует репозиторий в `/var/lib/task-manager`
3. Запишет API ключ в `/var/lib/task-manager-secrets/api-key`
4. Соберет фронтенд
5. Запустит backend
6. Настроит Caddy/Nginx
7. Включит fail2ban защиту

### Шаг 5: Готово!

Откройте браузер: `http://your-server:8080`

Введите API ключ который указали в модуле.

## Структура модуля

Модуль создает 4 systemd сервиса:

1. **task-manager-git-sync** - клонирование/обновление кода из Git
2. **task-manager-api-key-init** - запись API ключа в файл
3. **task-manager-frontend-build** - сборка React фронтенда
4. **task-manager-backend** - FastAPI backend

## Настройки модуля

Все настройки в блоке `let` в начале модуля:

### API ключ (ОБЯЗАТЕЛЬНО)

```nix
apiKey = "your-super-secret-api-key-change-me";
```

**ВАЖНО:** Это ваш единственный способ аутентификации. Выберите надежный ключ!

Примеры генерации случайного ключа:
```bash
# 32-байтный base64
openssl rand -base64 32

# UUID
uuidgen

# 64 hex символа
openssl rand -hex 32
```

### Git настройки

```nix
gitRepo = "https://github.com/umokee/umtask.git";
gitBranch = "claude/task-manager-fastapi-hYjWx";
```

Если форкнули репозиторий, измените на свой.

### Порты

```nix
publicPort = 8080;      # Публичный порт приложения
backendPort = 8000;     # Backend (обычно не нужно менять)
backendHost = "127.0.0.1";
```

`publicPort` - где будет доступно приложение извне.

### Пути

```nix
projectPath = "/var/lib/task-manager";          # Код и БД
secretsDir = "/var/lib/task-manager-secrets";   # API ключ
logDir = "/var/log/task-manager";               # Логи
```

Обычно не нужно менять.

### Reverse Proxy

```nix
reverseProxy = "caddy";  # "caddy", "nginx" или "none"
```

- **"caddy"** - Рекомендуется. Автоматически настраивает Caddy.
- **"nginx"** - Если предпочитаете Nginx.
- **"none"** - Без прокси. Backend будет слушать на `backendHost:backendPort` напрямую.

### Fail2ban

```nix
enableFail2ban = true;
fail2banMaxRetry = 2;       # Попыток до бана
fail2banFindTime = "1d";    # За какой период
fail2banBanTime = "52w";    # Длительность бана (52 недели = год)
```

Если у вас уже настроен fail2ban, установите `enableFail2ban = false` и добавьте вручную (см. ниже).

## Проверка работы

### Статус сервисов

```bash
systemctl status task-manager-backend
systemctl status task-manager-frontend-build
systemctl status task-manager-git-sync
systemctl status task-manager-api-key-init
```

### Логи

```bash
# Backend (real-time)
journalctl -u task-manager-backend -f

# Frontend build
journalctl -u task-manager-frontend-build

# Git sync
journalctl -u task-manager-git-sync

# Все сервисы task-manager
journalctl -u 'task-manager-*' -f
```

### Тест API

```bash
# Health check (без аутентификации)
curl http://localhost:8080/

# С аутентификацией
curl -H "X-API-Key: ваш-api-ключ" http://localhost:8080/api/stats
```

### Проверить API ключ

```bash
sudo cat /var/lib/task-manager-secrets/api-key
```

Вывод:
```
TASK_MANAGER_API_KEY=ваш-ключ-здесь
```

## Обновление

### Обновить код из Git

```bash
sudo systemctl restart task-manager-git-sync
sudo systemctl restart task-manager-frontend-build
sudo systemctl restart task-manager-backend
```

Или все сразу:

```bash
sudo systemctl restart task-manager-*
```

### Изменить API ключ

1. Изменить `apiKey` в модуле
2. Пересобрать:
   ```bash
   sudo nixos-rebuild switch
   ```
3. Перезапустить:
   ```bash
   sudo systemctl restart task-manager-api-key-init
   sudo systemctl restart task-manager-backend
   ```

### Изменить порт

1. Изменить `publicPort` в модуле
2. Пересобрать:
   ```bash
   sudo nixos-rebuild switch
   ```

Порт в firewall обновится автоматически.

## Интеграция с существующим fail2ban

Если у вас уже настроен fail2ban, в модуле установите:

```nix
enableFail2ban = false;
```

И добавьте в ваш fail2ban конфиг:

```nix
# В вашем модуле или configuration.nix
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

## Пример в стиле вашего cassettes

По аналогии с вашим модулем `cassettes-site`:

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

  # Настройки
  apiKey = "my-secret-api-key";
  publicPort = 8080;
  reverseProxy = "caddy";
  enableFail2ban = false;  # Используем ваш существующий fail2ban

  # ... остальные переменные из модуля ...
in
{
  config = lib.mkIf enable {
    # ... вся конфигурация из модуля ...
  };
}
```

И в вашем основном конфиге:

```nix
services = {
  cassettes-site = {};
  task-manager = {};  # Просто добавить
};
```

## Безопасность

### API ключ в коде

⚠️ **Внимание:** API ключ хранится в Nix конфигурации в открытом виде.

Для production рекомендуется использовать:
- `sops-nix` для шифрования секретов
- `agenix` для управления секретами
- Переменные окружения из защищенных файлов

Пример с переменной окружения:

```nix
# Вместо:
apiKey = "my-key";

# Использовать:
apiKey = builtins.getEnv "TASK_MANAGER_API_KEY";
```

И установить переменную перед сборкой:
```bash
export TASK_MANAGER_API_KEY="your-key"
sudo -E nixos-rebuild switch
```

### Права доступа

Модуль автоматически устанавливает безопасные права:
- API ключ: `0600` (только владелец)
- Секретная директория: `0700`
- Логи: `0750`
- Пользователь: непривилегированный `task-manager`

### Fail2ban защита

После 2 неудачных попыток аутентификации IP банится на 52 недели.

Формат лога:
```
2026-01-11 12:34:56 - task_manager.auth - WARNING - Invalid API key attempt from 192.168.1.100
```

## Troubleshooting

### Модуль не активируется

Убедитесь что:
1. `helpers` доступны в конфигурации
2. `task-manager = {}` добавлен в `services`
3. Модуль импортирован в `imports`

### Backend не запускается

```bash
# Проверить логи
journalctl -u task-manager-backend -n 50

# Проверить API ключ
sudo cat /var/lib/task-manager-secrets/api-key

# Проверить код склонирован
ls -la /var/lib/task-manager/
```

### Frontend не собирается

```bash
# Логи сборки
journalctl -u task-manager-frontend-build -n 100

# Проверить Node.js доступен
which node npm
```

### Порт занят

Изменить `publicPort` в модуле на свободный порт.

### Git sync не работает

```bash
# Логи
journalctl -u task-manager-git-sync -n 50

# Проверить доступ к репо
git ls-remote https://github.com/umokee/umtask.git
```

## Дополнительно

### HTTPS с Caddy

Измените в модуле:

```nix
# Вместо порта, используйте домен
publicPort = 443;  # или оставьте как есть
```

И добавьте в конфиг:

```nix
services.caddy.virtualHosts."tasks.yourdomain.com" = {
  extraConfig = ''
    reverse_proxy localhost:8080
  '';
};
```

Caddy автоматически получит Let's Encrypt сертификат.

### Кастомный домен с Nginx

В модуле:
```nix
reverseProxy = "nginx";
```

И настройте виртуальный хост как нужно.

### Отключить reverse proxy

В модуле:
```nix
reverseProxy = "none";
```

Backend будет доступен напрямую на `http://127.0.0.1:8000`.

## Полная схема

```
Internet → Firewall:8080 → Caddy:8080 → Backend:8000
                                       ↓
                                Frontend:dist/
```

С fail2ban:
```
Invalid API Key → Log → Fail2ban → iptables BAN
```

## Лицензия

MIT
