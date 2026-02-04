/**
 * Get effective date based on day_start_time setting.
 * If day_start_enabled is true and current time < day_start_time,
 * returns yesterday's date.
 *
 * @param {Object} settings - Settings object with day_start_enabled and day_start_time
 * @returns {Date} Effective date (at midnight)
 */
export const getEffectiveDate = (settings) => {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  if (!settings?.day_start_enabled) {
    return today;
  }

  // Parse day_start_time (format "HH:MM")
  const timeStr = settings.day_start_time || "06:00";
  const [hourStr, minuteStr] = timeStr.split(':');
  const dayStartHour = parseInt(hourStr, 10) || 6;
  const dayStartMinute = parseInt(minuteStr, 10) || 0;

  // Compare current time with day start time
  const currentMinutes = now.getHours() * 60 + now.getMinutes();
  const startMinutes = dayStartHour * 60 + dayStartMinute;

  if (currentMinutes < startMinutes) {
    // Still in "yesterday"
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    return yesterday;
  }

  return today;
};

/**
 * Format due date as "Today", "Tomorrow", or actual date
 * Uses effective date when settings are provided
 *
 * @param {string} dateString - ISO date string
 * @param {Object} settings - Optional settings object for day_start_time
 * @returns {string} Formatted date label
 */
export const formatDueDate = (dateString, settings = null) => {
  if (!dateString) return null;

  const date = new Date(dateString);
  const effectiveToday = settings ? getEffectiveDate(settings) : new Date();
  const tomorrow = new Date(effectiveToday);
  tomorrow.setDate(tomorrow.getDate() + 1);

  // Reset time to compare only dates
  date.setHours(0, 0, 0, 0);
  effectiveToday.setHours(0, 0, 0, 0);
  tomorrow.setHours(0, 0, 0, 0);

  if (date.getTime() === effectiveToday.getTime()) {
    return 'Today';
  } else if (date.getTime() === tomorrow.getTime()) {
    return 'Tomorrow';
  } else {
    // Show date for anything 2+ days away
    return date.toLocaleDateString();
  }
};

/**
 * Check if date is today (using effective date with settings)
 *
 * @param {string} dateString - ISO date string
 * @param {Object} settings - Optional settings object for day_start_time
 * @returns {boolean}
 */
export const isToday = (dateString, settings = null) => {
  if (!dateString) return false;
  const date = new Date(dateString);
  const effectiveToday = settings ? getEffectiveDate(settings) : new Date();
  return date.toDateString() === effectiveToday.toDateString();
};

/**
 * Get sort priority for date (lower = higher priority)
 * Uses effective date when settings are provided
 *
 * @param {string} dateString - ISO date string
 * @param {Object} settings - Optional settings object for day_start_time
 * @returns {number} Sort priority (0=today, 1=tomorrow, 2+=future)
 */
export const getDateSortPriority = (dateString, settings = null) => {
  if (!dateString) return 999; // No date = lowest priority

  const date = new Date(dateString);
  const effectiveToday = settings ? getEffectiveDate(settings) : new Date();

  // Reset time to compare only dates
  date.setHours(0, 0, 0, 0);
  effectiveToday.setHours(0, 0, 0, 0);

  const diffDays = Math.floor((date - effectiveToday) / (1000 * 60 * 60 * 24));

  if (diffDays < 0) {
    // Past dates go to bottom
    return 1000 + Math.abs(diffDays);
  }

  return diffDays; // 0=today, 1=tomorrow, 2=day after, etc.
};

/**
 * Sort tasks/habits by due date (today first, then tomorrow, etc.)
 *
 * @param {Array} items - Array of tasks or habits
 * @param {Object} settings - Optional settings object for day_start_time
 * @returns {Array} Sorted array
 */
export const sortByDueDate = (items, settings = null) => {
  return [...items].sort((a, b) => {
    const priorityA = getDateSortPriority(a.due_date, settings);
    const priorityB = getDateSortPriority(b.due_date, settings);
    return priorityA - priorityB;
  });
};
