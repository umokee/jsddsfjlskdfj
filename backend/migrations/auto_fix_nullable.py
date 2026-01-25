"""
Automatic migration: Make target_points nullable

This script checks and fixes the point_goals table schema on backend startup.
"""

import logging
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def fix_target_points_nullable(db: Session):
    """
    Make target_points column nullable in point_goals table if it isn't already.

    SQLite doesn't support ALTER COLUMN, so we need to recreate the table.
    """
    try:
        # Check if point_goals table exists
        inspector = inspect(db.bind)
        if 'point_goals' not in inspector.get_table_names():
            logger.info("point_goals table doesn't exist yet, skipping migration")
            return

        # Check current schema using raw SQLquery
        result = db.execute(text("PRAGMA table_info(point_goals)"))
        columns = result.fetchall()

        target_points_col = None
        for col in columns:
            # Column info: (cid, name, type, notnull, dflt_value, pk)
            if col[1] == 'target_points':
                target_points_col = col
                break

        if not target_points_col:
            logger.info("target_points column doesn't exist, skipping migration")
            return

        # Check if already nullable (notnull=0 means nullable)
        is_nullable = target_points_col[3] == 0

        if is_nullable:
            logger.info("✓ target_points is already nullable")
            return

        logger.info("⚠ target_points is NOT NULL, starting migration...")

        # Recreate table with correct schema
        logger.info("Creating temporary table...")
        db.execute(text("""
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
        """))

        logger.info("Copying existing data...")
        db.execute(text("""
            INSERT INTO point_goals_new
            SELECT * FROM point_goals
        """))

        logger.info("Dropping old table...")
        db.execute(text("DROP TABLE point_goals"))

        logger.info("Renaming new table...")
        db.execute(text("ALTER TABLE point_goals_new RENAME TO point_goals"))

        logger.info("Recreating indexes...")
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_point_goals_id ON point_goals (id)"))

        db.commit()

        logger.info("✓ Migration completed: target_points is now nullable")

    except Exception as e:
        logger.error(f"✗ Migration failed: {e}")
        db.rollback()
        raise
