# Пошаговая Диагностика Task Manager

Если backend не запускается, следуйте этим шагам **по порядку**.

## Шаг 1: Проверить что занимает порт 8000

```bash
# Проверить какой процесс занимает порт 8000
sudo ss -tlnp | grep 8000

# ИЛИ
sudo lsof -i :8000

# ИЛИ
sudo netstat -tlnp | grep 8000
```

**Что смотреть:**
- Если видите другой процесс `uvicorn` или `python` → есть дубликат
- Если видите другое приложение → конфликт портов

**Решение:**

### Если это старый процесс task-manager:
```bash
# Найти PID процесса из вывода выше
sudo kill <PID>

# ИЛИ остановить все сервисы task-manager
sudo systemctl stop task-manager-backend
sudo systemctl stop task-manager-*
```

### Если это другое приложение:
Измените порт в модуле `/path/to/task-manager.nix`:
```nix
backendPort = 8001;  # или другой свободный порт
```

Затем:
```bash
sudo nixos-rebuild switch
```

---

## Шаг 2: Проверить статус всех сервисов

```bash
# Проверить все сервисы task-manager
systemctl list-units 'task-manager-*'

# Детальный статус каждого
systemctl status task-manager-git-sync
systemctl status task-manager-api-key-init
systemctl status task-manager-frontend-build
systemctl status task-manager-backend
```

**Что смотреть:**
- Все ли сервисы зеленые (active/exited)?
- Есть ли ошибки (red/failed)?

**Типичные проблемы:**

### Git sync failed:
```bash
# Посмотреть логи
journalctl -u task-manager-git-sync -n 50

# Возможные причины:
# - Нет интернета
# - Неправильный gitRepo/gitBranch в модуле
# - Нет прав на /var/lib/task-manager
```

**Решение:**
```bash
# Проверить доступность репо
git ls-remote https://github.com/umokee/umtask.git

# Проверить права
ls -la /var/lib/task-manager/
sudo chown -R task-manager:task-manager /var/lib/task-manager
```

### Frontend build failed:
```bash
journalctl -u task-manager-frontend-build -n 100

# Возможные причины:
# - npm install не завершился
# - Нет Node.js
# - Ошибка в package.json
```

**Решение:**
```bash
# Пересобрать вручную
sudo -u task-manager bash
cd /var/lib/task-manager/frontend
npm install
npm run build
exit

# Перезапустить сервис
sudo systemctl restart task-manager-frontend-build
```

---

## Шаг 3: Проверить API ключ

```bash
# Проверить что файл существует
sudo cat /var/lib/task-manager-secrets/api-key

# Должен быть вывод:
# TASK_MANAGER_API_KEY=ваш-ключ-из-модуля
```

**Если файла нет или он пустой:**
```bash
# Перезапустить инициализацию
sudo systemctl restart task-manager-api-key-init

# Проверить логи
journalctl -u task-manager-api-key-init

# Проверить снова
sudo cat /var/lib/task-manager-secrets/api-key
```

**Если API ключ не совпадает с модулем:**
Вы изменили `apiKey` в модуле но не пересобрали:
```bash
# Пересобрать конфигурацию
sudo nixos-rebuild switch

# Перезапустить сервисы
sudo systemctl restart task-manager-api-key-init
sudo systemctl restart task-manager-backend
```

---

## Шаг 4: Проверить логи backend

```bash
# Real-time логи backend
journalctl -u task-manager-backend -f

# Последние 50 строк
journalctl -u task-manager-backend -n 50
```

**Типичные ошибки:**

### `Address already in use` (порт занят)
→ Вернитесь к **Шагу 1**

### `ModuleNotFoundError: No module named 'fastapi'`
Python пакеты не установились:
```bash
# Проверить что Python env корректный
sudo systemctl cat task-manager-backend | grep ExecStart

# Должно быть что-то вроде:
# /nix/store/.../bin/uvicorn backend.main:app ...
```

Если проблема - пересобрать конфигурацию:
```bash
sudo nixos-rebuild switch
```

### `No such file or directory: '/var/lib/task-manager/backend'`
Git sync не сработал → Вернитесь к **Шагу 2**

### `EnvironmentFile not found`
API key init не сработал → Вернитесь к **Шагу 3**

---

## Шаг 5: Проверить код склонирован

```bash
# Проверить что код на месте
ls -la /var/lib/task-manager/

# Должны быть:
# - backend/
# - frontend/
# - .git/
# - README.md
# и т.д.

# Проверить backend
ls -la /var/lib/task-manager/backend/

# Должны быть:
# - main.py
# - auth.py
# - models.py
# и т.д.

# Проверить frontend build
ls -la /var/lib/task-manager/frontend/dist/

# Должны быть:
# - index.html
# - assets/
```

**Если чего-то не хватает:**
```bash
# Полная пересинхронизация
sudo systemctl stop task-manager-*
sudo rm -rf /var/lib/task-manager/*
sudo systemctl start task-manager-git-sync
sudo systemctl start task-manager-frontend-build
sudo systemctl start task-manager-backend
```

---

## Шаг 6: Проверить настройки модуля

Откройте ваш файл модуля и проверьте:

```nix
let
  enable = helpers.hasIn "services" "task-manager";

  # Проверить что вы изменили API ключ!
  apiKey = "your-super-secret-api-key-change-me";  # <--- НЕ ДОЛЖНО БЫТЬ DEFAULT!

  # Проверить репо и ветку
  gitRepo = "https://github.com/umokee/umtask.git";
  gitBranch = "claude/task-manager-fastapi-hYjWx";

  # Проверить порты (должны быть свободны)
  publicPort = 8080;
  backendPort = 8000;

  # Остальное...
```

**Обязательные проверки:**
1. ✅ `apiKey` изменен на свой
2. ✅ `gitRepo` и `gitBranch` правильные
3. ✅ `publicPort` и `backendPort` свободны
4. ✅ `reverseProxy` соответствует вашему выбору

**После изменений:**
```bash
sudo nixos-rebuild switch
```

---

## Шаг 7: Проверить что модуль активирован

```bash
# Проверить что task-manager в списке сервисов
cat /etc/nixos/configuration.nix | grep -A 5 "services ="

# Должно быть:
# services = {
#   ...
#   task-manager = {};
#   ...
# };
```

**Если нет:**
Добавьте в `/etc/nixos/configuration.nix`:
```nix
services = {
  # ... ваши существующие сервисы ...
  task-manager = {};
};
```

И пересоберите:
```bash
sudo nixos-rebuild switch
```

---

## Шаг 8: Полная перезагрузка всех сервисов

```bash
# Остановить все
sudo systemctl stop task-manager-backend
sudo systemctl stop task-manager-frontend-build
sudo systemctl stop task-manager-api-key-init
sudo systemctl stop task-manager-git-sync

# Подождать 2 секунды
sleep 2

# Запустить по порядку
sudo systemctl start task-manager-git-sync
sleep 2
sudo systemctl start task-manager-api-key-init
sleep 2
sudo systemctl start task-manager-frontend-build
sleep 5
sudo systemctl start task-manager-backend

# Проверить статусы
systemctl status task-manager-backend
```

---

## Шаг 9: Проверить reverse proxy (Caddy/Nginx)

```bash
# Если используете Caddy
systemctl status caddy
journalctl -u caddy -n 50

# Если используете Nginx
systemctl status nginx
journalctl -u nginx -n 50

# Проверить что прокси слушает на publicPort
sudo ss -tlnp | grep 8080  # или ваш publicPort
```

**Если прокси не работает:**
```bash
# Для Caddy
sudo systemctl restart caddy

# Для Nginx
sudo systemctl restart nginx

# Проверить конфигурацию
sudo caddy validate --config /etc/caddy/Caddyfile
# ИЛИ
sudo nginx -t
```

---

## Шаг 10: Проверить firewall

```bash
# Проверить что publicPort открыт
sudo iptables -L -n | grep 8080  # или ваш publicPort

# Проверить NixOS firewall конфигурацию
cat /etc/nixos/configuration.nix | grep -i firewall
```

**Если порт закрыт:**
Модуль должен автоматически открыть порт. Если нет:
```bash
sudo nixos-rebuild switch
```

---

## Шаг 11: Тест приложения

```bash
# Проверить что backend отвечает (локально)
curl http://127.0.0.1:8000/

# Должно вернуть:
# {"message":"Task Manager API","status":"active"}

# Проверить через публичный порт
curl http://localhost:8080/

# С API ключом
API_KEY="ваш-api-ключ-из-модуля"
curl -H "X-API-Key: $API_KEY" http://localhost:8080/api/stats
```

**Если не работает:**
- `Connection refused` на 8000 → backend не запущен
- `Connection refused` на 8080 → reverse proxy не работает
- `401 Unauthorized` → неправильный API ключ
- `404 Not Found` → неправильный путь

---

## Полный скрипт диагностики

Скопируйте и запустите:

```bash
#!/bin/bash

echo "=== Task Manager Diagnostic ==="
echo

echo "1. Checking port 8000..."
sudo ss -tlnp | grep 8000
echo

echo "2. Services status..."
systemctl list-units 'task-manager-*' --no-pager
echo

echo "3. API key..."
sudo cat /var/lib/task-manager-secrets/api-key 2>/dev/null || echo "NOT FOUND"
echo

echo "4. Code directory..."
ls -la /var/lib/task-manager/ 2>/dev/null | head -10
echo

echo "5. Backend logs (last 20 lines)..."
journalctl -u task-manager-backend -n 20 --no-pager
echo

echo "6. Public port..."
sudo ss -tlnp | grep 8080
echo

echo "7. Backend test..."
curl -s http://127.0.0.1:8000/ 2>/dev/null || echo "FAILED"
echo

echo "8. Proxy test..."
curl -s http://localhost:8080/ 2>/dev/null || echo "FAILED"
echo

echo "=== End of diagnostic ==="
```

---

## Быстрое решение типичных проблем

### Проблема: "Address already in use"

```bash
# Найти и убить процесс
sudo pkill -f 'uvicorn backend.main'

# ИЛИ
sudo systemctl stop task-manager-backend
sleep 2
sudo systemctl start task-manager-backend
```

### Проблема: Код не склонирован

```bash
sudo systemctl restart task-manager-git-sync
journalctl -u task-manager-git-sync -n 50
```

### Проблема: Frontend не собран

```bash
sudo systemctl restart task-manager-frontend-build
journalctl -u task-manager-frontend-build -f
```

### Проблема: Неправильный API ключ

1. Изменить `apiKey` в модуле
2. `sudo nixos-rebuild switch`
3. `sudo systemctl restart task-manager-api-key-init`
4. `sudo systemctl restart task-manager-backend`

### Проблема: Полный сброс

```bash
# ВНИМАНИЕ: Удалит все данные и задачи!
sudo systemctl stop task-manager-*
sudo rm -rf /var/lib/task-manager/*
sudo rm -rf /var/lib/task-manager-secrets/*
sudo nixos-rebuild switch
```

---

## Что делать если ничего не помогло

1. Показать вывод:
   ```bash
   journalctl -u task-manager-backend -n 100 --no-pager
   ```

2. Показать настройки модуля (без API ключа):
   ```bash
   cat /path/to/task-manager.nix | head -60
   ```

3. Показать статус всех сервисов:
   ```bash
   systemctl status task-manager-* --no-pager
   ```

4. Показать что на портах:
   ```bash
   sudo ss -tlnp | grep -E '8000|8080'
   ```
