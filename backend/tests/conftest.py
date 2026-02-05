"""
Pytest configuration and fixtures for backend tests.
"""
import pytest
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.core.database import Base
from backend.models import Task, Settings, PointHistory, RestDay


@pytest.fixture(scope="function")
def db_engine():
    """Create in-memory SQLite database for testing"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create database session for testing"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def default_settings(db_session):
    """Create default settings for testing"""
    settings = Settings(
        id=1,
        max_tasks_per_day=10,
        points_per_task_base=10,
        points_per_habit_base=10,
        energy_mult_base=0.6,
        energy_mult_step=0.2,
        minutes_per_energy_unit=20,
        min_work_time_seconds=120,
        streak_log_factor=0.15,
        routine_points_fixed=6,
        completion_bonus_full=0.10,
        completion_bonus_good=0.05,
        idle_penalty=30,
        incomplete_penalty_percent=0.5,
        missed_habit_penalty_base=15,
        progressive_penalty_factor=0.1,
        progressive_penalty_max=1.5,
        penalty_streak_reset_days=2,
        day_start_enabled=False,
        day_start_time="06:00"
    )
    db_session.add(settings)
    db_session.commit()
    return settings


@pytest.fixture
def today():
    """Return today's date"""
    return date.today()


@pytest.fixture
def yesterday(today):
    """Return yesterday's date"""
    return today - timedelta(days=1)


@pytest.fixture
def sample_task(db_session, today):
    """Create a sample task"""
    task = Task(
        description="Test task",
        project="Test",
        priority=5,
        energy=3,
        status="pending",
        is_habit=False,
        is_today=True,
        created_at=datetime.now()
    )
    db_session.add(task)
    db_session.commit()
    return task


@pytest.fixture
def sample_habit(db_session, today):
    """Create a sample habit"""
    habit = Task(
        description="Test habit",
        project=None,
        priority=5,
        energy=2,
        status="pending",
        is_habit=True,
        is_today=False,
        recurrence_type="daily",
        habit_type="skill",
        due_date=datetime.combine(today, datetime.min.time()),
        created_at=datetime.now()
    )
    db_session.add(habit)
    db_session.commit()
    return habit


@pytest.fixture
def point_history(db_session, today):
    """Create point history for today"""
    history = PointHistory(
        date=today,
        points_earned=0,
        points_penalty=0,
        points_bonus=0,
        daily_total=0,
        cumulative_total=100,
        tasks_completed=0,
        habits_completed=0,
        tasks_planned=0,
        completion_rate=0.0,
        penalty_streak=0
    )
    db_session.add(history)
    db_session.commit()
    return history


def create_history_with_penalties(db_session, target_date, penalty, streak, cumulative=100):
    """Helper to create history with specific penalty values"""
    import json
    history = PointHistory(
        date=target_date,
        points_earned=0,
        points_penalty=penalty,
        points_bonus=0,
        daily_total=-penalty,
        cumulative_total=cumulative,
        tasks_completed=0,
        habits_completed=0,
        tasks_planned=0,
        completion_rate=0.0,
        penalty_streak=streak,
        details=json.dumps({"penalty_breakdown": {"total_penalty": penalty}}) if penalty > 0 else None
    )
    db_session.add(history)
    db_session.commit()
    return history
