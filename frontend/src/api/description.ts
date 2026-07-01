import apiClient from './client';
import type { IDescriptionResponse, IDescriptionValidation } from '@/interfaces';

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

/**
 * URL absolue de l'image (position `index`, 0-based) servie par le proxy.
 * Utilisable directement dans <img src>. Les cookies d'auth sont envoyés
 * automatiquement (même site).
 */
export function getImageUrl(taskId: string, index: number): string {
  return `${API_BASE_URL}/api/description/${taskId}/images/${index}`;
}

export async function getDescriptions(taskId: string): Promise<IDescriptionResponse> {
  const response = await apiClient.get<IDescriptionResponse>(`/api/description/${taskId}`);
  return response.data;
}

export async function validateDescriptions(
  taskId: string,
  validatedDescriptions: IDescriptionValidation[]
): Promise<{ success: boolean; message: string; validated_count: number }> {
  const response = await apiClient.post<{ success: boolean; message: string; validated_count: number }>(
    `/api/description/${taskId}/validate`,
    { validated_descriptions: validatedDescriptions }
  );
  return response.data;
}

export async function addDescriptions(taskIdRedis: string): Promise<Blob> {
  const response = await apiClient.post(
    '/api/description/add_descriptions',
    { task_id_redis: taskIdRedis },
    { responseType: 'blob' }
  );
  return response.data as Blob;
}
