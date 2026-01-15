/**
 * Format due date as "Today", "Tomorrow", or actual date
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date label
 */
export const formatDueDate = (dateString) => {
  if (!dateString) return null;

  const date = new Date(dateString);
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  // Reset time to compare only dates
  date.setHours(0, 0, 0, 0);
  today.setHours(0, 0, 0, 0);
  tomorrow.setHours(0, 0, 0, 0);

  if (date.getTime() === today.getTime()) {
    return 'Today';
  } else if (date.getTime() === tomorrow.getTime()) {
    return 'Tomorrow';
  } else {
    // Show date for anything 2+ days away
    return date.toLocaleDateString();
  }
};

/**
 * Check if date is today
 * @param {string} dateString - ISO date string
 * @returns {boolean}
 */
export const isToday = (dateString) => {
  if (!dateString) return false;
  const date = new Date(dateString);
  const today = new Date();
  return date.toDateString() === today.toDateString();
};

/**
 * Get sort priority for date (lower = higher priority)
 * @param {string} dateString - ISO date string
 * @returns {number} Sort priority (0=today, 1=tomorrow, 2+=future)
 */
export const getDateSortPriority = (dateString) => {
  if (!dateString) return 999; // No date = lowest priority

  const date = new Date(dateString);
  const today = new Date();

  // Reset time to compare only dates
  date.setHours(0, 0, 0, 0);
  today.setHours(0, 0, 0, 0);

  const diffDays = Math.floor((date - today) / (1000 * 60 * 60 * 24));

  if (diffDays < 0) {
    // Past dates go to bottom
    return 1000 + Math.abs(diffDays);
  }

  return diffDays; // 0=today, 1=tomorrow, 2=day after, etc.
};

/**
 * Sort tasks/habits by due date (today first, then tomorrow, etc.)
 * @param {Array} items - Array of tasks or habits
 * @returns {Array} Sorted array
 */
export const sortByDueDate = (items) => {
  return [...items].sort((a, b) => {
    const priorityA = getDateSortPriority(a.due_date);
    const priorityB = getDateSortPriority(b.due_date);
    return priorityA - priorityB;
  });
};
