# Project Structure - Clean Architecture

## 📁 Complete Backend Structure

```
backend/
│
├── 📦 infrastructure/           # Core Infrastructure Layer
│   ├── __init__.py
│   ├── database.py             # Database connection & session management
│   └── migrations.py           # Automatic schema migrations
│
├── 🔒 middleware/              # Middleware Layer
│   ├── __init__.py
│   └── auth.py                 # API key authentication
│
├── 🎯 services/                # Business Logic Layer
│   ├── __init__.py
│   ├── backup_service.py       # Database backup & Google Drive integration
│   ├── date_service.py         # Date calculations & effective date logic
│   ├── goal_service.py         # Goal & rest day management
│   ├── penalty_service.py      # Penalty calculation with progressive multipliers
│   ├── points_service.py       # Points calculations & tracking
│   ├── scheduler_service.py    # Background task scheduler (auto-roll, penalties)
│   └── task_service.py         # Task lifecycle management (CRUD, start, stop, complete)
│
├── 💾 repositories/            # Data Access Layer
│   ├── __init__.py
│   ├── points_repository.py    # Point history, goals, rest days queries
│   ├── settings_repository.py  # Settings queries
│   └── task_repository.py      # Task queries
│
├── 🛠️  scripts/                # Utility Scripts
│   ├── __init__.py
│   ├── init_db.py             # Database initialization
│   ├── migrate_db.py          # Manual migration script
│   └── migrate_time_settings.py # Time settings migration
│
├── 📝 Core Files
│   ├── __init__.py
│   ├── constants.py           # All application constants (no magic numbers!)
│   ├── exceptions.py          # Custom exception classes
│   ├── models.py              # SQLAlchemy ORM models
│   ├── schemas.py             # Pydantic validation schemas
│   ├── crud.py                # Compatibility facade (298 lines, was 1,183)
│   └── main.py                # FastAPI application entry point
│
└── 📚 Documentation
    ├── ARCHITECTURE.md         # Detailed architecture documentation
    ├── REFACTORING_SUMMARY.md  # Refactoring changes summary
    └── PROJECT_STRUCTURE.md    # This file
```

## 📊 Statistics

### File Count by Layer
- **Infrastructure**: 2 files
- **Middleware**: 1 file
- **Services**: 7 files
- **Repositories**: 3 files
- **Scripts**: 3 files
- **Core**: 6 files

**Total**: 22 Python files + 5 `__init__.py` = **27 files**

### Code Reduction
- **Before**: crud.py (1,183 lines) + scattered files
- **After**:
  - crud.py facade: 298 lines (75% reduction)
  - Well-organized services: ~2,000 lines in focused modules
  - Clear repositories: ~400 lines

## 🏗️ Architecture Layers

### Layer Flow (Bottom to Top)

```
┌─────────────────────────────────────────┐
│         FastAPI Endpoints               │ ← API Layer (main.py)
│         (HTTP Routes)                   │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│         Middleware                      │ ← Authentication
│         (auth.py)                       │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│         Services                        │ ← Business Logic
│  (task, points, penalty, goal, etc.)   │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│         Repositories                    │ ← Data Access
│  (task, settings, points)               │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│         Infrastructure                  │ ← Database
│  (database, migrations)                 │
└─────────────────────────────────────────┘
```

## 🎨 Design Principles Applied

### SOLID Principles ✅
- ✓ **Single Responsibility**: Each service/repository has one clear purpose
- ✓ **Open/Closed**: Open for extension, closed for modification
- ✓ **Liskov Substitution**: Repository interfaces are substitutable
- ✓ **Interface Segregation**: Small, focused interfaces
- ✓ **Dependency Inversion**: High-level depends on abstractions

### Additional Patterns ✅
- ✓ **Repository Pattern**: Abstracts data access
- ✓ **Service Layer Pattern**: Encapsulates business logic
- ✓ **Facade Pattern**: crud.py provides backward compatibility

## 📖 Quick Reference Guide

### Finding Code by Purpose

| I need to... | Look in... |
|--------------|------------|
| Add business logic | `services/` |
| Add database query | `repositories/` |
| Add API endpoint | `main.py` |
| Add constant | `constants.py` |
| Add exception type | `exceptions.py` |
| Add authentication logic | `middleware/` |
| Add database migration | `infrastructure/migrations.py` |
| Create utility script | `scripts/` |

### Common Tasks

#### Adding a New Feature
1. Define constants in `constants.py`
2. Add models in `models.py` (if needed)
3. Add schemas in `schemas.py` (if needed)
4. Create repository methods in `repositories/`
5. Create service methods in `services/`
6. Add API endpoints in `main.py`
7. Update `crud.py` facade (if needed for compatibility)

#### Adding a New Service
1. Create `services/my_service.py`
2. Define service class with clear responsibility
3. Inject database session and needed repositories
4. Implement business logic methods
5. Use from other services or API endpoints

## 🚀 Benefits

### For Developers
- **Easy Navigation**: Find files by their purpose instantly
- **Clear Boundaries**: Know where to put new code
- **No Confusion**: Each file has a clear, single responsibility
- **Fast Onboarding**: New developers understand structure quickly

### For Maintenance
- **Isolated Changes**: Changes affect only relevant layers
- **Easy Testing**: Mock repositories, test services independently
- **Refactoring Safe**: Change implementation without breaking interfaces
- **Bug Fixing**: Know exactly where to look

### For Scaling
- **Horizontal Scaling**: Services can be extracted to microservices
- **Vertical Scaling**: Add features without touching existing code
- **Team Scaling**: Different teams can work on different layers
- **Performance**: Easy to add caching at repository level

## 🎯 Code Quality Metrics

### Before Refactoring
- ❌ Monolithic files (1,183 lines)
- ❌ Mixed responsibilities
- ❌ Code duplication (18+ instances)
- ❌ Magic numbers everywhere
- ❌ Poor separation of concerns
- ❌ Difficult to test
- ❌ Hard to extend

### After Refactoring
- ✅ Modular structure (max 400 lines per file)
- ✅ Single responsibility per module
- ✅ Zero duplication (centralized constants)
- ✅ Named constants for all values
- ✅ Clear layer separation
- ✅ Easy to test (mockable layers)
- ✅ Easy to extend (add new services)

## 📚 Documentation Files

1. **ARCHITECTURE.md**: Detailed architecture explanation with examples
2. **REFACTORING_SUMMARY.md**: Complete refactoring history and metrics
3. **PROJECT_STRUCTURE.md**: This file - quick reference for structure

## 🔄 Migration Path

All existing code continues to work through the `crud.py` facade, which delegates to the new services. No breaking changes!

## 🎓 Learning Resources

To understand this architecture:
1. Start with `ARCHITECTURE.md` for detailed explanation
2. Read `REFACTORING_SUMMARY.md` to see the transformation
3. Explore `services/task_service.py` for a complete example
4. Check `repositories/task_repository.py` for data access patterns

## ✨ Future Improvements

The structure supports adding:
- [ ] GraphQL API layer
- [ ] Redis caching in repositories
- [ ] Event-driven architecture
- [ ] Async task queues (Celery)
- [ ] Distributed tracing
- [ ] API versioning
- [ ] WebSocket support

All without breaking existing code! 🎉
