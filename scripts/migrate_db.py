#!/usr/bin/env python3
"""
Database migration script to add missing columns to existing database.
Run this script to update your database schema without losing data.
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = "/var/lib/task-manager/tasks.db"

def migrate_database(db_path):
    """Add missing columns to tasks table"""
    print(f"Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check existing columns
    cursor.execute("PRAGMA table_info(tasks)")
    columns = {row[1] for row in cursor.fetchall()}
    print(f"Existing columns: {columns}")

    migrations = []

    # Add time_spent column if missing
    if 'time_spent' not in columns:
        migrations.append(("time_spent", "ALTER TABLE tasks ADD COLUMN time_spent INTEGER DEFAULT 0"))

    # Add recurrence_type column if missing
    if 'recurrence_type' not in columns:
        migrations.append(("recurrence_type", "ALTER TABLE tasks ADD COLUMN recurrence_type VARCHAR DEFAULT 'none'"))

    # Add recurrence_interval column if missing
    if 'recurrence_interval' not in columns:
        migrations.append(("recurrence_interval", "ALTER TABLE tasks ADD COLUMN recurrence_interval INTEGER DEFAULT 1"))

    # Add recurrence_days column if missing
    if 'recurrence_days' not in columns:
        migrations.append(("recurrence_days", "ALTER TABLE tasks ADD COLUMN recurrence_days VARCHAR"))

    # Add streak column if missing
    if 'streak' not in columns:
        migrations.append(("streak", "ALTER TABLE tasks ADD COLUMN streak INTEGER DEFAULT 0"))

    # Add last_completed_date column if missing
    if 'last_completed_date' not in columns:
        migrations.append(("last_completed_date", "ALTER TABLE tasks ADD COLUMN last_completed_date DATE"))

    # Run migrations
    if migrations:
        print(f"\nApplying {len(migrations)} migrations:")
        for col_name, sql in migrations:
            print(f"  - Adding column: {col_name}")
            try:
                cursor.execute(sql)
            except sqlite3.OperationalError as e:
                print(f"    Warning: {e}")

        conn.commit()
        print("\n✓ Migration completed successfully!")
    else:
        print("\n✓ Database is already up to date!")

    # Verify final schema
    cursor.execute("PRAGMA table_info(tasks)")
    final_columns = [row[1] for row in cursor.fetchall()]
    print(f"\nFinal columns: {final_columns}")

    conn.close()

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH

    if not Path(db_path).exists():
        print(f"Error: Database file not found: {db_path}")
        print(f"\nUsage: python3 migrate_db.py [path_to_database]")
        print(f"Default path: {DB_PATH}")
        sys.exit(1)

    # Backup database
    backup_path = Path(db_path).with_suffix('.db.backup')
    print(f"Creating backup: {backup_path}")
    import shutil
    shutil.copy2(db_path, backup_path)

    try:
        migrate_database(db_path)
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        print(f"Your original database is backed up at: {backup_path}")
        sys.exit(1)
