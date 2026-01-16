"""
Migration: Add max_streak_bonus_days column to settings table

Usage:
    python backend/migrations/add_max_streak_bonus_days.py
"""
import sqlite3
import os
from pathlib import Path

# Get database path
DB_DIR = os.getenv("TASK_MANAGER_DB_DIR", "/var/lib/task-manager")
DB_FILE = "tasks.db"

try:
    DB_PATH = Path(DB_DIR) / DB_FILE
    if not DB_PATH.exists():
        # Fallback to local directory
        DB_PATH = Path("./tasks.db")
except:
    DB_PATH = Path("./tasks.db")

print(f"Database path: {DB_PATH}")

# Connect to database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # Check if column already exists
    cursor.execute("PRAGMA table_info(settings)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'max_streak_bonus_days' in columns:
        print("✓ Column 'max_streak_bonus_days' already exists. No migration needed.")
    else:
        # Add the new column
        print("Adding column 'max_streak_bonus_days' to settings table...")
        cursor.execute("""
            ALTER TABLE settings
            ADD COLUMN max_streak_bonus_days INTEGER DEFAULT 30 NOT NULL
        """)
        conn.commit()
        print("✓ Migration completed successfully!")
        print("  - Added max_streak_bonus_days column with default value: 30")

except sqlite3.Error as e:
    print(f"✗ Migration failed: {e}")
    conn.rollback()
finally:
    conn.close()

print("\nYou can now restart the backend service.")
