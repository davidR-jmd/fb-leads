import React, { createContext, useCallback, useEffect, useState } from 'react';
import { authApi } from '../api/auth.api';
import { clearTokens, getAccessToken, setTokens } from '../api/client';
import type { LoginRequest, RegisterRequest, User } from '../types/auth';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isLoading: boolean;
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<{ pendingApproval: boolean }>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadUser = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setIsLoading(false);
      return;
    }

    try {
      const userData = await authApi.getMe();
      setUser(userData);
    } catch {
      clearTokens();
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = async (data: LoginRequest): Promise<void> => {
    const tokens = await authApi.login(data);
    setTokens(tokens.access_token, tokens.refresh_token);
    const userData = await authApi.getMe();
    setUser(userData);
  };

  const register = async (data: RegisterRequest): Promise<{ pendingApproval: boolean }> => {
    await authApi.register(data);
    // Try to auto-login after registration (will fail if pending approval)
    try {
      await login({ email: data.email, password: data.password });
      return { pendingApproval: false };
    } catch {
      // Login failed - likely pending approval
      return { pendingApproval: true };
    }
  };

  const logout = (): void => {
    clearTokens();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isAdmin: user?.role === 'admin',
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
