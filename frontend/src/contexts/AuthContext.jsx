/**
 * Authentication context.
 * Manages API key storage and authentication state.
 */
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getApiKey, setApiKey as setStoredApiKey, clearApiKey } from '../shared/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [apiKey, setApiKeyState] = useState(getApiKey());
  const [isAuthenticated, setIsAuthenticated] = useState(!!getApiKey());

  // Handle unauthorized events from API interceptor
  useEffect(() => {
    const handleUnauthorized = () => {
      setApiKeyState('');
      setIsAuthenticated(false);
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, []);

  const login = useCallback((key) => {
    setStoredApiKey(key);
    setApiKeyState(key);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(() => {
    clearApiKey();
    setApiKeyState('');
    setIsAuthenticated(false);
  }, []);

  const value = {
    apiKey,
    isAuthenticated,
    login,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
