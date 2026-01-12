/**
 * Format seconds into human-readable time
 * @param {number} seconds - Total seconds
 * @returns {string} Formatted time string (e.g., "2h 30m", "45m", "30s")
 */
export function formatTimeSpent(seconds) {
  if (!seconds || seconds === 0) return '';

  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;

  const parts = [];
  if (h > 0) parts.push(`${h}h`);
  if (m > 0) parts.push(`${m}m`);
  if (s > 0 && h === 0) parts.push(`${s}s`); // Only show seconds if less than an hour

  return parts.join(' ');
}
