/**
 * Application providers wrapper.
 * Combines all context providers in one place.
 */
import { AuthProvider } from '../contexts/AuthContext';
import { SettingsProvider } from '../contexts/SettingsContext';

export function AppProviders({ children }) {
  return (
    <AuthProvider>
      <SettingsProvider>
        {children}
      </SettingsProvider>
    </AuthProvider>
  );
}

export default AppProviders;
