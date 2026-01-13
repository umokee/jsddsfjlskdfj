#!/usr/bin/env python3
"""
Database migration script for adding new columns to existing tables.
Run this script to update your database schema without losing data.

Usage:
    python backend/migrate_db.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'tasks.db')

def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def migrate():
    """Add new columns to existing database"""
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        print("No migration needed - database will be created on first run")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    migrations_applied = []

    try:
        # 1. Add depends_on column to Task table
        if not column_exists(cursor, 'task', 'depends_on'):
            cursor.execute('ALTER TABLE task ADD COLUMN depends_on INTEGER')
            migrations_applied.append('Added depends_on column to Task table')

        # 2. Add habit_type column to Task table
        if not column_exists(cursor, 'task', 'habit_type'):
            cursor.execute('ALTER TABLE task ADD COLUMN habit_type VARCHAR DEFAULT "skill"')
            migrations_applied.append('Added habit_type column to Task table')

        # 3. Add penalty_streak column to PointHistory table
        if not column_exists(cursor, 'point_history', 'penalty_streak'):
            cursor.execute('ALTER TABLE point_history ADD COLUMN penalty_streak INTEGER DEFAULT 0')
            migrations_applied.append('Added penalty_streak column to PointHistory table')

        # 4. Update Settings table - add new penalty columns
        if not column_exists(cursor, 'settings', 'idle_tasks_penalty'):
            cursor.execute('ALTER TABLE settings ADD COLUMN idle_tasks_penalty INTEGER DEFAULT 20')
            migrations_applied.append('Added idle_tasks_penalty column to Settings table')

        if not column_exists(cursor, 'settings', 'idle_habits_penalty'):
            cursor.execute('ALTER TABLE settings ADD COLUMN idle_habits_penalty INTEGER DEFAULT 20')
            migrations_applied.append('Added idle_habits_penalty column to Settings table')

        if not column_exists(cursor, 'settings', 'penalty_streak_reset_days'):
            cursor.execute('ALTER TABLE settings ADD COLUMN penalty_streak_reset_days INTEGER DEFAULT 3')
            migrations_applied.append('Added penalty_streak_reset_days column to Settings table')

        if not column_exists(cursor, 'settings', 'routine_habit_multiplier'):
            cursor.execute('ALTER TABLE settings ADD COLUMN routine_habit_multiplier FLOAT DEFAULT 0.5')
            migrations_applied.append('Added routine_habit_multiplier column to Settings table')

        # 5. Remove old idle_day_penalty column if it exists (optional - we can keep it for backwards compatibility)
        # Note: SQLite doesn't support DROP COLUMN in older versions, so we'll keep it

        conn.commit()

        if migrations_applied:
            print("✅ Database migration completed successfully!")
            print("\nMigrations applied:")
            for migration in migrations_applied:
                print(f"  - {migration}")
        else:
            print("✅ Database is already up to date - no migrations needed")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
