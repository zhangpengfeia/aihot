import { createContext, useContext, useState, type ReactNode } from 'react';
import { useResource } from '../hooks/useResource';
import type { User } from '../views/users/UserManagementPage';
const AuthContext = createContext<{ user: User | null; loading: boolean; refresh: () => void }>({
  user: null,
  loading: true,
  refresh: () => {},
});
export function AuthProvider({ children }: { children: ReactNode }) {
  const [tick, setTick] = useState(0);
  const { data, loading } = useResource<User | null>('/auth/me', tick);
  return (
    <AuthContext.Provider
      value={{ user: data ?? null, loading, refresh: () => setTick((t) => t + 1) }}
    >
      {children}
    </AuthContext.Provider>
  );
}
export function useAuth() {
  return useContext(AuthContext);
}
