# Task Manager

Минималистичный task manager с FastAPI backend и React frontend.

## Особенности

- **Приоритеты**: 0-10 (числовая шкала)
- **Энергия**: 0-5 (уровень сложности задачи)
- **Привычки**: ежедневные задачи с дедлайнами
- **API защита**: аутентификация по API ключу
- **Минималистичный UI**: темная тема с острыми углами

## Функционал

- ✅ Создание и управление задачами
- ✅ Отслеживание привычек
- ✅ Автоматическая генерация дневного плана (Roll)
- ✅ Статистика выполнения
- ✅ Start/Stop/Complete задачи
- ✅ Вычисление приоритета (urgency) на основе дедлайна, приоритета и энергии
- ✅ REST API с защитой по API ключу

## Быстрый старт

### Backend

```bash
cd backend
pip install -r requirements.txt

# Установить API ключ (опционально)
export TASK_MANAGER_API_KEY="ваш-секретный-ключ"

# Запустить сервер
python -m backend.main
```

Backend будет доступен на `http://localhost:8000`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend будет доступен на `http://localhost:5173`

## API Endpoints

Все endpoints требуют заголовок `X-API-Key` с вашим API ключом.

### Задачи

- `GET /api/tasks` - все задачи
- `GET /api/tasks/pending` - pending задачи (sorted by urgency)
- `GET /api/tasks/current` - текущая задача (активная или следующая)
- `GET /api/tasks/habits` - привычки на сегодня
- `GET /api/tasks/{id}` - конкретная задача
- `POST /api/tasks` - создать задачу
- `PUT /api/tasks/{id}` - обновить задачу
- `DELETE /api/tasks/{id}` - удалить задачу

### Действия

- `POST /api/tasks/start?task_id={id}` - начать задачу (или следующую если ID не указан)
- `POST /api/tasks/stop` - остановить активную задачу
- `POST /api/tasks/done?task_id={id}` - завершить задачу
- `POST /api/tasks/roll?mood={0-5}` - сгенерировать план на день

### Статистика

- `GET /api/stats` - статистика за день

## Структура задачи

```json
{
  "description": "Описание задачи",
  "project": "Название проекта",
  "priority": 5,
  "energy": 3,
  "is_habit": false,
  "is_today": false,
  "due_date": "2024-01-15T12:00:00"
}
```

## Пример использования API

```bash
# Установить API ключ
API_KEY="your-secret-key-change-me"

# Создать задачу
curl -X POST http://localhost:8000/api/tasks \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Написать документацию",
    "priority": 7,
    "energy": 3,
    "is_today": true
  }'

# Получить текущую задачу
curl http://localhost:8000/api/tasks/current \
  -H "X-API-Key: $API_KEY"

# Начать задачу
curl -X POST http://localhost:8000/api/tasks/start \
  -H "X-API-Key: $API_KEY"

# Завершить задачу
curl -X POST http://localhost:8000/api/tasks/done \
  -H "X-API-Key: $API_KEY"

# Сгенерировать план на день
curl -X POST http://localhost:8000/api/tasks/roll \
  -H "X-API-Key: $API_KEY"
```

## Конфигурация

### API ключ

По умолчанию используется ключ `your-secret-key-change-me`. Для изменения:

```bash
export TASK_MANAGER_API_KEY="ваш-секретный-ключ"
```

### База данных

По умолчанию используется SQLite база `tasks.db` в корне проекта.

## Алгоритм "Roll" (генерация плана)

1. Удаляет просроченные привычки
2. Очищает тег `is_today` со всех обычных задач
3. Добавляет критические задачи (дедлайн через 2 дня или меньше)
4. Дополняет случайными задачами до лимита (по умолчанию 5)
5. Фильтрует по уровню энергии если указан параметр `mood`

## Вычисление Urgency

```python
urgency = priority * 10.0

if overdue:
    urgency += 50.0
elif due_in_2_days:
    urgency += 25.0
elif due_in_week:
    urgency += 10.0

if energy >= 4:
    urgency += 5.0
elif energy <= 1:
    urgency -= 1.0
```

## UI особенности

- **Минималистичный дизайн**: темная тема, монотипный шрифт
- **Острые углы**: без border-radius
- **Компактность**: вся информация на одном экране
- **Keyboard-friendly**: возможность работы без мыши

## Технологии

- **Backend**: FastAPI, SQLAlchemy, SQLite
- **Frontend**: React, Vite, Axios
- **Стиль**: Vanilla CSS (без фреймворков)

## License

MIT
