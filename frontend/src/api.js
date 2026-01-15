import axios from 'axios';

// В production используем относительные пути (через reverse proxy)
// В development - прямое подключение к backend
const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');
const API_BASE = `${API_URL}/api`;

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

const api = axios.create({
  baseURL: API_BASE,
});

api.interceptors.request.use((config) => {
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey;
  }
  return config;
});

// Tasks
export const getTasks = () => api.get('/tasks');
export const getPendingTasks = () => api.get('/tasks/pending');
export const getCurrentTask = () => api.get('/tasks/current');
export const getHabits = () => api.get('/tasks/habits');
export const getTodayTasks = () => api.get('/tasks/today');
export const getTodayHabits = () => api.get('/tasks/today-habits');
export const getStats = () => api.get('/stats');
export const getTask = (id) => api.get(`/tasks/${id}`);
export const createTask = (task) => api.post('/tasks', task);
export const updateTask = (id, task) => api.put(`/tasks/${id}`, task);
export const deleteTask = (id) => api.delete(`/tasks/${id}`);

// Actions
export const startTask = (taskId = null) => api.post('/tasks/start', null, { params: { task_id: taskId } });
export const stopTask = () => api.post('/tasks/stop');
export const completeTask = (taskId = null) => api.post('/tasks/done', null, { params: { task_id: taskId } });
export const rollTasks = (mood = null) => api.post('/tasks/roll', null, { params: { mood } });
export const canRoll = () => api.get('/tasks/can-roll');

export default api;
