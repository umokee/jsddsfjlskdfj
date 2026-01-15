#!/usr/bin/env python3
"""
Database migration script to add time-based settings
Adds: roll_available_time, auto_penalties_enabled, auto_roll_enabled, auto_roll_time
"""

import sqlite3
import sys
from pathlib import Path

def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def migrate_database(db_path='task_manager.db'):
    """Add new time-based settings columns if they don't exist"""
    print(f"Migrating database: {db_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check and add roll_available_time column
        if not column_exists(cursor, 'settings', 'roll_available_time'):
            print("Adding roll_available_time column...")
            cursor.execute('ALTER TABLE settings ADD COLUMN roll_available_time VARCHAR DEFAULT "00:00"')
            print("✓ Added roll_available_time")
        else:
            print("✓ roll_available_time already exists")

        # Check and add auto_penalties_enabled column
        if not column_exists(cursor, 'settings', 'auto_penalties_enabled'):
            print("Adding auto_penalties_enabled column...")
            cursor.execute('ALTER TABLE settings ADD COLUMN auto_penalties_enabled BOOLEAN DEFAULT 1')
            print("✓ Added auto_penalties_enabled")
        else:
            print("✓ auto_penalties_enabled already exists")

        # Check and add auto_roll_enabled column
        if not column_exists(cursor, 'settings', 'auto_roll_enabled'):
            print("Adding auto_roll_enabled column...")
            cursor.execute('ALTER TABLE settings ADD COLUMN auto_roll_enabled BOOLEAN DEFAULT 0')
            print("✓ Added auto_roll_enabled")
        else:
            print("✓ auto_roll_enabled already exists")

        # Check and add auto_roll_time column
        if not column_exists(cursor, 'settings', 'auto_roll_time'):
            print("Adding auto_roll_time column...")
            cursor.execute('ALTER TABLE settings ADD COLUMN auto_roll_time VARCHAR DEFAULT "06:00"')
            print("✓ Added auto_roll_time")
        else:
            print("✓ auto_roll_time already exists")

        # Commit changes
        conn.commit()
        print("\n✅ Migration completed successfully!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        sys.exit(1)

    finally:
        conn.close()

if __name__ == "__main__":
    # Default database path
    db_path = Path(__file__).parent.parent / "task_manager.db"

    # Allow custom path from command line
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("Creating new database will happen automatically on first run.")
        sys.exit(1)

    migrate_database(str(db_path))
