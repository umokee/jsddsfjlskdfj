# Подключение к API извне

## 🔑 Быстрый старт

### 1. Настройка API ключа

```bash
# Установите переменную окружения с вашим секретным ключом
export TASK_MANAGER_API_KEY="ваш-секретный-ключ-здесь"
```

Добавьте в `~/.bashrc` или `~/.zshrc` для постоянного использования:

```bash
echo 'export TASK_MANAGER_API_KEY="ваш-секретный-ключ-здесь"' >> ~/.bashrc
source ~/.bashrc
```

### 2. Настройка CORS

Откройте `backend/main.py` и измените настройки CORS:

```python
# Для разработки - разрешить все источники
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить все источники
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**ИЛИ** для продакшена - указать конкретные домены:

```python
# Для продакшена - указать конкретные домены
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://ваш-сервер.com",          # Ваш домен
        "http://192.168.1.100:5173",      # Локальная сеть
        "https://ваш-сервер.com",         # HTTPS версия
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Запуск сервера

```bash
cd /home/user/umtask/backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

Теперь API доступен на `http://ваш-ip:8000`

---

## 📡 Использование API из внешних приложений

### Пример: cURL

```bash
# Проверка подключения
curl http://ваш-ip:8000/

# Получить все задачи (с API ключом)
curl -H "X-API-Key: ваш-секретный-ключ" \
     http://ваш-ip:8000/api/tasks

# Создать новую задачу
curl -X POST \
     -H "X-API-Key: ваш-секретный-ключ" \
     -H "Content-Type: application/json" \
     -d '{"description":"Новая задача","priority":2,"energy_level":2,"is_habit":false}' \
     http://ваш-ip:8000/api/tasks

# Получить статистику
curl -H "X-API-Key: ваш-секретный-ключ" \
     http://ваш-ip:8000/api/stats
```

### Пример: Python

```python
import requests

API_URL = "http://ваш-ip:8000"
API_KEY = "ваш-секретный-ключ"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Получить все задачи
response = requests.get(f"{API_URL}/api/tasks", headers=headers)
tasks = response.json()
print(tasks)

# Создать задачу
new_task = {
    "description": "Новая задача из Python",
    "priority": 2,
    "energy_level": 3,
    "is_habit": False
}
response = requests.post(f"{API_URL}/api/tasks", json=new_task, headers=headers)
print(response.json())

# Сделать Roll
response = requests.post(f"{API_URL}/api/tasks/roll", headers=headers)
print(response.json())
```

### Пример: JavaScript/TypeScript

```javascript
const API_URL = 'http://ваш-ip:8000';
const API_KEY = 'ваш-секретный-ключ';

const headers = {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json'
};

// Получить все задачи
async function getTasks() {
    const response = await fetch(`${API_URL}/api/tasks`, { headers });
    const tasks = await response.json();
    console.log(tasks);
}

// Создать задачу
async function createTask() {
    const newTask = {
        description: 'Новая задача из JS',
        priority: 2,
        energy_level: 3,
        is_habit: false
    };

    const response = await fetch(`${API_URL}/api/tasks`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(newTask)
    });

    const task = await response.json();
    console.log(task);
}

// Завершить задачу
async function completeTask(taskId) {
    const response = await fetch(`${API_URL}/api/tasks/done?task_id=${taskId}`, {
        method: 'POST',
        headers: headers
    });

    const result = await response.json();
    console.log(result);
}
```

### Пример: Mobile App (React Native)

```javascript
import axios from 'axios';

const API_URL = 'http://ваш-ip:8000';
const API_KEY = 'ваш-секретный-ключ';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json'
    }
});

// Получить сегодняшние задачи
const getTodayTasks = async () => {
    try {
        const response = await api.get('/api/tasks/today');
        return response.data;
    } catch (error) {
        console.error('Ошибка получения задач:', error);
    }
};

// Начать задачу
const startTask = async (taskId) => {
    try {
        const response = await api.post('/api/tasks/start', null, {
            params: { task_id: taskId }
        });
        return response.data;
    } catch (error) {
        console.error('Ошибка запуска задачи:', error);
    }
};
```

---

## 🔒 Продакшен: Nginx Reverse Proxy

### 1. Установка Nginx

```bash
sudo apt install nginx
```

### 2. Конфигурация `/etc/nginx/sites-available/taskmanager`

```nginx
server {
    listen 80;
    server_name ваш-домен.com;

    # Ограничение скорости запросов
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Таймауты
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Логи для fail2ban
    access_log /var/log/nginx/taskmanager_access.log;
    error_log /var/log/nginx/taskmanager_error.log;
}
```

### 3. Активация конфигурации

```bash
sudo ln -s /etc/nginx/sites-available/taskmanager /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. SSL с Let's Encrypt (опционально)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d ваш-домен.com
```

---

## 🌐 Локальная сеть (LAN)

Для доступа из локальной сети (другие устройства в той же WiFi):

### 1. Узнайте IP адрес сервера

```bash
ip addr show | grep "inet "
# Или
hostname -I
```

Например: `192.168.1.100`

### 2. Настройте frontend

Откройте `frontend/src/config.js` (создайте если нет):

```javascript
export const API_URL = import.meta.env.PROD
    ? 'http://192.168.1.100:8000'  // IP вашего сервера
    : 'http://localhost:8000';
```

В `frontend/src/App.jsx` используйте:

```javascript
import { API_URL } from './config';

const response = await fetch(`${API_URL}/api/tasks`, {
    headers: { 'X-API-Key': 'ваш-ключ' }
});
```

### 3. Запустите frontend на всех интерфейсах

```bash
cd /home/user/umtask/frontend
npm run dev -- --host 0.0.0.0
```

Теперь доступ:
- Backend: `http://192.168.1.100:8000`
- Frontend: `http://192.168.1.100:5173`

---

## 🛡️ Безопасность

### 1. Firewall (UFW)

```bash
# Разрешить только определённые IP
sudo ufw allow from 192.168.1.0/24 to any port 8000

# Или разрешить всем (не рекомендуется для интернета)
sudo ufw allow 8000/tcp
```

### 2. Сильный API ключ

Генерация безопасного ключа:

```bash
openssl rand -hex 32
# Результат: a1b2c3d4e5f6... (используйте как API_KEY)
```

### 3. Rate Limiting с Nginx

Уже настроено в конфигурации выше: 10 запросов/сек + burst 20

### 4. Fail2ban

См. секцию "Безопасность" в `README.md`

---

## 🐳 Docker с внешним доступом

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - TASK_MANAGER_API_KEY=${TASK_MANAGER_API_KEY}
    volumes:
      - ./task_manager.db:/app/task_manager.db
    restart: unless-stopped

  frontend:
    image: node:18-alpine
    working_dir: /app
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
    command: sh -c "npm install && npm run dev -- --host 0.0.0.0"
    environment:
      - VITE_API_URL=http://ваш-ip:8000
    restart: unless-stopped
```

### Запуск

```bash
export TASK_MANAGER_API_KEY="ваш-секретный-ключ"
docker-compose up -d
```

---

## 📱 Доступ с телефона

### Вариант 1: Локальная сеть

1. Убедитесь что телефон подключён к той же WiFi
2. Откройте браузер на телефоне
3. Перейдите на `http://192.168.1.100:5173` (IP вашего сервера)

### Вариант 2: Интернет через VPN (Tailscale)

```bash
# На сервере
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# На телефоне - установите Tailscale app
# Используйте Tailscale IP (100.x.x.x)
```

### Вариант 3: Cloudflare Tunnel (бесплатно)

```bash
# Установка
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Создание туннеля
cloudflared tunnel --url http://localhost:8000
```

---

## 🧪 Проверка доступа

### 1. Локальная проверка

```bash
curl http://localhost:8000/
# {"message":"Task Manager API","status":"active"}
```

### 2. Внешняя проверка

```bash
curl http://ваш-ip:8000/
```

### 3. Проверка API ключа

```bash
# Без ключа - должна быть ошибка 401
curl http://ваш-ip:8000/api/tasks

# С ключом - должен быть список задач
curl -H "X-API-Key: ваш-ключ" http://ваш-ip:8000/api/tasks
```

### 4. Проверка CORS из браузера

Откройте консоль браузера (F12) на любом сайте:

```javascript
fetch('http://ваш-ip:8000/api/tasks', {
    headers: { 'X-API-Key': 'ваш-ключ' }
})
.then(r => r.json())
.then(console.log);
```

---

## 🔧 Troubleshooting

### Проблема: "Connection refused"

```bash
# Проверьте что сервер запущен
ps aux | grep uvicorn

# Проверьте на каком порту слушает
sudo netstat -tlnp | grep 8000

# Перезапустите сервер
cd /home/user/umtask/backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Проблема: "CORS error"

Проверьте `backend/main.py` строку 60 - убедитесь что ваш домен/IP добавлен в `allow_origins`

### Проблема: "401 Unauthorized"

```bash
# Проверьте API ключ
echo $TASK_MANAGER_API_KEY

# Убедитесь что передаёте правильный заголовок
curl -v -H "X-API-Key: ваш-ключ" http://ваш-ip:8000/api/tasks
```

### Проблема: Firewall блокирует

```bash
# Проверьте правила
sudo ufw status

# Разрешите порт
sudo ufw allow 8000/tcp
```

---

## 📚 Полезные команды

```bash
# Узнать внешний IP
curl ifconfig.me

# Узнать локальный IP
hostname -I

# Проверить открыт ли порт
sudo netstat -tlnp | grep 8000

# Посмотреть логи сервера
tail -f logs/app.log

# Проверить процессы Python
ps aux | grep python

# Убить процесс на порту 8000
sudo lsof -ti:8000 | xargs kill -9
```

---

## 🎯 Рекомендации

1. **Для разработки**: `allow_origins=["*"]` + локальная сеть
2. **Для продакшена**: Nginx reverse proxy + Let's Encrypt SSL + конкретные домены в CORS
3. **Для мобильного доступа**: Tailscale VPN (просто и безопасно)
4. **API ключ**: Используйте сгенерированный ключ 64+ символов
5. **Логи**: Настройте fail2ban для защиты от брутфорса
