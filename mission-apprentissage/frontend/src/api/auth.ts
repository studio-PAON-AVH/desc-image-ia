import apiClient from './client';
import type { ILogin, IRegister, IUser, ITask } from '@/interfaces';

export async function register(body: IRegister): Promise<IUser> {
  const response = await apiClient.post<IUser>('/api/auth/register', body);
  return response.data;
}

export async function login(body: ILogin): Promise<void> {
  await apiClient.post('/api/auth/login', body);
}

export async function getMe(): Promise<IUser> {
  const response = await apiClient.get<IUser>('/api/auth/users/me');
  return response.data;
}

export async function getMyTasks(): Promise<ITask[]> {
  const response = await apiClient.get<{ tasks: ITask[] }>('/api/auth/users/me/tasks');
  return response.data.tasks;
}

export async function refresh(): Promise<void> {
  await apiClient.post('/api/auth/refresh');
}

export async function logout(): Promise<void> {
  await apiClient.post('/api/auth/logout');
}
