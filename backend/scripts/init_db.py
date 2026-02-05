#!/usr/bin/env python3
"""
Database initialization script
Creates all tables and initializes default settings
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.database import engine, SessionLocal, Base
from backend import models  # Import all models to register them with Base

def init_database():
    """Initialize database with all tables and default settings"""
    print("Initializing database...")

    try:
        # Create all tables
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✓ All tables created successfully")

        # Initialize default settings if they don't exist
        print("Checking settings...")
        db = SessionLocal()
        try:
            from backend.modules.settings import SettingsService
            settings_service = SettingsService(db)
            settings = settings_service.get_data()
            print(f"✓ Settings already exist (ID: {settings.id})")
        except Exception as e:
            print(f"Settings not found, will be created on first API call")
        finally:
            db.close()

        print("\n✅ Database initialization completed successfully!")
        return 0

    except Exception as e:
        print(f"\n❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(init_database())
