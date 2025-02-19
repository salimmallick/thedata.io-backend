import { useState, useEffect, useCallback } from 'react';
import { api, login as apiLogin } from '../services/api';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  isAdmin: boolean;
  permissions: string[];
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const useAuth = () => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isAuthenticated: !!localStorage.getItem('auth_token'),
    isLoading: true
  });

  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      checkAuthStatus();
    } else {
      setAuthState(prev => ({ ...prev, isLoading: false }));
    }
  }, []);

  const checkAuthStatus = async () => {
    try {
      const response = await api.get<User>('/api/v1/auth/me');
      setAuthState({
        user: response.data,
        isAuthenticated: true,
        isLoading: false
      });
      return true;
    } catch (error) {
      console.error('Auth status check failed:', error);
      localStorage.removeItem('auth_token');
      setAuthState({
        user: null,
        isAuthenticated: false,
        isLoading: false
      });
      return false;
    }
  };

  const login = useCallback(async (email: string, password: string) => {
    try {
      const response = await apiLogin(email, password);
      if (response.access_token) {
        const userData = response.user;
        setAuthState({
          user: userData,
          isAuthenticated: true,
          isLoading: false
        });
        localStorage.setItem('auth_token', response.access_token);
        await checkAuthStatus(); // Verify token and get full user data
        return true;
      }
      return false;
    } catch (error) {
      console.error('Login error:', error);
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token');
    setAuthState({
      user: null,
      isAuthenticated: false,
      isLoading: false
    });
  }, []);

  return {
    ...authState,
    login,
    logout
  };
}; 