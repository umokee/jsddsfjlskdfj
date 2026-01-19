# APScheduler Monitoring

## Overview

The task manager now has full monitoring for the background scheduler (APScheduler) that handles automatic tasks like roll, penalties, and backups.

## Features

### Backend Statistics Tracking

The scheduler service (`backend/services/scheduler_service.py`) now tracks:

- **Uptime**: How long the scheduler has been running
- **Per-job statistics**:
  - Total checks performed
  - Total executions (actual work done)
  - Last check time
  - Last execution time
  - Last error (if any)
  - Next run time
  - Seconds until next run

### API Endpoint

**GET** `/api/scheduler/status`

Returns detailed scheduler status including:

```json
{
  "running": true,
  "started_at": "2024-01-20T10:30:00",
  "uptime_seconds": 3600,
  "uptime_human": "1h 0m 0s",
  "current_time": "2024-01-20T11:30:00",
  "jobs": [
    {
      "id": "check_auto_roll",
      "name": "check_auto_roll",
      "next_run_time": "2024-01-20T11:31:00",
      "seconds_until_next": 45,
      "checks": 60,
      "executions": 1,
      "last_check": "2024-01-20T11:30:00",
      "last_execution": "2024-01-20T06:00:00",
      "last_error": null
    },
    // ... other jobs
  ],
  "settings": {
    "auto_roll_enabled": true,
    "auto_roll_time": "06:00",
    "auto_penalties_enabled": true,
    "penalty_time": "00:01",
    "auto_backup_enabled": true,
    "backup_time": "03:00",
    "backup_interval_days": 1
  }
}
```

### Frontend UI

Navigate to **[🤖] SCHEDULER** tab to see:

#### Status Overview
- Scheduler running/stopped status
- Total uptime (human-readable)
- Start time
- Current time

#### Jobs Information
For each scheduled job (roll, penalties, backup):
- **Status badge**: ACTIVE (executed at least once), IDLE (never executed), ERROR (last execution failed)
- **Statistics**:
  - Total checks performed (how many times the job ran)
  - Total executions (how many times actual work was done)
  - Next run time (countdown in seconds)
- **Detailed information**:
  - Last check timestamp
  - Last execution timestamp
  - Last error message (if any)

#### Automation Settings
Shows which automation features are enabled/disabled:
- Auto Roll (with scheduled time)
- Auto Penalties (with scheduled time)
- Auto Backup (with scheduled time and interval)

#### Auto-Refresh
- Checkbox to enable/disable auto-refresh
- Refreshes every 10 seconds when enabled
- Manual refresh button

## Understanding the Statistics

### Checks vs Executions

- **Checks**: How many times the scheduler ran the job function (every minute by default)
- **Executions**: How many times the job actually did work

Example for `check_auto_roll`:
- Checks: 1440 (ran every minute for 24 hours)
- Executions: 1 (actually rolled once at 06:00)

This is normal! The job checks every minute but only executes when conditions are met.

### Status Badges

- **ACTIVE** (green): Job has executed at least once since startup
- **IDLE** (gray): Job has never executed (checking but conditions not met)
- **ERROR** (red): Last execution failed - check error message

### Troubleshooting

If you see:
- **Status: STOPPED**: Scheduler isn't running - restart the backend
- **High check count, 0 executions**: Normal if conditions haven't been met
- **ERROR badge**: Check the error message below the job details
- **Old "Last Check"**: Scheduler might be stuck - restart backend

## Technical Details

### Implementation

1. **Statistics Storage**: In-memory dictionary `scheduler_stats` in `scheduler_service.py`
2. **Tracking**: Each job function increments counters before/after execution
3. **Thread-safe**: APScheduler handles concurrency
4. **No database**: Statistics reset on restart (by design)

### Performance Impact

- Minimal: Just dictionary updates
- No database writes for statistics
- No impact on job execution speed

### Future Enhancements

Potential improvements:
- [ ] Persist statistics to database
- [ ] Historical graphs
- [ ] Alert notifications on errors
- [ ] Job control (pause/resume/trigger manually)
- [ ] Email notifications on failures

## API Usage Example

```javascript
import { schedulerApi } from './services/apiService';

// Get scheduler status
const response = await schedulerApi.getStatus();
console.log('Scheduler running:', response.data.running);
console.log('Uptime:', response.data.uptime_human);
```

## Configuration

No additional configuration needed! The monitoring is automatically enabled when the scheduler starts.

To disable auto-refresh in UI:
1. Go to [🤖] SCHEDULER tab
2. Uncheck "Auto-refresh (10s)"

## Benefits

1. **Visibility**: See exactly what the scheduler is doing
2. **Debugging**: Identify issues quickly with error messages
3. **Confidence**: Know that automation is working
4. **Diagnostics**: Understand execution patterns
5. **Peace of mind**: Monitor without checking logs
