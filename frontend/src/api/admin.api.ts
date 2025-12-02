import apiClient from './client';
import type { User } from '../types/auth';

export interface UserUpdateRequest {
  is_approved?: boolean;
  role?: string;
  is_active?: boolean;
}

export const adminApi = {
  getAllUsers: async (): Promise<User[]> => {
    const response = await apiClient.get<User[]>('/admin/users');
    return response.data;
  },

  getPendingUsers: async (): Promise<User[]> => {
    const response = await apiClient.get<User[]>('/admin/users/pending');
    return response.data;
  },

  updateUser: async (userId: string, data: UserUpdateRequest): Promise<User> => {
    const response = await apiClient.patch<User>(`/admin/users/${userId}`, data);
    return response.data;
  },

  approveUser: async (userId: string): Promise<User> => {
    const response = await apiClient.post<User>(`/admin/users/${userId}/approve`);
    return response.data;
  },

  rejectUser: async (userId: string): Promise<void> => {
    await apiClient.post(`/admin/users/${userId}/reject`);
  },

  toggleUserActive: async (userId: string): Promise<User> => {
    const response = await apiClient.post<User>(`/admin/users/${userId}/toggle-active`);
    return response.data;
  },
};
