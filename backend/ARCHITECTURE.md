# Modular Monolith Architecture

## Overview

This project follows **Modular Monolith** architecture with **Orchestrator** pattern for cross-module communication.

```
backend/
├── main.py                 # Entry point, assembles the app
├── core/                   # Infrastructure (no business logic)
├── shared/                 # Shared utilities (no business logic)
├── modules/                # Business modules (isolated)
├── workflows/              # Orchestrators (cross-module coordination)
└── scheduler/              # Background jobs
```

---

## Core Principles

### 1. Module = Black Box

A module is a **black box**. Outside code can only see what it explicitly exports.

```python
# ✅ Correct - import from module's __init__.py
from modules.tasks import TaskService, TaskResponse

# ❌ Forbidden - reaching inside module
from modules.tasks.repository import TaskRepository
from modules.tasks.models import Task
```

### 2. Modules Do NOT Know Each Other

Modules **never import** other modules directly. All cross-module coordination happens through **Workflows**.

```python
# ❌ Forbidden - modules/tasks/service.py
from modules.points import PointsService  # NO!

# ✅ Correct - workflows/complete_task.py
from modules.tasks import TaskService
from modules.points import PointsService
```

### 3. Data Over Dependencies

Modules return **data (DTOs)**, not ORM models. They accept **primitives or DTOs**, not services.

```python
# Module returns DTO
class TaskService:
    def complete(self, task_id: int) -> TaskResult:
        # Returns data, not ORM model
        return TaskResult(id=task.id, energy=task.energy, ...)

# Workflow passes data between modules
class CompleteTaskWorkflow:
    def execute(self, task_id: int):
        task_data = self.tasks.complete(task_id)
        points = self.points.calculate(
            energy=task_data.energy,  # Pass data, not service
            priority=task_data.priority
        )
```

---

## Directory Structure

### `core/` — Infrastructure

Contains database connection, base exceptions, security. **No business logic.**

```
core/
├── __init__.py
├── database.py         # Engine, SessionLocal, Base, get_db()
├── exceptions.py       # Base exception classes
└── security.py         # Authentication (API key verification)
```

**Rules:**
- `core/` can only import external packages and `shared/`
- `core/` **never** imports from `modules/`
- All modules can import from `core/`

### `shared/` — Utilities

Contains pure utility functions without business logic.

```
shared/
├── __init__.py
├── constants.py        # App-wide constants
└── date_utils.py       # Date/time helpers
```

**Rules:**
- `shared/` can only import external packages
- `shared/` **never** imports from `core/` or `modules/`
- Contains only **pure functions** (no side effects, no DB access)

### `modules/` — Business Modules

Each module is a self-contained business area.

```
modules/
├── tasks/
├── points/
├── penalties/
├── goals/
├── rest_days/
├── settings/
└── backups/
```

---

## Module Structure

Every module has the **same structure**:

```
modules/example/
├── __init__.py         # PUBLIC API (only this is visible outside)
├── models.py           # SQLAlchemy models (PRIVATE)
├── schemas.py          # Pydantic DTOs
├── repository.py       # Data access layer (PRIVATE)
├── service.py          # Business logic
├── routes.py           # HTTP endpoints
└── exceptions.py       # Module-specific exceptions
```

### File Responsibilities

| File | Contains | Visibility |
|------|----------|------------|
| `__init__.py` | Exports (Service, DTOs, Exceptions) | PUBLIC |
| `models.py` | SQLAlchemy ORM models | PRIVATE |
| `schemas.py` | Pydantic request/response models | PUBLIC (via __init__) |
| `repository.py` | Database queries | PRIVATE |
| `service.py` | Business logic | PUBLIC (via __init__) |
| `routes.py` | FastAPI endpoints | PUBLIC (router) |
| `exceptions.py` | Custom exceptions | PUBLIC (via __init__) |

### `__init__.py` — Public Contract

```python
# modules/tasks/__init__.py

from .service import TaskService
from .schemas import TaskCreate, TaskUpdate, TaskResponse, TaskResult
from .exceptions import TaskNotFoundError, DependencyNotMetError
from .routes import router

__all__ = [
    # Service
    "TaskService",
    # Schemas
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "TaskResult",
    # Exceptions
    "TaskNotFoundError",
    "DependencyNotMetError",
    # Router
    "router",
]
```

### `models.py` — ORM Models (PRIVATE)

```python
# modules/tasks/models.py
from sqlalchemy import Column, Integer, String
from core.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    description = Column(String, nullable=False)
    # ...

# NEVER import this from outside the module!
```

### `schemas.py` — DTOs

```python
# modules/tasks/schemas.py
from pydantic import BaseModel

# Input DTOs
class TaskCreate(BaseModel):
    description: str
    priority: int = 3

# Output DTOs
class TaskResponse(BaseModel):
    id: int
    description: str
    status: str

    class Config:
        from_attributes = True

# Internal DTOs (for cross-module communication)
class TaskResult(BaseModel):
    """Data returned after task completion - used by workflows"""
    id: int
    energy: int
    priority: int
    is_habit: bool
    streak: int
```

### `repository.py` — Data Access (PRIVATE)

```python
# modules/tasks/repository.py
from sqlalchemy.orm import Session
from .models import Task

class TaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, task_id: int) -> Task | None:
        return self.db.query(Task).filter(Task.id == task_id).first()

    def create(self, **data) -> Task:
        task = Task(**data)
        self.db.add(task)
        self.db.flush()
        return task

# NEVER import this from outside the module!
```

### `service.py` — Business Logic

```python
# modules/tasks/service.py
from sqlalchemy.orm import Session
from .repository import TaskRepository
from .schemas import TaskCreate, TaskResponse, TaskResult
from .exceptions import TaskNotFoundError

class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TaskRepository(db)

    def create(self, data: TaskCreate) -> TaskResponse:
        task = self.repo.create(**data.model_dump())
        return TaskResponse.model_validate(task)

    def complete(self, task_id: int) -> TaskResult:
        task = self.repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(task_id)

        # Business logic here...

        return TaskResult(
            id=task.id,
            energy=task.energy,
            priority=task.priority,
            is_habit=task.is_habit,
            streak=task.streak
        )
```

### `routes.py` — HTTP Layer

```python
# modules/tasks/routes.py
from fastapi import APIRouter, Depends
from core.database import get_db
from core.security import verify_api_key
from .service import TaskService
from .schemas import TaskCreate, TaskResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=TaskResponse)
def create_task(
    data: TaskCreate,
    db = Depends(get_db),
    _ = Depends(verify_api_key)
):
    service = TaskService(db)
    return service.create(data)
```

---

## Workflows — Cross-Module Orchestration

Workflows coordinate operations that span multiple modules.

```
workflows/
├── __init__.py
├── complete_task.py    # Task completion with points
├── roll_day.py         # Daily roll with penalties
├── apply_penalties.py  # Penalty calculation
└── schemas.py          # Workflow result DTOs
```

### Workflow Example

```python
# workflows/complete_task.py
from sqlalchemy.orm import Session
from modules.tasks import TaskService
from modules.points import PointsService
from modules.goals import GoalService
from .schemas import CompleteTaskResult

class CompleteTaskWorkflow:
    def __init__(self, db: Session):
        self.db = db
        self.tasks = TaskService(db)
        self.points = PointsService(db)
        self.goals = GoalService(db)

    def execute(self, task_id: int) -> CompleteTaskResult:
        # 1. Complete the task (get data back)
        task_data = self.tasks.complete(task_id)

        # 2. Calculate and add points (pass data, not service)
        points = self.points.calculate(
            energy=task_data.energy,
            priority=task_data.priority,
            is_habit=task_data.is_habit,
            streak=task_data.streak
        )
        self.points.add_to_history(points=points, task_id=task_data.id)

        # 3. Check goal achievements
        self.goals.check_achievements()

        # 4. Commit transaction
        self.db.commit()

        return CompleteTaskResult(
            task_id=task_data.id,
            points_earned=points
        )
```

### When to Use Workflow vs Direct Service

| Scenario | Use |
|----------|-----|
| Simple CRUD (get task, create task) | Direct service call in route |
| Single module operation | Direct service call in route |
| Multiple modules involved | Workflow |
| Transaction spans modules | Workflow |

```python
# routes.py

# Simple read - direct service
@router.get("/{task_id}")
def get_task(task_id: int, db = Depends(get_db)):
    return TaskService(db).get(task_id)

# Complex operation - workflow
@router.post("/{task_id}/complete")
def complete_task(task_id: int, db = Depends(get_db)):
    return CompleteTaskWorkflow(db).execute(task_id)
```

---

## Import Rules

```
┌─────────────────────────────────────────────┐
│                  main.py                     │
│         (imports everything)                 │
└─────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│              workflows/*                     │
│     (imports modules via __init__.py)        │
└─────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│               modules/*                      │
│      (imports core/, shared/ only)           │
└─────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│            core/ and shared/                 │
│     (imports external packages only)         │
└─────────────────────────────────────────────┘
```

### What Can Import What

| From | Can Import |
|------|------------|
| `main.py` | Everything |
| `workflows/*` | `modules/*` (via __init__), `core/*`, `shared/*` |
| `modules/X/routes.py` | `modules/X/*`, `core/*`, `shared/*`, `workflows/*` |
| `modules/X/service.py` | `modules/X/*`, `core/*`, `shared/*` |
| `modules/X/repository.py` | `modules/X/models`, `core/database` |
| `modules/X/models.py` | `core/database`, `shared/constants` |
| `core/*` | `shared/*`, external packages |
| `shared/*` | External packages only |

### Forbidden Imports

```python
# ❌ Module imports another module's internals
from modules.points.repository import PointHistoryRepository

# ❌ Module imports another module (even via __init__)
# modules/tasks/service.py
from modules.points import PointsService

# ❌ Core imports from modules
# core/database.py
from modules.tasks.models import Task

# ❌ Shared contains business logic
# shared/task_helpers.py  # Should be in modules/tasks/
```

---

## Database Relations Between Modules

### Foreign Keys: ID Only, No Relationships

```python
# modules/points/models.py
class PointHistory(Base):
    __tablename__ = "point_history"

    id = Column(Integer, primary_key=True)

    # FK as plain integer - no ORM relationship
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)

    # DON'T do this:
    # task = relationship("Task")  # Creates coupling
```

When you need related data, get it through the workflow:

```python
# workflows/get_day_details.py
class GetDayDetailsWorkflow:
    def execute(self, date: date):
        history = self.points.get_history(date)

        # Enrich with task data
        for record in history.task_completions:
            if record.task_id:
                record.task_info = self.tasks.get_brief(record.task_id)

        return history
```

---

## Exception Handling

### Base Exceptions in Core

```python
# core/exceptions.py
class AppError(Exception):
    """Base exception for all app errors"""
    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

class NotFoundError(AppError):
    """Resource not found"""
    def __init__(self, resource: str, identifier):
        super().__init__(
            f"{resource} with id {identifier} not found",
            code="NOT_FOUND"
        )

class ValidationError(AppError):
    """Validation failed"""
    pass
```

### Module-Specific Exceptions

```python
# modules/tasks/exceptions.py
from core.exceptions import NotFoundError, AppError

class TaskNotFoundError(NotFoundError):
    def __init__(self, task_id: int):
        super().__init__("Task", task_id)
        self.task_id = task_id

class DependencyNotMetError(AppError):
    def __init__(self, task_id: int, dependency_id: int):
        super().__init__(
            f"Task {task_id} depends on task {dependency_id} which is not completed",
            code="DEPENDENCY_NOT_MET"
        )
```

### Exception Handlers in Main

```python
# main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from core.exceptions import AppError, NotFoundError

app = FastAPI()

@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": exc.message})

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=400, content={"detail": exc.message})
```

---

## Checklist: Where Does Code Go?

| What | Where | Example |
|------|-------|---------|
| HTTP endpoint | `modules/X/routes.py` | `POST /tasks` |
| Business rule | `modules/X/service.py` | "can't complete already completed task" |
| SQL query | `modules/X/repository.py` | `SELECT * FROM tasks WHERE status = 'pending'` |
| DB table definition | `modules/X/models.py` | `class Task(Base)` |
| Request/Response format | `modules/X/schemas.py` | `class TaskCreate(BaseModel)` |
| Business exception | `modules/X/exceptions.py` | `TaskNotFoundError` |
| Module constant | `modules/X/` top of relevant file | `MAX_DAILY_TARGET = 20` |
| App-wide constant | `shared/constants.py` | `DATE_FORMAT = "%Y-%m-%d"` |
| DB connection | `core/database.py` | `get_db()`, `Base` |
| Authentication | `core/security.py` | `verify_api_key()` |
| Base exceptions | `core/exceptions.py` | `AppError`, `NotFoundError` |
| Cross-module flow | `workflows/` | `CompleteTaskWorkflow` |
| Date utilities | `shared/date_utils.py` | `get_effective_date()` |

---

## Testing Strategy

### Unit Tests: Test Modules in Isolation

```python
# tests/modules/tasks/test_service.py
def test_complete_task_returns_result():
    # Mock repository
    service = TaskService(mock_db)
    result = service.complete(task_id=1)

    assert isinstance(result, TaskResult)
    assert result.id == 1
```

### Integration Tests: Test Workflows

```python
# tests/workflows/test_complete_task.py
def test_complete_task_adds_points():
    workflow = CompleteTaskWorkflow(db)
    result = workflow.execute(task_id=1)

    assert result.points_earned > 0
    # Check points were actually saved
```

---

## Common Mistakes to Avoid

### 1. Too Many Small Modules

```
modules/
├── create_task/      # ❌ This is an action, not a module
├── complete_task/    # ❌
├── delete_task/      # ❌
```

Correct: One `tasks/` module with all operations.

### 2. God Module

```
modules/
├── core/             # ❌ Contains all business logic
├── api/              # Only routes
```

This is layered architecture, not modular monolith.

### 3. Business Logic in Routes

```python
# ❌ routes.py
@router.post("/{task_id}/complete")
def complete_task(task_id: int, db = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task.status == "completed":
        raise HTTPException(400, "Already completed")
    task.status = "completed"
    # ... more logic
```

Correct: Routes call services, all logic in services.

### 4. Circular Dependencies

```
tasks → points → penalties → tasks  # ❌ Cycle
```

Solutions:
- Extract common code to `shared/`
- Use workflows for coordination
- Pass data, not services

---

## Summary

1. **Module = business area**, not technical function
2. **Public API only through `__init__.py`**
3. **Never import module internals**
4. **Same file structure in all modules**
5. **Routes → Services → Repository → Models**
6. **Business logic only in services**
7. **Cross-module coordination through workflows**
8. **FK through ID, no ORM relationships between modules**
9. **Utilities without business logic in `shared/`**
10. **Infrastructure in `core/`**
