# Обновление: Автоматическое управление временем

Это обновление добавляет полноценную систему управления временем для Task Manager.

## Новые возможности

### 1. **Настройка времени доступности Roll**
- Можно указать время когда Roll становится доступен (по умолчанию 00:00)
- Если текущее время раньше указанного, кнопка Roll скрыта
- Показывается сообщение "Roll will be available at HH:MM"

### 2. **Автоматическое применение штрафов**
- Включается/выключается в Settings
- Автоматически применяет штрафы за вчерашний день в полночь (00:01)
- Не требует ручного действия

### 3. **Автоматический Roll**
- Можно включить автоматический Roll в заданное время (по умолчанию 06:00)
- Система автоматически выполнит Roll когда наступит указанное время
- Удобно если у вас есть фиксированный режим дня

### 4. **Фоновый планировщик**
- Работает постоянно в фоне
- Проверяет время каждую минуту
- Выполняет автоматические задачи по расписанию

## Установка обновления

### Шаг 1: Обновить зависимости

```bash
cd /home/user/umtask/backend
pip install -r requirements.txt
```

Будет установлена новая зависимость: `apscheduler==3.10.4`

### Шаг 2: Применить миграцию базы данных

```bash
cd /home/user/umtask/backend
python migrate_time_settings.py
```

Это добавит 4 новых столбца в таблицу `settings`:
- `roll_available_time` - время доступности Roll
- `auto_penalties_enabled` - включить авто-штрафы
- `auto_roll_enabled` - включить авто-Roll
- `auto_roll_time` - время авто-Roll

### Шаг 3: Перезапустить сервер

```bash
# Остановить текущий процесс (Ctrl+C)

# Запустить заново
cd /home/user/umtask/backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

Или если используете systemd:

```bash
sudo systemctl restart taskmanager
```

### Шаг 4: Обновить фронтенд

Фронтенд обновится автоматически благодаря Vite HMR, но для гарантии можно перезапустить:

```bash
cd /home/user/umtask/frontend
# Ctrl+C чтобы остановить
npm run dev
```

## Настройка

Откройте Settings в веб-интерфейсе. Новая секция **"Automation & Time Settings"**:

### Roll Available Time
- Время когда кнопка Roll становится доступной
- Формат: HH:MM (24-часовой)
- По умолчанию: 00:00 (доступен сразу после полуночи)
- **Пример**: Установите 06:00 если хотите планировать день с утра

### Auto-apply penalties at midnight
- Чекбокс: включить/выключить
- По умолчанию: **включено**
- Автоматически применяет штрафы за вчерашний день в 00:01

### Enable automatic Roll
- Чекбокс: включить/выключить
- По умолчанию: **выключено**
- Автоматически выполняет Roll в указанное время

### Auto Roll Time
- Показывается только если включен Auto Roll
- Формат: HH:MM (24-часовой)
- По умолчанию: 06:00
- **Пример**: Установите 07:00 если встаёте в 7 утра - план будет готов когда проснётесь

## Как это работает

### Фоновый планировщик

При запуске сервера автоматически запускается фоновый планировщик (APScheduler):

1. **Проверка авто-Roll**: каждую минуту
   - Проверяет включен ли `auto_roll_enabled`
   - Проверяет не выполнялся ли уже Roll сегодня
   - Проверяет наступило ли время `auto_roll_time`
   - Если все условия выполнены - выполняет Roll

2. **Применение штрафов**: в 00:01 каждую ночь
   - Проверяет включен ли `auto_penalties_enabled`
   - Вычисляет штрафы за вчерашний день
   - Применяет их к истории поинтов

### Логика доступности Roll

```python
# Проверяется при каждом запросе /api/tasks/can-roll

1. Выполнялся ли Roll сегодня?
   -> Да: Roll недоступен ("Roll already done today")
   -> Нет: продолжить

2. Текущее время >= roll_available_time?
   -> Да: Roll доступен
   -> Нет: "Roll will be available at HH:MM"
```

## Примеры использования

### Пример 1: Фиксированный утренний режим

**Настройки:**
- Roll Available Time: `07:00`
- Auto Roll Enabled: `true`
- Auto Roll Time: `07:00`
- Auto Penalties: `true`

**Что происходит:**
- 00:01 - Применяются штрафы за вчерашний день
- 07:00 - Автоматически выполняется Roll
- 07:01 - Вы просыпаетесь, открываете приложение - план на день уже готов!

### Пример 2: Гибкий режим

**Настройки:**
- Roll Available Time: `00:00` (после полуночи)
- Auto Roll Enabled: `false`
- Auto Penalties: `true`

**Что происходит:**
- 00:01 - Применяются штрафы за вчерашний день
- В любое время после 00:00 - кнопка Roll доступна
- Вы делаете Roll вручную когда удобно

### Пример 3: Поздний режим (сова)

**Настройки:**
- Roll Available Time: `18:00` (6 вечера)
- Auto Roll Enabled: `true`
- Auto Roll Time: `18:00`
- Auto Penalties: `true`

**Что происходит:**
- 00:01 - Применяются штрафы
- До 18:00 - кнопка Roll недоступна (показывает "Roll will be available at 18:00")
- 18:00 - Автоматически выполняется Roll
- Вы начинаете рабочий день вечером с готовым планом

## Логи

Планировщик записывает логи в:
- `/var/log/task-manager/app.log` (если есть права)
- `./logs/app.log` (fallback)

Примеры логов:

```
2026-01-15 00:01:00 - task_manager.scheduler - INFO - Applying midnight penalties for yesterday
2026-01-15 00:01:01 - task_manager.scheduler - INFO - Midnight penalties applied: 40 points

2026-01-15 07:00:00 - task_manager.scheduler - INFO - Executing automatic roll at 07:00
2026-01-15 07:00:01 - task_manager.scheduler - INFO - Auto-roll successful: 5 tasks, 3 habits
```

## Troubleshooting

### Roll не выполняется автоматически

1. Проверьте что `auto_roll_enabled = true` в Settings
2. Проверьте время в `auto_roll_time`
3. Проверьте логи: `tail -f /var/log/task-manager/app.log`
4. Убедитесь что сервер запущен

### Штрафы не применяются

1. Проверьте `auto_penalties_enabled = true` в Settings
2. Проверьте логи в 00:01
3. Убедитесь что сервер работает 24/7

### Roll доступен раньше времени

Проверьте настройку `roll_available_time` в Settings - возможно стоит `00:00`

## Технические детали

### Новые поля в Settings

```sql
roll_available_time VARCHAR DEFAULT "00:00"
auto_penalties_enabled BOOLEAN DEFAULT 1
auto_roll_enabled BOOLEAN DEFAULT 0
auto_roll_time VARCHAR DEFAULT "06:00"
```

### API Changes

**GET /api/tasks/can-roll** теперь возвращает:

```json
{
  "can_roll": true|false,
  "error_message": "Roll will be available at 07:00" | null,
  "roll_available_time": "07:00",
  "last_roll_date": "2026-01-15" | null
}
```

### Новые файлы

- `backend/scheduler.py` - фоновый планировщик
- `backend/migrate_time_settings.py` - миграция БД
- `UPDATE_TIME_SETTINGS.md` - этот файл

## Откат обновления

Если что-то пошло не так:

```bash
# 1. Откатить код
git revert <commit-hash>

# 2. Удалить новые столбцы из БД (опционально)
sqlite3 task_manager.db
> ALTER TABLE settings DROP COLUMN roll_available_time;
> ALTER TABLE settings DROP COLUMN auto_penalties_enabled;
> ALTER TABLE settings DROP COLUMN auto_roll_enabled;
> ALTER TABLE settings DROP COLUMN auto_roll_time;
> .quit

# 3. Переустановить старые зависимости
pip install -r requirements.txt
```
