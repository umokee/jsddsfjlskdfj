# Fail2ban Integration for Task Manager API

## Описание

Task Manager API логирует все неудачные попытки аутентификации с API ключом, включая IP адрес злоумышленника. Fail2ban может автоматически банить IP адреса после определенного количества неудачных попыток.

## Формат логов

При неудачной попытке аутентификации в лог записывается:
```
2026-01-11 12:34:56 - task_manager.auth - WARNING - Invalid API key attempt from 192.168.1.100
```

## NixOS конфигурация

### Вариант 1: Логирование в файл (рекомендуется для начала)

```nix
{
  lib,
  helpers,
  ...
}:
let
  enable = helpers.hasIn "services" "fail2ban";
in
{
  config = lib.mkIf enable {
    # Фильтр для task-manager
    environment.etc."fail2ban/filter.d/task-manager-api.conf".text = ''
      [Definition]
      failregex = ^.*Invalid API key attempt from <HOST>.*$
      ignoreregex =
    '';

    services.fail2ban = {
      enable = true;

      ignoreIP = [
        "127.0.0.1/8"
        "::1"
        # Добавьте ваши доверенные IP здесь
      ];

      maxretry = 2;  # Глобальное значение по умолчанию
      bantime = "52w";  # Глобальное значение по умолчанию

      jails = {
        # ... другие jails ...

        task-manager-api = {
          settings = {
            enabled = true;
            filter = "task-manager-api";
            logpath = "/var/log/task-manager/app.log";
            action = "iptables-allports";
            maxretry = 2;  # 2 неудачные попытки
            findtime = "1d";  # В течение 1 дня
            bantime = "52w";  # Бан на 52 недели (год)
          };
        };
      };
    };

    # Включить Task Manager сервис
    services.task-manager = {
      enable = true;
      apiKey = "your-super-secret-key-here";  # ОБЯЗАТЕЛЬНО ПОМЕНЯЙТЕ!
      logDir = "/var/log/task-manager";
    };
  };
}
```

### Вариант 2: Логирование в journald (более чистый вариант)

```nix
task-manager-api = {
  settings = {
    enabled = true;
    filter = "task-manager-api";
    backend = "systemd";  # Используем journald вместо файлов
    action = "iptables-allports";
    maxretry = 2;
    findtime = "1d";
    bantime = "52w";
  };
};
```

## Проверка конфигурации

### Ваша текущая конфигурация - ПРАВИЛЬНАЯ! ✅

Ваша конфигурация выглядит отлично, но есть пара рекомендаций:

### Рекомендации:

1. **findtime слишком большой**: `findtime = "60000d"` (164 года) - это слишком много. Рекомендую:
   ```nix
   findtime = "1d";  # Искать попытки за последние 24 часа
   # или
   findtime = "1h";  # Искать попытки за последний час
   ```

2. **Убрать комментарии из NixOS конфига**: Nix не любит `#` комментарии внутри атрибутов, лучше переместить их выше:
   ```nix
   # Task Manager API protection: 2 попытки и бан на 52 недели
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
   ```

3. **Опция backend**: Если используете systemd service (как в модуле выше), можете использовать:
   ```nix
   backend = "systemd";  # Вместо logpath
   ```

## Исправленная версия вашего конфига:

```nix
{
  lib,
  helpers,
  ...
}:
let
  enable = helpers.hasIn "services" "fail2ban";
in
{
  config = lib.mkIf enable {
    environment.etc."fail2ban/filter.d/sing-box-reality.conf".text = ''
      [Definition]
      failregex = .*inbound/vless\[vless-reality-in\]: process connection from <HOST>:[0-9]+: TLS handshake: REALITY: processed invalid connection
      ignoreregex =
    '';

    environment.etc."fail2ban/filter.d/task-manager-api.conf".text = ''
      [Definition]
      failregex = ^.*Invalid API key attempt from <HOST>.*$
      ignoreregex =
    '';

    services.fail2ban = {
      enable = true;

      ignoreIP = [
        "127.0.0.1/8"
        "::1"
        "2a10:c943:100::37c"
        "5.189.254.155"
        "178.218.98.139"
        "178.218.98.0/24"
        "178.218.0.0/16"
        "192.168.1.0/24"
        "172.18.0.0/30"
        "10.0.0.0/8"
        "172.16.0.0/12"
        "176.208.78.6"
        "80.83.234.147"
        "80.83.234.0/24"
      ];

      maxretry = 2;
      bantime = "52w";

      daemonSettings = {
        Definition = {
          dbpurgeage = "60000d";
        };
      };

      bantime-increment = {
        enable = true;
        multipliers = "2 4 8 16 32 64";
        maxtime = "10000d";
        rndtime = "600";
      };

      jails = {
        sshd.settings = {
          enabled = true;
          filter = "sshd";
          port = "ssh";
          mode = "aggressive";
          findtime = "60000d";
        };

        sing-box-reality = {
          settings = {
            enabled = true;
            filter = "sing-box-reality";
            backend = "systemd";
            action = "iptables-allports";
            findtime = "60000d";
          };
        };

        # Task Manager API protection
        task-manager-api = {
          settings = {
            enabled = true;
            filter = "task-manager-api";
            logpath = "/var/log/task-manager/app.log";
            action = "iptables-allports";
            maxretry = 2;
            findtime = "1d";  # Изменено с 60000d на 1d
            bantime = "52w";
          };
        };

        recidive = {
          settings = {
            enabled = true;
            filter = "recidive";
            logpath = "/var/log/fail2ban.log";
            action = "iptables-allports[name=recidive]";
            findtime = "60000d";
          };
        };

        nginx-http-auth = {
          settings = {
            enabled = false;
            filter = "nginx-http-auth";
            logpath = "/var/log/nginx/error.log";
            findtime = "60000d";
          };
        };

        nginx-4xx = {
          settings = {
            enabled = false;
            filter = "nginx-4xx";
            logpath = "/var/log/nginx/access.log";
            findtime = "60000d";
          };
        };

        nginx-botsearch = {
          settings = {
            enabled = false;
            filter = "nginx-botsearch";
            logpath = "/var/log/nginx/access.log";
            findtime = "60000d";
          };
        };
      };
    };
  };
}
```

## Тестирование

### 1. Проверить fail2ban фильтр:
```bash
fail2ban-regex /var/log/task-manager/app.log /etc/fail2ban/filter.d/task-manager-api.conf
```

### 2. Проверить статус jail:
```bash
fail2ban-client status task-manager-api
```

### 3. Тестовая неудачная попытка:
```bash
# Попробуйте с неправильным ключом
curl -H "X-API-Key: wrong-key" http://your-server:8000/api/tasks

# После 2 попыток ваш IP должен быть забанен
```

### 4. Разбанить IP (если забанили себя):
```bash
fail2ban-client set task-manager-api unbanip YOUR_IP
```

## Логика работы

1. Злоумышленник пытается обратиться к API с неправильным ключом
2. FastAPI логирует: `Invalid API key attempt from X.X.X.X`
3. Fail2ban видит эту запись в логе
4. После 2 попыток (maxretry=2) за 1 день (findtime="1d")
5. IP банится на 52 недели (bantime="52w") через iptables
6. Все порты блокируются (action="iptables-allports")

## Секьюрити-рекомендации

1. **API ключ**: Храните в secrets, не в конфиге напрямую
2. **HTTPS**: Обязательно используйте reverse proxy с TLS
3. **Rate limiting**: Добавьте дополнительный rate limiter в nginx/traefik
4. **Мониторинг**: Настройте алерты на события fail2ban
