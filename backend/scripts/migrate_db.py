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

        # === BALANCED PROGRESS v2.0 MIGRATIONS ===

        # Energy multiplier settings
        if not column_exists(cursor, 'settings', 'energy_mult_base'):
            cursor.execute('ALTER TABLE settings ADD COLUMN energy_mult_base FLOAT DEFAULT 0.6')
            migrations_applied.append('Added energy_mult_base column to Settings table')

        if not column_exists(cursor, 'settings', 'energy_mult_step'):
            cursor.execute('ALTER TABLE settings ADD COLUMN energy_mult_step FLOAT DEFAULT 0.2')
            migrations_applied.append('Added energy_mult_step column to Settings table')

        # Time quality settings
        if not column_exists(cursor, 'settings', 'min_work_time_seconds'):
            cursor.execute('ALTER TABLE settings ADD COLUMN min_work_time_seconds INTEGER DEFAULT 120')
            migrations_applied.append('Added min_work_time_seconds column to Settings table')

        # Streak settings
        if not column_exists(cursor, 'settings', 'streak_log_factor'):
            cursor.execute('ALTER TABLE settings ADD COLUMN streak_log_factor FLOAT DEFAULT 0.15')
            migrations_applied.append('Added streak_log_factor column to Settings table')

        # Routine habits
        if not column_exists(cursor, 'settings', 'routine_points_fixed'):
            cursor.execute('ALTER TABLE settings ADD COLUMN routine_points_fixed INTEGER DEFAULT 6')
            migrations_applied.append('Added routine_points_fixed column to Settings table')

        # Daily completion bonus
        if not column_exists(cursor, 'settings', 'completion_bonus_full'):
            cursor.execute('ALTER TABLE settings ADD COLUMN completion_bonus_full FLOAT DEFAULT 0.10')
            migrations_applied.append('Added completion_bonus_full column to Settings table')

        if not column_exists(cursor, 'settings', 'completion_bonus_good'):
            cursor.execute('ALTER TABLE settings ADD COLUMN completion_bonus_good FLOAT DEFAULT 0.05')
            migrations_applied.append('Added completion_bonus_good column to Settings table')

        # New penalty settings
        if not column_exists(cursor, 'settings', 'idle_penalty'):
            cursor.execute('ALTER TABLE settings ADD COLUMN idle_penalty INTEGER DEFAULT 30')
            migrations_applied.append('Added idle_penalty column to Settings table')

        if not column_exists(cursor, 'settings', 'incomplete_threshold_severe'):
            cursor.execute('ALTER TABLE settings ADD COLUMN incomplete_threshold_severe FLOAT DEFAULT 0.4')
            migrations_applied.append('Added incomplete_threshold_severe column to Settings table')

        if not column_exists(cursor, 'settings', 'incomplete_penalty_severe'):
            cursor.execute('ALTER TABLE settings ADD COLUMN incomplete_penalty_severe INTEGER DEFAULT 15')
            migrations_applied.append('Added incomplete_penalty_severe column to Settings table')

        if not column_exists(cursor, 'settings', 'progressive_penalty_max'):
            cursor.execute('ALTER TABLE settings ADD COLUMN progressive_penalty_max FLOAT DEFAULT 1.5')
            migrations_applied.append('Added progressive_penalty_max column to Settings table')

        # Day boundary settings for shifted schedules
        if not column_exists(cursor, 'settings', 'day_start_enabled'):
            cursor.execute('ALTER TABLE settings ADD COLUMN day_start_enabled BOOLEAN DEFAULT 0')
            migrations_applied.append('Added day_start_enabled column to Settings table')

        if not column_exists(cursor, 'settings', 'day_start_time'):
            cursor.execute('ALTER TABLE settings ADD COLUMN day_start_time VARCHAR DEFAULT "06:00"')
            migrations_applied.append('Added day_start_time column to Settings table')

        # Percent-based incomplete penalty (replaces fixed thresholds)
        if not column_exists(cursor, 'settings', 'incomplete_penalty_percent'):
            cursor.execute('ALTER TABLE settings ADD COLUMN incomplete_penalty_percent FLOAT DEFAULT 0.5')
            migrations_applied.append('Added incomplete_penalty_percent column to Settings table')

        # Morning Check-in feature
        if not column_exists(cursor, 'settings', 'pending_roll'):
            cursor.execute('ALTER TABLE settings ADD COLUMN pending_roll BOOLEAN DEFAULT 0')
            migrations_applied.append('Added pending_roll column to Settings table (Morning Check-in feature)')

        # Update existing settings to v2.0 defaults
        # Update minutes_per_energy_unit from 30 to 20
        cursor.execute('UPDATE settings SET minutes_per_energy_unit = 20 WHERE minutes_per_energy_unit = 30')
        # Update missed_habit_penalty_base from 50 to 15
        cursor.execute('UPDATE settings SET missed_habit_penalty_base = 15 WHERE missed_habit_penalty_base = 50')
        # Update penalty_streak_reset_days from 3 to 2
        cursor.execute('UPDATE settings SET penalty_streak_reset_days = 2 WHERE penalty_streak_reset_days = 3')
        # Update incomplete_day_threshold from 0.8 to 0.6
        cursor.execute('UPDATE settings SET incomplete_day_threshold = 0.6 WHERE incomplete_day_threshold = 0.8')
        # Update incomplete_day_penalty from 20 to 10
        cursor.execute('UPDATE settings SET incomplete_day_penalty = 10 WHERE incomplete_day_penalty = 20')
        # Update progressive_penalty_factor from 0.5 to 0.1
        cursor.execute('UPDATE settings SET progressive_penalty_factor = 0.1 WHERE progressive_penalty_factor = 0.5')

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
