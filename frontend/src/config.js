// API configuration
// В production используем относительные пути (через reverse proxy)
// В development - прямое подключение к backend
export const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');
export const API_KEY = import.meta.env.VITE_API_KEY || '';
