# Database Migration Guide

## Problem

If you see "Failed to create task" error, it means your database schema is out of date. New columns were added:
- `time_spent` - tracks accumulated time on tasks
- `recurrence_type`, `recurrence_interval`, `recurrence_days` - habit recurrence settings
- `streak`, `last_completed_date` - habit streak tracking

## Solution: Run Migration Script

The migration script adds missing columns to your existing database **without losing data**.

### On Production Server:

```bash
# Stop the backend
sudo systemctl stop task-manager-backend

# Run migration (automatic backup included)
cd /var/lib/task-manager
python3 scripts/migrate_db.py /var/lib/task-manager/tasks.db

# Start the backend
sudo systemctl start task-manager-backend
```

### On Development:

```bash
# Run migration for local database
python3 scripts/migrate_db.py ./tasks.db

# Or just delete and recreate
rm tasks.db
python3 -m uvicorn backend.main:app --reload
```

## What the Script Does:

1. **Creates backup** → `tasks.db.backup`
2. **Checks existing columns** → Shows what you have
3. **Adds missing columns** → Only adds what's missing
4. **Verifies schema** → Shows final result

## Alternative: Fresh Start

If you don't need existing data:

```bash
sudo systemctl stop task-manager-backend
sudo rm /var/lib/task-manager/tasks.db
sudo systemctl start task-manager-backend
```

The backend will create a new database with the correct schema automatically.

## Troubleshooting

**Error: "Database file not found"**
- Check if path is correct: `/var/lib/task-manager/tasks.db`
- Or specify custom path: `python3 scripts/migrate_db.py /path/to/tasks.db`

**Error: "Permission denied"**
- Run with sudo: `sudo python3 scripts/migrate_db.py ...`
- Or change database permissions

**Migration successful but still getting errors**
- Restart backend service: `sudo systemctl restart task-manager-backend`
- Check logs: `journalctl -u task-manager-backend -n 50`
