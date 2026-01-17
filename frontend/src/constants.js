/**
 * Application constants
 * Centralizes all hardcoded values for better maintainability
 */

// Task Status
export const TASK_STATUS = {
  PENDING: 'pending',
  ACTIVE: 'active',
  COMPLETED: 'completed'
};

// Recurrence Types
export const RECURRENCE = {
  NONE: 'none',
  DAILY: 'daily',
  EVERY_N_DAYS: 'every_n_days',
  WEEKLY: 'weekly'
};

// Habit Types
export const HABIT_TYPE = {
  SKILL: 'skill',
  ROUTINE: 'routine'
};

// Energy Levels
export const ENERGY_LEVELS = [0, 1, 2, 3, 4, 5];

// Priority Levels
export const PRIORITY_LEVELS = [1, 2, 3, 4, 5];

// Navigation Views
export const VIEWS = {
  TODAY: 'today',
  PENDING: 'pending',
  HABITS: 'habits',
  HISTORY: 'history',
  POINTS: 'points',
  SETTINGS: 'settings'
};

// Default Settings Values
export const DEFAULT_SETTINGS = {
  daily_limit: 5,
  critical_days: 2,
  points_per_task_base: 10,
  points_per_habit_base: 10,
  energy_mult_base: 0.6,
  energy_mult_step: 0.2,
  minutes_per_energy_unit: 30,
  min_work_time_seconds: 120,
  idle_penalty: 30,
  missed_habit_penalty_base: 15,
  incomplete_penalty_percent: 0.5,
  completion_bonus_full: 0.1,
  completion_bonus_good: 0.05,
  progressive_penalty_factor: 0.1,
  progressive_penalty_max: 1.5,
  penalty_streak_reset_days: 2,
  routine_points_fixed: 6,
  streak_log_factor: 0.15,
  day_start_enabled: false,
  day_start_time: '06:00',
  roll_available_time: '00:00',
  auto_roll_enabled: false,
  auto_roll_time: '06:00',
  auto_penalty_enabled: false,
  auto_penalty_time: '00:01',
  auto_backup_enabled: false,
  auto_backup_time: '03:00',
  auto_backup_interval_hours: 24
};

// UI Constants
export const UI = {
  MAX_DESCRIPTION_LENGTH: 200,
  TOAST_DURATION: 3000,
  ANIMATION_DURATION: 300
};

// API Configuration
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  TIMEOUT: 10000
};

// Date Formats
export const DATE_FORMATS = {
  DISPLAY: 'YYYY-MM-DD',
  TIME: 'HH:mm',
  DATETIME: 'YYYY-MM-DD HH:mm:ss'
};

// Weekdays
export const WEEKDAYS = [
  { value: 0, label: 'Mon' },
  { value: 1, label: 'Tue' },
  { value: 2, label: 'Wed' },
  { value: 3, label: 'Thu' },
  { value: 4, label: 'Fri' },
  { value: 5, label: 'Sat' },
  { value: 6, label: 'Sun' }
];
