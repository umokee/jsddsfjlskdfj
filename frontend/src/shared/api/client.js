/**
 * Axios client with interceptors.
 * Centralized HTTP client configuration.
 */
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || (
  import.meta.env.DEV ? 'http://localhost:8000' : ''
);

export const API_BASE = `${API_URL}/api`;

// Create axios instance
const client = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
});

// API Key management
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

// Request Interceptor - add auth header
client.interceptors.request.use(
  (config) => {
    if (apiKey) {
      config.headers['X-API-Key'] = apiKey;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor - handle errors
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const { status, data } = error.response;
      console.error(`API Error ${status}:`, data);

      if (status === 401) {
        clearApiKey();
        // Emit event for auth context to handle
        window.dispatchEvent(new CustomEvent('auth:unauthorized'));
      }
    } else if (error.request) {
      console.error('Network Error:', error.message);
    } else {
      console.error('Request Error:', error.message);
    }

    return Promise.reject(error);
  }
);

export default client;
