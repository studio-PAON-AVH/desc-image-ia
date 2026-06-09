import apiClient from './client';
import type { ITask } from '../interfaces';

export async function getTask(taskId: string): Promise<{ result: ITask; status?: number }> {
  const response = await apiClient.get<{ result: ITask }>(`/api/task/${taskId}`, {
    validateStatus: (status) => status === 200 || status === 202,
  });
  return { result: response.data.result, status: response.status };
}

export async function getAdminTasks(
  limit = 50,
  offset = 0
): Promise<{ tasks: ITask[]; limit: number; offset: number }> {
  const response = await apiClient.get<{ tasks: ITask[]; limit: number; offset: number }>(
    '/api/task/admin',
    { params: { limit, offset } }
  );
  return response.data;
}