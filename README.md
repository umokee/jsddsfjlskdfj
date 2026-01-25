# Task Manager

Менеджер задач и привычек с системой поинтов. FastAPI + React.

## Запуск

### Backend

```bash
cd backend
pip install -r requirements.txt
export TASK_MANAGER_API_KEY="your-secret-key"
python -m backend.main
```

Backend: `http://localhost:8000`

### Frontend

```bash
cd frontend
npm install
echo "VITE_API_KEY=your-secret-key" > .env
npm run dev
```

Frontend: `http://localhost:5173`

## Структура

```
backend/
  main.py           # FastAPI endpoints
  models.py         # SQLAlchemy models
  schemas.py        # Pydantic schemas
  crud.py           # Business logic
  constants.py      # Configuration
  services/         # Task, points, backup services

frontend/
  src/
    components/     # React components
    App.jsx         # Main app
    api.js          # API client

deployment/
  nixos-module.nix  # NixOS module
```

## API

Все запросы требуют `X-API-Key` header.

### Tasks

```
GET    /api/tasks              # All tasks
GET    /api/tasks/pending      # Pending tasks
GET    /api/tasks/today        # Today's tasks
GET    /api/tasks/habits       # Habits
POST   /api/tasks              # Create task
PUT    /api/tasks/{id}         # Update task
DELETE /api/tasks/{id}         # Delete task
POST   /api/tasks/start        # Start task
POST   /api/tasks/stop         # Stop task
POST   /api/tasks/done         # Complete task
POST   /api/tasks/roll         # Roll daily plan
```

### Points

```
GET    /api/points/current     # Current points
GET    /api/points/history     # Points history
GET    /api/points/projection  # Points projection
```

### Goals

```
GET    /api/goals              # Get goals
POST   /api/goals              # Create goal
PUT    /api/goals/{id}         # Update goal
DELETE /api/goals/{id}         # Delete goal
```

### Settings

```
GET    /api/settings           # Get settings
PUT    /api/settings           # Update settings
```

## Система поинтов

### Задачи

```
Points = Base * EnergyMultiplier * TimeQuality
```

- Base: 10 (настраивается)
- EnergyMultiplier: 0.6 + (energy * 0.2) = 0.6-1.6
- TimeQuality: actual_time / expected_time (0.5-1.0)

### Привычки

**Skill** (навыки):
```
Points = Base * (1 + log2(streak + 1) * 0.15)
```

**Routine** (рутина): фиксированные 6 поинтов

### Штрафы

- Idle (0 tasks + 0 habits): -30
- Incomplete: 50% от потенциала
- Missed habit: -15 (skill), -8 (routine)
- Progressive: x1.1 - x1.5 за дни подряд

## NixOS

```nix
{
  imports = [ ./deployment/nixos-module.nix ];

  services.task-manager = {
    enable = true;
    domain = "tasks.example.com";  # optional
  };
}
```

## License

MIT
