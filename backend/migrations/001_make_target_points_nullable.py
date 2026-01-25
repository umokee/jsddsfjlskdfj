#!/usr/bin/env python3
"""
Migration: Make target_points nullable in point_goals table

This migration modifies the point_goals table to allow target_points to be NULL,
which is required for project_completion goals that don't use target_points.

SQLite doesn't support ALTER COLUMN, so we need to recreate the table.
"""

import sqlite3
import sys
import os
from pathlib import Path

def migrate():
    """Run the migration"""
    # Determine database path - try production first
    production_path = Path("/var/lib/task-manager/tasks.db")

    if production_path.exists():
        db_path = production_path
    else:
        # Fallback to local
        db_path = Path("tasks.db")

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if target_points is already nullable
        cursor.execute("PRAGMA table_info(point_goals)")
        columns = cursor.fetchall()

        target_points_col = None
        for col in columns:
            if col[1] == 'target_points':
                target_points_col = col
                break

        if not target_points_col:
            print("Error: target_points column not found in point_goals table")
            return False

        # Column info: (cid, name, type, notnull, dflt_value, pk)
        is_nullable = target_points_col[3] == 0  # notnull=0 means nullable

        if is_nullable:
            print("✓ target_points is already nullable. No migration needed.")
            return True

        print("⚠ target_points is NOT NULL. Starting migration...")

        # Step 1: Create new table with correct schema
        print("Creating temporary table with correct schema...")
        cursor.execute("""
            CREATE TABLE point_goals_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_type VARCHAR DEFAULT 'points',
                target_points INTEGER,
                project_name VARCHAR,
                reward_description VARCHAR NOT NULL,
                reward_claimed BOOLEAN DEFAULT 0,
                reward_claimed_at DATETIME,
                deadline DATE,
                achieved BOOLEAN DEFAULT 0,
                achieved_date DATE,
                created_at DATETIME
            )
        """)

        # Step 2: Copy data from old table
        print("Copying existing data...")
        cursor.execute("""
            INSERT INTO point_goals_new
            SELECT * FROM point_goals
        """)

        rows_copied = cursor.rowcount
        print(f"✓ Copied {rows_copied} row(s)")

        # Step 3: Drop old table
        print("Dropping old table...")
        cursor.execute("DROP TABLE point_goals")

        # Step 4: Rename new table
        print("Renaming new table...")
        cursor.execute("ALTER TABLE point_goals_new RENAME TO point_goals")

        # Step 5: Recreate indexes
        print("Recreating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_point_goals_id ON point_goals (id)")

        # Commit changes
        conn.commit()

        print("✓ Migration completed successfully!")
        print("  - target_points is now nullable")
        print("  - All existing data preserved")

        return True

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
