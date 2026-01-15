// API configuration
// В production используем относительные пути (через reverse proxy)
// В development - прямое подключение к backend
export const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');

// NOTE: API ключ НЕ экспортируется отсюда!
// Всегда используй getApiKey() из api.js для получения ключа из localStorage
