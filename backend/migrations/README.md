# Database Migrations

This directory contains database migration scripts for schema changes.

## How to run migrations

### Method 1: Run migration script (Recommended)

```bash
# From project root directory
python backend/migrations/add_max_streak_bonus_days.py
```

The script will:
- Automatically detect your database location
- Check if the column already exists
- Add the column if needed
- Show success/error messages

### Method 2: Manual SQL (if you prefer)

```bash
# Find your database
sqlite3 /var/lib/task-manager/tasks.db
# OR if using local development
sqlite3 ./tasks.db
```

Then run:
```sql
-- Check if column exists
PRAGMA table_info(settings);

-- Add column if it doesn't exist
ALTER TABLE settings ADD COLUMN max_streak_bonus_days INTEGER DEFAULT 30 NOT NULL;

-- Verify
PRAGMA table_info(settings);
```

## After migration

Restart your backend service:
```bash
# If using systemd
sudo systemctl restart task-manager

# If running manually
# Kill the old process and start again
pkill -f "python.*backend/main.py"
python -m uvicorn backend.main:app --reload
```

## Migration History

- **add_max_streak_bonus_days.py** - Adds configurable max streak bonus days parameter
