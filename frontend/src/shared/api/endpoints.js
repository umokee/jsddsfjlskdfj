/**
 * API endpoints organized by feature.
 */
import client from './client';

/**
 * Tasks API
 */
export const taskApi = {
  getAll: () => client.get('/tasks'),
  getPending: () => client.get('/tasks/pending'),
  getCurrent: () => client.get('/tasks/current'),
  getHabits: () => client.get('/tasks/habits'),
  getToday: () => client.get('/tasks/today'),
  getTodayHabits: () => client.get('/tasks/today-habits'),
  getById: (id) => client.get(`/tasks/${id}`),
  create: (task) => client.post('/tasks', task),
  update: (id, task) => client.put(`/tasks/${id}`, task),
  delete: (id) => client.delete(`/tasks/${id}`),
  start: (taskId = null) => client.post('/tasks/start', null, { params: { task_id: taskId } }),
  stop: () => client.post('/tasks/stop'),
  complete: (taskId = null) => client.post('/tasks/done', null, { params: { task_id: taskId } }),
  roll: (mood = null) => client.post('/tasks/roll', null, { params: { mood } }),
  canRoll: () => client.get('/tasks/can-roll'),
  completeRoll: (mood) => client.post('/tasks/complete-roll', null, { params: { mood } }),
};

/**
 * Stats API
 */
export const statsApi = {
  get: () => client.get('/tasks/stats'),
};

/**
 * Settings API
 */
export const settingsApi = {
  get: () => client.get('/settings'),
  update: (settings) => client.put('/settings', settings),
};

/**
 * Points API
 */
export const pointsApi = {
  getCurrent: () => client.get('/points/current'),
  getHistory: (days = 30) => client.get('/points/history', { params: { days } }),
  getHistoryByDate: (date) => client.get(`/points/history/${date}`),
  getProjection: (targetDate) => client.get('/points/projection', { params: { target_date: targetDate } }),
};

/**
 * Goals API
 */
export const goalsApi = {
  getAll: (includeAchieved = false) => client.get('/goals', {
    params: { include_achieved: includeAchieved }
  }),
  create: (goal) => client.post('/goals', goal),
  update: (id, goal) => client.put(`/goals/${id}`, goal),
  delete: (id) => client.delete(`/goals/${id}`),
  claim: (id) => client.post(`/goals/${id}/claim`),
};

/**
 * Rest Days API
 */
export const restDaysApi = {
  getAll: () => client.get('/rest-days'),
  create: (restDay) => client.post('/rest-days', restDay),
  delete: (id) => client.delete(`/rest-days/${id}`),
};

/**
 * Backups API
 */
export const backupsApi = {
  getAll: () => client.get('/backups'),
  create: () => client.post('/backups/create'),
  download: (id) => client.get(`/backups/${id}/download`, { responseType: 'blob' }),
  delete: (id) => client.delete(`/backups/${id}`),
};
