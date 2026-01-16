"""
Automatic database migration system.
Compares SQLAlchemy models with actual database schema and adds missing columns.
"""
import sqlite3
import logging
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from backend.database import engine, Base
from backend import models  # Import to register all models

logger = logging.getLogger("task_manager.migrations")


def get_table_columns(conn: sqlite3.Connection, table_name: str) -> dict:
    """Get existing columns from database table"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = {}
    for row in cursor.fetchall():
        # row: (cid, name, type, notnull, dflt_value, pk)
        columns[row[1]] = {
            'type': row[2],
            'notnull': row[3],
            'default': row[4],
            'pk': row[5]
        }
    return columns


def sqlalchemy_type_to_sqlite(sa_type: str) -> str:
    """Convert SQLAlchemy type to SQLite type"""
    sa_type_upper = str(sa_type).upper()

    if 'INTEGER' in sa_type_upper or 'BIGINT' in sa_type_upper:
        return 'INTEGER'
    elif 'VARCHAR' in sa_type_upper or 'TEXT' in sa_type_upper or 'STRING' in sa_type_upper:
        return 'TEXT'
    elif 'FLOAT' in sa_type_upper or 'NUMERIC' in sa_type_upper or 'REAL' in sa_type_upper:
        return 'REAL'
    elif 'BOOLEAN' in sa_type_upper:
        return 'INTEGER'  # SQLite stores booleans as integers
    elif 'DATE' in sa_type_upper or 'TIME' in sa_type_upper:
        return 'TEXT'  # SQLite stores dates as text
    else:
        return 'TEXT'  # Default fallback


def get_default_value(column) -> str:
    """Get default value for a column in SQL format"""
    if column.default is None:
        return 'NULL'

    default = column.default

    # Handle ColumnDefault
    if hasattr(default, 'arg'):
        value = default.arg

        # Handle callable defaults (like datetime.utcnow)
        if callable(value):
            # For datetime functions, use SQLite's CURRENT_TIMESTAMP
            if 'datetime' in str(value):
                return 'CURRENT_TIMESTAMP'
            return 'NULL'  # Can't represent other callables as SQL defaults

        # Handle direct values
        if isinstance(value, bool):
            return '1' if value else '0'
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            return f"'{value}'"
        else:
            return 'NULL'

    return 'NULL'


def auto_migrate():
    """
    Automatically migrate database schema.
    Adds missing columns based on SQLAlchemy models.
    """
    logger.info("Starting automatic schema migration...")

    # Get database connection
    conn = engine.raw_connection()
    cursor = conn.cursor()

    # Get all tables from SQLAlchemy models
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    migrations_applied = 0

    try:
        # Iterate through all mapped classes
        for table_name, table in Base.metadata.tables.items():
            if table_name not in existing_tables:
                logger.warning(f"Table '{table_name}' doesn't exist. Run Base.metadata.create_all() first.")
                continue

            # Get existing columns from database
            existing_columns = get_table_columns(conn, table_name)

            # Check each column from the model
            for column in table.columns:
                column_name = column.name

                if column_name not in existing_columns:
                    # Column is missing - add it
                    sqlite_type = sqlalchemy_type_to_sqlite(column.type)
                    default_value = get_default_value(column)
                    nullable = column.nullable

                    # Build ALTER TABLE statement
                    alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sqlite_type}"

                    # Add DEFAULT if specified
                    if default_value != 'NULL':
                        alter_sql += f" DEFAULT {default_value}"

                    # Add NOT NULL if specified and default is provided
                    # (SQLite requires default for NOT NULL columns in ALTER TABLE)
                    if not nullable and default_value != 'NULL':
                        alter_sql += " NOT NULL"

                    logger.info(f"Adding column '{column_name}' to table '{table_name}'")
                    logger.debug(f"SQL: {alter_sql}")

                    try:
                        cursor.execute(alter_sql)
                        migrations_applied += 1
                        logger.info(f"✓ Added column: {table_name}.{column_name}")
                    except sqlite3.Error as e:
                        logger.error(f"✗ Failed to add column {table_name}.{column_name}: {e}")

        conn.commit()

        if migrations_applied > 0:
            logger.info(f"✓ Migration completed: {migrations_applied} column(s) added")
        else:
            logger.info("✓ Schema is up to date - no migrations needed")

    except Exception as e:
        logger.error(f"✗ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

    return migrations_applied


if __name__ == "__main__":
    # Allow running as standalone script
    logging.basicConfig(level=logging.INFO)
    auto_migrate()
