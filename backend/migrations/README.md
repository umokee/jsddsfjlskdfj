# Automatic Database Migrations

This project uses an **automatic migration system** that detects and adds missing columns when the application starts.

## How it works

1. When the backend starts, it automatically:
   - Creates all missing tables (via SQLAlchemy's `create_all()`)
   - Compares SQLAlchemy models with the actual database schema
   - Adds any missing columns with their default values
   - Logs all changes to the console and log file

2. **You don't need to run any migration scripts manually!**

## What happens when you update

When you pull new code that adds database fields:

1. **Just restart the backend:**
   ```bash
   # If using systemd
   sudo systemctl restart task-manager

   # If running manually
   pkill -f "python.*backend/main.py"
   python -m uvicorn backend.main:app --reload
   ```

2. The auto-migration system will:
   - Detect new columns in the models
   - Add them to the database automatically
   - Show messages like: `✓ Added column: settings.max_streak_bonus_days`

3. **Your data is safe!** The system only ADDS columns, never deletes or modifies existing data.

## Manual migration (optional)

If you want to run migrations manually without starting the app:

```bash
# From project root
python -m backend.auto_migrate
```

## How to verify

Check the logs to see what migrations were applied:

```bash
# View recent logs
tail -f /var/log/task-manager/app.log

# Or if using local logs
tail -f logs/app.log
```

You should see messages like:
```
INFO - Starting automatic schema migration...
INFO - Adding column 'max_streak_bonus_days' to table 'settings'
INFO - ✓ Added column: settings.max_streak_bonus_days
INFO - ✓ Migration completed: 1 column(s) added
```

## Technical details

The auto-migration system (`backend/auto_migrate.py`):
- Uses SQLAlchemy's introspection to compare models with database
- Generates and executes `ALTER TABLE ADD COLUMN` statements
- Handles default values and NOT NULL constraints
- Supports all SQLAlchemy column types
- Is idempotent (safe to run multiple times)

## Limitations

The auto-migration system can:
- ✅ Add new columns
- ✅ Set default values
- ✅ Handle all SQLAlchemy types

The system cannot:
- ❌ Remove columns (must be done manually)
- ❌ Rename columns (must be done manually)
- ❌ Change column types (must be done manually)

For complex migrations (rename, remove, change type), create a manual migration script in this directory.
