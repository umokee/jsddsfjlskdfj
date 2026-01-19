/**
 * Centralized API service
 * Handles all HTTP requests with proper error handling and authentication
 */
import axios from 'axios';
import { API_CONFIG } from '../constants';

// API Configuration
const API_URL = import.meta.env.VITE_API_URL || (
  import.meta.env.DEV ? 'http://localhost:8000' : ''
);
const API_BASE = `${API_URL}/api`;

// API Key Management
let apiKey = localStorage.getItem('taskManagerApiKey') || import.meta.env.VITE_API_KEY || '';

export const setApiKey = (key) => {
  apiKey = key;
  localStorage.setItem('taskManagerApiKey', key);
};

export const getApiKey = () => apiKey;

export const clearApiKey = () => {
  apiKey = '';
  localStorage.removeItem('taskManagerApiKey');
};

// Axios Instance
const api = axios.create({
  baseURL: API_BASE,
  timeout: API_CONFIG.TIMEOUT
});

// Request Interceptor
api.interceptors.request.use(
  (config) => {
    if (apiKey) {
      config.headers['X-API-Key'] = apiKey;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Enhanced error handling
    if (error.response) {
      // Server responded with error
      const { status, data } = error.response;
      console.error(`API Error ${status}:`, data);

      if (status === 401) {
        // Unauthorized - clear API key
        clearApiKey();
      }
    } else if (error.request) {
      // Request made but no response
      console.error('Network Error:', error.message);
    } else {
      // Error in request setup
      console.error('Request Error:', error.message);
    }

    return Promise.reject(error);
  }
);

/**
 * Task API
 */
export const taskApi = {
  getAll: () => api.get('/tasks'),
  getPending: () => api.get('/tasks/pending'),
  getCurrent: () => api.get('/tasks/current'),
  getHabits: () => api.get('/tasks/habits'),
  getToday: () => api.get('/tasks/today'),
  getTodayHabits: () => api.get('/tasks/today-habits'),
  getById: (id) => api.get(`/tasks/${id}`),
  create: (task) => api.post('/tasks', task),
  update: (id, task) => api.put(`/tasks/${id}`, task),
  delete: (id) => api.delete(`/tasks/${id}`),
  start: (taskId = null) => api.post('/tasks/start', null, { params: { task_id: taskId } }),
  stop: () => api.post('/tasks/stop'),
  complete: (taskId = null) => api.post('/tasks/done', null, { params: { task_id: taskId } }),
  roll: (mood = null) => api.post('/tasks/roll', null, { params: { mood } }),
  canRoll: () => api.get('/tasks/can-roll')
};

/**
 * Stats API
 */
export const statsApi = {
  get: () => api.get('/stats')
};

/**
 * Settings API
 */
export const settingsApi = {
  get: () => api.get('/settings'),
  update: (settings) => api.put('/settings', settings)
};

/**
 * Points API
 */
export const pointsApi = {
  getCurrent: () => api.get('/points'),
  getHistory: (days = 30) => api.get('/points/history', { params: { days } }),
  getProjection: (targetDate) => api.get('/points/projection', { params: { target_date: targetDate } })
};

/**
 * Goals API
 */
export const goalsApi = {
  getAll: (includeAchieved = false) => api.get('/points/goals', {
    params: { include_achieved: includeAchieved }
  }),
  create: (goal) => api.post('/points/goals', goal),
  update: (id, goal) => api.put(`/points/goals/${id}`, goal),
  delete: (id) => api.delete(`/points/goals/${id}`)
};

/**
 * Rest Days API
 */
export const restDaysApi = {
  getAll: () => api.get('/rest-days'),
  create: (restDay) => api.post('/rest-days', restDay),
  delete: (id) => api.delete(`/rest-days/${id}`)
};

/**
 * Backups API
 */
export const backupsApi = {
  getAll: () => api.get('/backups'),
  create: () => api.post('/backups'),
  restore: (filename) => api.post(`/backups/${filename}/restore`),
  delete: (filename) => api.delete(`/backups/${filename}`)
};

/**
 * Scheduler API
 */
export const schedulerApi = {
  getStatus: () => api.get('/scheduler/status')
};

// Backward compatibility - export old API
export const getTasks = taskApi.getAll;
export const getPendingTasks = taskApi.getPending;
export const getCurrentTask = taskApi.getCurrent;
export const getHabits = taskApi.getHabits;
export const getTodayTasks = taskApi.getToday;
export const getTodayHabits = taskApi.getTodayHabits;
export const getStats = statsApi.get;
export const getTask = taskApi.getById;
export const createTask = taskApi.create;
export const updateTask = taskApi.update;
export const deleteTask = taskApi.delete;
export const startTask = taskApi.start;
export const stopTask = taskApi.stop;
export const completeTask = taskApi.complete;
export const rollTasks = taskApi.roll;
export const canRoll = taskApi.canRoll;

export default api;
