# QuickShell Task Manager Widget

Интеграция таск-менеджера с QuickShell в терминальном стиле.

## Особенности

- **Терминальная эстетика** - без эмодзи, монохромные границы
- **Morning Check-in** - напоминание выбрать настроение
- **Rest Days** - индикатор дней отдыха
- **Таймер Pomodoro** - встроенный таймер для задач
- **Задачи и привычки** - полный список на сегодня
- **Быстрые действия** - старт, стоп, завершение задач

## Установка

1. Скопируйте файлы в папку QuickShell:
```bash
cp TaskWidget.qml TaskService.qml ~/.config/quickshell/widgets/
```

2. Настройте API ключ в вашем конфиге QuickShell:
```qml
TaskService {
    id: taskService
    apiKey: "your-api-key-here"
    apiUrl: "http://localhost:8000/api"
}

TaskWidget {
    service: taskService
    panelWindow: panel
}
```

## Использование

### Основные действия:

- **ЛКМ** - Открыть главное меню с задачами и привычками
- **ПКМ** - Обновить данные
- **Клик по таймеру** - Запустить/остановить Pomodoro

### Статусы виджета:

- **[REST_DAY]** - Сегодня день отдыха (желтый)
- **[MORNING_CHECK-IN]** - Нужно выбрать настроение (желтый, мигает)
- **[ALL_DONE]** - Все задачи выполнены (зеленый)
- **[NO_TASKS]** - Нет задач на сегодня (серый)
- **Описание задачи** - Текущая активная задача (зеленый)

### Morning Check-in:

При включенном авторолле утром появится модалка выбора энергии:
- E0 - EXHAUSTED (полностью без сил)
- E1 - TIRED (низкая энергия)
- E2 - OKAY (средняя энергия)
- E3 - GOOD (хорошая энергия)
- E4 - STRONG (высокая энергия)
- E5 - PEAK (максимум энергии)

### Главное меню:

Показывает:
- Текущую задачу с кнопками [COMPLETE] и [STOP]
- Список задач на сегодня
- Список привычек с прогрессом
- Клик на задачу/привычку запускает её

### Таймер:

- Показывает прогресс времени работы
- Рассчитывается: энергия × 20 минут
- ЛКМ - пауза/возобновление
- СКМ - сброс таймера

## Цветовая схема

Использует цвета из вашей темы QuickShell:
- `Theme.green` - акцент, активные задачи
- `Theme.red` - таймер, критические состояния
- `Theme.yellow` - предупреждения (Rest Day, Morning Check-in)
- `Theme.muted` - вторичный текст
- `Theme.bg` - фон модалок
- `Theme.fg` - основной текст

## API Integration

Виджет работает через REST API таск-менеджера:

- `GET /api/stats` - статистика
- `GET /api/tasks/current` - текущая задача
- `GET /api/tasks/today` - задачи на сегодня
- `GET /api/habits/today` - привычки на сегодня
- `GET /api/settings` - настройки (pending_roll)
- `POST /api/tasks/{id}/start` - запуск задачи
- `POST /api/tasks/{id}/stop` - остановка задачи
- `POST /api/tasks/{id}/complete` - завершение задачи
- `POST /api/tasks/complete-roll?mood={0-5}` - завершить Morning Check-in

## Требования

- QuickShell
- Task Manager Backend (запущен на localhost:8000)
- API ключ
- curl (для HTTP запросов)

## Структура файлов

- `TaskWidget.qml` - UI виджета
- `TaskService.qml` - API интеграция и бизнес-логика
- `README.md` - документация
