import apiClient from './client';
import type { LoginRequest, RegisterRequest, TokenResponse, User } from '../types/auth';

export const authApi = {
  register: async (data: RegisterRequest): Promise<User> => {
    const response = await apiClient.post<User>('/auth/register', data);
    return response.data;
  },

  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/auth/login', data);
    return response.data;
  },

  getMe: async (): Promise<User> => {
    const response = await apiClient.get<User>('/auth/me');
    return response.data;
  },

  refresh: async (refreshToken: string): Promise<{ access_token: string }> => {
    const response = await apiClient.post('/auth/refresh', { refresh_token: refreshToken });
    return response.data;
  },
};
