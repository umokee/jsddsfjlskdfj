# Project Architecture

## Backend Structure

The backend follows a clean layered architecture with clear separation of concerns:

```
backend/
├── infrastructure/          # Core infrastructure (database, migrations)
│   ├── database.py         # Database connection and session management
│   └── migrations.py       # Automatic schema migration system
│
├── middleware/             # Request/response processing
│   └── auth.py            # API key authentication
│
├── services/              # Business logic layer
│   ├── task_service.py    # Task lifecycle management
│   ├── points_service.py  # Points calculations and tracking
│   ├── penalty_service.py # Penalty calculation logic
│   ├── goal_service.py    # Goal and rest day management
│   ├── date_service.py    # Date calculations and effective date handling
│   ├── backup_service.py  # Database backup with Google Drive integration
│   └── scheduler_service.py # Background task scheduler (auto-roll, penalties, backups)
│
├── repositories/          # Data access layer (pure database queries)
│   ├── task_repository.py      # Task data access
│   ├── settings_repository.py  # Settings data access
│   └── points_repository.py    # Points, goals, and rest days data access
│
├── scripts/               # Utility scripts
│   ├── init_db.py         # Database initialization
│   ├── migrate_db.py      # Manual migration script
│   └── migrate_time_settings.py # Time settings migration
│
├── constants.py           # Application constants (no magic numbers!)
├── exceptions.py          # Custom exception classes
├── models.py              # SQLAlchemy ORM models
├── schemas.py             # Pydantic schemas for validation
├── crud.py                # Compatibility facade (delegates to services)
└── main.py                # FastAPI application entry point
```

## Architecture Layers

### 1. Infrastructure Layer (`infrastructure/`)
- **Purpose**: Core infrastructure components
- **Responsibilities**:
  - Database connection management
  - Schema migrations
  - Low-level infrastructure concerns
- **Key Principle**: No business logic

### 2. Middleware Layer (`middleware/`)
- **Purpose**: Request/response processing
- **Responsibilities**:
  - Authentication and authorization
  - Request validation
  - Response formatting
- **Key Principle**: Cross-cutting concerns

### 3. Service Layer (`services/`)
- **Purpose**: Business logic and orchestration
- **Responsibilities**:
  - Complex business operations
  - Coordination between multiple repositories
  - Transaction management
  - Business rule enforcement
- **Key Principle**: Each service has single responsibility
- **Services**:
  - `TaskService`: Complete task lifecycle (CRUD, start, stop, complete, roll)
  - `PointsService`: Points calculation and tracking
  - `PenaltyService`: Penalty calculation with progressive multipliers
  - `GoalService`: Goal management
  - `DateService`: Date calculations and effective date logic
  - `BackupService`: Database backup operations
  - `SchedulerService`: Background automated tasks

### 4. Repository Layer (`repositories/`)
- **Purpose**: Data access abstraction
- **Responsibilities**:
  - Database queries
  - CRUD operations
  - Data retrieval and persistence
- **Key Principle**: No business logic, only data access
- **Repositories**:
  - `TaskRepository`: Task queries
  - `SettingsRepository`: Settings queries
  - `PointHistoryRepository`: Point history queries
  - `PointGoalRepository`: Goal queries
  - `RestDayRepository`: Rest day queries

### 5. API Layer (`main.py`)
- **Purpose**: HTTP API endpoints
- **Responsibilities**:
  - Route definitions
  - Request/response handling
  - Error handling
  - API documentation
- **Key Principle**: Thin controllers - delegate to services

## Design Principles

### SOLID Principles Applied

1. **Single Responsibility Principle (SRP)**
   - Each service/repository has one clear responsibility
   - Example: `PointsService` only handles points, `PenaltyService` only handles penalties

2. **Open/Closed Principle (OCP)**
   - Services are open for extension but closed for modification
   - New features added through new services, not modifying existing ones

3. **Liskov Substitution Principle (LSP)**
   - Repository interfaces can be substituted with different implementations
   - Services depend on abstractions, not concrete implementations

4. **Interface Segregation Principle (ISP)**
   - Small, focused repositories instead of one large repository
   - Example: Separate `PointHistoryRepository`, `PointGoalRepository`, `RestDayRepository`

5. **Dependency Inversion Principle (DIP)**
   - High-level services depend on repository abstractions
   - Low-level repositories implement these abstractions

### Additional Design Patterns

1. **Facade Pattern**
   - `crud.py` acts as a facade for backward compatibility
   - Provides simple interface to complex subsystem

2. **Repository Pattern**
   - Abstracts data access logic
   - Allows easy testing with mock repositories

3. **Service Layer Pattern**
   - Encapsulates business logic
   - Coordinates operations across multiple repositories

## Data Flow

```
HTTP Request
    ↓
API Endpoint (main.py)
    ↓
Middleware (auth.py)
    ↓
Service Layer (services/)
    ↓
Repository Layer (repositories/)
    ↓
Database (infrastructure/database.py)
```

## Benefits of This Architecture

### Maintainability
- Clear separation of concerns
- Easy to locate and modify code
- Changes isolated to specific layers

### Testability
- Each layer can be tested independently
- Mock repositories for service testing
- Mock services for API testing

### Scalability
- Easy to add new features
- Services can be extracted to microservices if needed
- Horizontal scaling possible

### Readability
- Clear naming conventions
- Consistent structure
- Self-documenting code organization

### Extensibility
- New services can be added without modifying existing code
- Repository implementations can be swapped (e.g., PostgreSQL instead of SQLite)
- Easy to add caching, logging, monitoring

## Example: Task Completion Flow

```python
# 1. API Layer (main.py)
@app.post("/api/tasks/done")
async def complete_task(task_id: Optional[int] = None, db: Session = Depends(get_db)):
    # 2. Service Layer
    service = TaskService(db)
    task = service.complete_task(task_id)
    return task

# 3. Service Layer (services/task_service.py)
class TaskService:
    def complete_task(self, task_id: Optional[int] = None) -> Optional[Task]:
        # Get task
        task = self.task_repo.get_by_id(self.db, task_id)

        # Business logic
        task.status = TASK_STATUS_COMPLETED
        task.completed_at = datetime.now()

        # Handle habit recurrence
        if task.is_habit:
            self._handle_habit_completion(task)

        # Update task
        self.task_repo.update(self.db, task)

        # Award points (different service)
        self.points_service.add_task_completion_points(task)

        # Check goals (different service)
        self.points_service.check_goal_achievements()

        return task

# 4. Repository Layer (repositories/task_repository.py)
class TaskRepository:
    @staticmethod
    def update(db: Session, task: Task) -> Task:
        db.commit()
        db.refresh(task)
        return task
```

## Migration from Old Structure

The refactoring process:

1. **Before**: Monolithic `crud.py` (1,183 lines)
2. **After**:
   - Organized services (6 files, ~1,200 lines)
   - Organized repositories (3 files, ~400 lines)
   - Facade `crud.py` (298 lines)
   - Infrastructure properly separated

**Result**: 75% reduction in main file size, significantly better organization

## Best Practices

### When Adding New Features

1. **Identify the layer**: Is it business logic (service) or data access (repository)?
2. **Single responsibility**: Create new service/repository if needed
3. **Use existing patterns**: Follow established naming and structure
4. **Update constants**: Add new constants to `constants.py`
5. **Add exceptions**: Create custom exceptions in `exceptions.py` if needed
6. **Update facade**: Add compatibility methods to `crud.py` if needed

### Code Organization Rules

1. **Services** should:
   - Contain business logic
   - Coordinate multiple repositories
   - Handle transactions
   - Use other services for different domains

2. **Repositories** should:
   - Only access database
   - Return raw data/models
   - No business logic
   - Be simple and focused

3. **Constants** should:
   - Be in `constants.py`
   - Use UPPER_CASE naming
   - Be well-documented

4. **Exceptions** should:
   - Be specific and descriptive
   - Include relevant context
   - Inherit from `TaskManagerException`

## Frontend Integration

The frontend uses the API through a centralized service layer in `frontend/src/services/apiService.js`, which mirrors the backend's modular approach.

## Future Improvements

Potential enhancements while maintaining this architecture:

1. **Caching Layer**: Add Redis caching in repositories
2. **Message Queue**: Add async task processing with Celery/RabbitMQ
3. **Event System**: Implement event-driven architecture for loose coupling
4. **API Versioning**: Support multiple API versions
5. **GraphQL**: Add GraphQL layer on top of services
6. **Metrics**: Add Prometheus metrics in middleware
7. **Tracing**: Add distributed tracing with OpenTelemetry

All these can be added without breaking existing architecture.
