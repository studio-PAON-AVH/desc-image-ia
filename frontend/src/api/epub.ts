import apiClient from './client';

export async function uploadEpub(
  file: File,
  onUploadProgress?: (progressEvent: { loaded: number; total?: number }) => void
): Promise<{ task_id: string }> {
  const formData = new FormData();
  formData.append('upload', file);

  const response = await apiClient.post<{ task_id: string }>(
    '/api/epub/upload-epub',
    formData,
    {
      headers: { 'Content-Type': undefined },
      onUploadProgress,
    }
  );
  return response.data;
}

export async function downloadEpub(fileName: string): Promise<Blob> {
  const response = await apiClient.get(`/api/epub/download-epub/${encodeURIComponent(fileName)}`, {
    responseType: 'blob',
  });
  return response.data as Blob;
}
