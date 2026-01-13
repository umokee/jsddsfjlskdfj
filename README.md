# Task Manager with Points System

Comprehensive task and habit manager with gamification through a points system. Built with FastAPI backend and React frontend.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Points System](#points-system)
- [API Reference](#api-reference)
- [Settings Reference](#settings-reference)
- [Database Migration](#database-migration)
- [Deployment](#deployment)
- [Security](#security)

---

## Features

### Core Features
- **Task Management**: Priority (0-10), Energy (0-5), Due dates
- **Habit Tracking**: Daily habits with streak counting (max 30 days)
- **Task Dependencies**: Sequential task chains (Task B depends on Task A)
- **Daily Planning**: Smart "Roll" algorithm for daily task selection
- **Points System**: Comprehensive gamification with rewards and penalties
- **Goals**: Set point-based goals with reward tracking
- **Point Calculator**: Project future points based on performance

### Points System Features
- Automatic point calculation based on task completion
- Streak bonuses for habits (capped at 30 days)
- Energy-based multipliers
- Time efficiency bonuses
- Progressive penalties for consecutive days with penalties
- Separate penalties for tasks and habits
- Habit types: Skills (full points) vs Routines (50% points)
- Rest days support (no penalties)

### Technical Features
- API Key authentication
- Fail2ban integration for security
- SQLite database with automatic migrations
- Responsive terminal-style UI
- NixOS deployment module

---

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt

# Set API key (optional, default: "your-secret-key-change-me")
export TASK_MANAGER_API_KEY="your-secret-key"

# Run server
python -m backend.main
```

Backend runs on `http://localhost:8000`

### Frontend

```bash
cd frontend
npm install

# Set API key and URL in .env (or use defaults)
echo "VITE_API_KEY=your-secret-key" > .env
echo "VITE_API_URL=http://localhost:8000" >> .env

npm run dev
```

Frontend runs on `http://localhost:5173`

### First Run

1. Open `http://localhost:5173` in browser
2. The system creates default settings automatically
3. Create your first task or habit
4. Click "Roll Daily Plan" to select tasks for today
5. Complete tasks to earn points!

---

## Project Structure

```
umtask/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI app & all API endpoints
│   ├── models.py            # SQLAlchemy database models
│   ├── schemas.py           # Pydantic validation schemas
│   ├── crud.py              # Business logic & calculations
│   ├── auth.py              # API key authentication
│   ├── requirements.txt     # Python dependencies
│   ├── migrate_db.py        # Database migration script
│   └── tasks.db             # SQLite database (created on first run)
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── TaskForm.jsx         # Create/edit tasks
│   │   │   ├── TaskList.jsx         # Task list display
│   │   │   ├── HabitList.jsx        # Habit list display
│   │   │   ├── Timer.jsx            # Task timer
│   │   │   ├── Settings.jsx         # Points system settings
│   │   │   ├── PointsDisplay.jsx    # Points & history
│   │   │   ├── PointsGoals.jsx      # Goals management
│   │   │   └── PointsCalculator.jsx # Future projections
│   │   ├── App.jsx          # Main app component
│   │   ├── App.css          # Global styles
│   │   └── api.js           # Axios API client
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── deployment/
│   ├── nixos-module.nix     # NixOS service module
│   ├── NIXOS-SETUP.md       # NixOS deployment guide
│   └── FAIL2BAN.md          # Fail2ban setup guide
│
└── README.md                # This file
```

---

## Points System

### Overview

The points system gamifies task completion with rewards for productivity and penalties for inactivity.

### Earning Points

#### Task Completion

```
Base Points: 10 (configurable)
Energy Bonus: energy_level × energy_weight (default: 3.0)
Time Efficiency Bonus: (1 - time_taken/expected_time) × time_efficiency_weight (default: 0.5)

Formula:
points = base + (energy × weight) + efficiency_bonus
```

**Example:**
- Task with energy=3, completed in expected time
- Points = 10 + (3 × 3.0) + 0 = **19 points**

#### Habit Completion

```
Base Points: 10 (configurable)
Streak Bonus: min(current_streak, 30) × streak_multiplier (default: 1.0)
Habit Type Multiplier:
  - Skill: 1.0 (full points)
  - Routine: 0.5 (half points)

Formula:
points = (base + streak_bonus) × habit_type_multiplier
```

**Example:**
- Skill habit with 15-day streak
- Points = (10 + 15 × 1.0) × 1.0 = **25 points**

**Routine Example:**
- Routine habit (like "brush teeth") with 20-day streak
- Points = (10 + 20 × 1.0) × 0.5 = **15 points**

### Penalties

#### Idle Tasks Penalty
Applied when **0 tasks** completed in a day
- Default: -20 points
- Applied independently from habits

#### Idle Habits Penalty
Applied when **0 habits** completed in a day
- Default: -20 points
- Applied independently from tasks

#### Incomplete Day Penalty
Applied when completion rate < threshold
- Default: -20 points
- Threshold: 80% (configurable)
- Only applies if tasks were planned

#### Missed Habit Penalty
Applied for each uncompleted habit
```
Base Penalty: 50 (configurable)
Habit Type Multiplier:
  - Skill: 1.0
  - Routine: 0.5

Formula:
penalty = base × habit_type_multiplier
```

#### Progressive Penalties (Surge Pricing)

Penalties increase based on **penalty streak** (consecutive days WITH penalties):

```
Penalty Streak: Number of consecutive days with any penalty
Reset: After 3 consecutive days without penalties (configurable)

Formula:
final_penalty = base_penalty × (1 + factor × penalty_streak)

Where factor = progressive_penalty_factor (default: 0.5)
```

**Example:**
- Day 1: -20 penalty → streak = 1 → -20 × (1 + 0.5×1) = **-30 points**
- Day 2: -20 penalty → streak = 2 → -20 × (1 + 0.5×2) = **-40 points**
- Day 3: -20 penalty → streak = 3 → -20 × (1 + 0.5×3) = **-50 points**
- Day 4: No penalty for 1 day (streak still active)
- Day 5-7: No penalty for 3 days → **streak resets to 0**

### Task Dependencies

Tasks can depend on other tasks being completed first.

**Roll Algorithm Behavior:**
1. **Pass 1**: Select tasks with completed dependencies (or no dependencies)
2. **Pass 2**: If slots remain, select tasks whose dependency is in today's plan
3. Dependent tasks can be completed today after their dependency

**Example:**
- Task A: "Learn React" (no dependency)
- Task B: "Build React project" (depends on A)
- Roll selects A → B can also be selected (both in today's plan)

### Habit Types

**Skills** (habit_type='skill'):
- New habits you're building
- Full points and penalties
- Examples: Exercise, meditation, learning

**Routines** (habit_type='routine'):
- Easy daily tasks
- 50% points and penalties (configurable)
- Examples: Brush teeth, make bed, shower

### Rest Days

Special dates with no penalties applied:
- Create via API: `POST /api/rest-days`
- Examples: Holidays, vacation days, sick days
- Points earned normally, but no penalties

---

## API Reference

All endpoints require `X-API-Key` header with your API key.

### Tasks

#### Get All Tasks
```http
GET /api/tasks
```

Returns all tasks with calculated urgency.

#### Get Pending Tasks
```http
GET /api/tasks/pending
```

Returns pending tasks sorted by urgency (highest first).

#### Get Current Task
```http
GET /api/tasks/current
```

Returns currently active task, or next task if none active.

#### Get Today's Habits
```http
GET /api/tasks/habits
```

Returns all habits due today.

#### Get Today's Tasks
```http
GET /api/tasks/today
```

Returns all tasks marked for today (is_today=true).

#### Get Specific Task
```http
GET /api/tasks/{task_id}
```

Returns task by ID.

#### Create Task
```http
POST /api/tasks
Content-Type: application/json

{
  "description": "Task description",
  "project": "Project name",
  "priority": 5,
  "energy": 3,
  "is_habit": false,
  "is_today": false,
  "due_date": "2024-01-15T00:00:00",
  "depends_on": null,
  "habit_type": "skill",
  "recurrence_type": "none"
}
```

**Fields:**
- `description` (required): Task description
- `project`: Optional project name
- `priority`: 0-10, affects urgency calculation
- `energy`: 0-5, affects points and urgency
- `is_habit`: Is this a habit?
- `is_today`: Schedule for today?
- `due_date`: ISO datetime (time ignored, set to midnight)
- `depends_on`: ID of task this depends on (tasks only)
- `habit_type`: "skill" or "routine" (habits only)
- `recurrence_type`: "none", "daily", "every_n_days", "weekly" (habits only)

#### Update Task
```http
PUT /api/tasks/{task_id}
Content-Type: application/json

{
  "description": "Updated description",
  "priority": 7
}
```

#### Delete Task
```http
DELETE /api/tasks/{task_id}
```

### Task Actions

#### Start Task
```http
POST /api/tasks/start?task_id=123
```

Starts specified task (or next task if ID omitted). Stops any currently active task.

#### Stop Task
```http
POST /api/tasks/stop
```

Stops currently active task.

#### Complete Task
```http
POST /api/tasks/done?task_id=123
```

Completes specified task (or current task if ID omitted). Awards points.

#### Roll Daily Plan
```http
POST /api/tasks/roll?mood=3&daily_limit=5&critical_days=2
```

Generates daily task plan. Must be called once per day.

**Parameters:**
- `mood` (optional): 0-5, filters tasks by energy level
- `daily_limit`: Max tasks to select (default: 5)
- `critical_days`: Days until deadline for critical tasks (default: 2)

**Algorithm:**
1. Delete overdue habits from previous days
2. Clear is_today flag from all regular tasks
3. Select critical tasks (due within critical_days)
4. Fill remaining slots with tasks whose dependencies are met
5. If slots remain, add tasks whose dependency is in today's plan
6. Calculate penalties for yesterday
7. Update last_roll_date

### Points

#### Get Current Points
```http
GET /api/points/current
```

Returns total points accumulated.

#### Get Points History
```http
GET /api/points/history?days=7
```

Returns daily point history.

**Response:**
```json
[
  {
    "id": 1,
    "date": "2024-01-15",
    "points_earned": 45,
    "points_penalty": 20,
    "daily_total": 25,
    "tasks_completed": 3,
    "tasks_planned": 5,
    "habits_completed": 2,
    "completion_rate": 0.6,
    "penalty_streak": 1
  }
]
```

#### Get Points Projection
```http
GET /api/points/projection?target_date=2024-12-31
```

Projects future points based on last 30 days average.

**Response:**
```json
{
  "current_total": 500,
  "target_date": "2024-12-31",
  "days_until": 90,
  "avg_per_day": 10,
  "min_projection": 1130,
  "avg_projection": 1400,
  "max_projection": 1670
}
```

Projections:
- **Minimum**: 70% of average (pessimistic)
- **Average**: Current average (realistic)
- **Maximum**: 130% of average (optimistic)

### Goals

#### Get Goals
```http
GET /api/goals?include_achieved=false
```

Returns active goals (or all if include_achieved=true).

#### Create Goal
```http
POST /api/goals
Content-Type: application/json

{
  "target_points": 1000,
  "reward_description": "Buy new laptop",
  "deadline": "2024-12-31"
}
```

#### Update Goal
```http
PUT /api/goals/{goal_id}
Content-Type: application/json

{
  "reward_description": "Updated reward"
}
```

Goals are automatically marked as achieved when points reach target.

#### Delete Goal
```http
DELETE /api/goals/{goal_id}
```

### Rest Days

#### Get Rest Days
```http
GET /api/rest-days
```

Returns all rest days (future and past).

#### Create Rest Day
```http
POST /api/rest-days
Content-Type: application/json

{
  "date": "2024-12-25",
  "description": "Christmas"
}
```

#### Delete Rest Day
```http
DELETE /api/rest-days/{rest_day_id}
```

### Settings

#### Get Settings
```http
GET /api/settings
```

Returns current points system settings.

#### Update Settings
```http
PUT /api/settings
Content-Type: application/json

{
  "points_per_task_base": 15,
  "idle_tasks_penalty": 30
}
```

### Statistics

#### Get Daily Stats
```http
GET /api/stats
```

Returns statistics for current day.

**Response:**
```json
{
  "pending_tasks": 5,
  "completed_tasks": 3,
  "active_habits": 8,
  "completed_habits": 5,
  "total_time": 3600,
  "current_points": 500
}
```

---

## Settings Reference

All settings are configurable via Settings page in UI or API.

### Task Limits

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `max_tasks_per_day` | 10 | 1-100 | Maximum tasks in daily plan |

### Base Points

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `points_per_task_base` | 10 | 1-1000 | Base points per task |
| `points_per_habit_base` | 10 | 1-1000 | Base points per habit |

### Multipliers & Weights

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `streak_multiplier` | 1.0 | 0-10 | Points per streak day (capped at 30 days) |
| `energy_weight` | 3.0 | 0-20 | Points multiplier per energy level |
| `time_efficiency_weight` | 0.5 | 0-5 | Impact of time efficiency on points |

### Time Estimation

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `minutes_per_energy_unit` | 30 | 5-180 | Expected minutes per energy level |

**Example:**
- Energy 3 task = 3 × 30 = 90 minutes expected

### Penalties

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `incomplete_day_penalty` | 20 | 0-500 | Penalty for < threshold completion |
| `incomplete_day_threshold` | 0.8 | 0-1 | Minimum completion rate (80%) |
| `missed_habit_penalty_base` | 50 | 0-500 | Base penalty per missed habit |
| `progressive_penalty_factor` | 0.5 | 0-5 | Penalty streak multiplier |
| `penalty_streak_reset_days` | 3 | 1-30 | Days without penalty to reset streak |
| `idle_tasks_penalty` | 20 | 0-500 | Penalty for 0 tasks completed |
| `idle_habits_penalty` | 20 | 0-500 | Penalty for 0 habits completed |

### Habit Types

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `routine_habit_multiplier` | 0.5 | 0-1 | Points/penalty multiplier for routine habits |

---

## Database Migration

If upgrading from a previous version, run the migration script:

```bash
python backend/migrate_db.py
```

**This adds:**
- `depends_on` column to tasks (task dependencies)
- `habit_type` column to tasks (skill vs routine)
- `penalty_streak` column to point_history
- New penalty columns to settings
- `routine_habit_multiplier` to settings

The script is safe to run multiple times (checks if columns exist).

---

## Deployment

### Local Development

See [Quick Start](#quick-start) above.

### NixOS (Recommended)

Full automated deployment with:
- Git clone
- Frontend build
- Backend service
- Reverse proxy (Caddy)
- Fail2ban integration
- Automatic API key generation

**Minimal configuration:**

```nix
{ config, pkgs, ... }:
{
  imports = [
    /path/to/umtask/deployment/nixos-module.nix
  ];

  services.task-manager = {
    enable = true;
    domain = "tasks.example.com";  # Optional
  };
}
```

See `deployment/NIXOS-SETUP.md` for details.

### Docker (Coming Soon)

Docker deployment is planned but not yet available.

### Systemd (Manual)

1. Install dependencies
2. Create systemd service (see `deployment/systemd-service.example`)
3. Configure reverse proxy (Nginx/Caddy)
4. Set up Fail2ban (see `deployment/FAIL2BAN.md`)

---

## Security

### API Key Authentication

All API endpoints require `X-API-Key` header.

**Set custom key:**

```bash
# Backend
export TASK_MANAGER_API_KEY="your-secure-random-key"

# Frontend .env
VITE_API_KEY=your-secure-random-key
```

### Fail2ban Integration

Automatically logs failed authentication attempts with IP addresses.

**Default settings:**
- Max retries: 2
- Ban time: 52 weeks
- Find time: 1 day

See `deployment/FAIL2BAN.md` for setup.

### HTTPS

Use reverse proxy (Nginx/Caddy) for HTTPS in production.

NixOS module includes Caddy with automatic HTTPS.

---

## Technologies

**Backend:**
- FastAPI - Modern Python web framework
- SQLAlchemy - ORM for database
- SQLite - Embedded database
- Pydantic - Data validation

**Frontend:**
- React - UI library
- Vite - Build tool
- Axios - HTTP client
- Vanilla CSS - No framework, terminal-style theme

**Deployment:**
- NixOS - Declarative deployment
- Systemd - Service management
- Fail2ban - Security
- Caddy/Nginx - Reverse proxy

---

## License

MIT
