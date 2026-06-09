export interface IRegister { username: string; email: string; password: string; }
export interface ILogin { email: string; password: string; }
export interface IUser { id: number; username: string; email: string; role: string; created_at: string; updated_at: string; }

export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed';
export type EpubStatus = 'uploaded' | 'processing' | 'completed' | 'failed';

export interface IEpub { file_name: string; upload_date: string; status: EpubStatus; }
export interface ITask {
  task_id_redis: string;
  epubs?: IEpub[];
  status: TaskStatus;
  total_images: number;
  processed_images: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface IDescription {
  description_id: number;
  description_text: string;
  model_name: string | null;
  model_key: string | null;
  validated_by_human: boolean;
}
export interface IFinalDescription {
  description_text: string;
  model_key: string | null;
}
export interface IImage {
  image_id: number;
  image_file_name: string;
  image_position_in_epub: number;
  descriptions: IDescription[];
  final_description?: IFinalDescription | null;
}
export interface IDescriptionResponse { task_id: string; status: string; total_images: number; images: IImage[]; }

export interface ITaskModelDescription { french_description?: string; description?: string; success?: boolean; error?: string; }
export interface ITaskImageEntry {
  index: number;
  salesforce_blip: ITaskModelDescription | null;
  florence2: ITaskModelDescription | null;
  git_large: ITaskModelDescription | null;
}
export interface ITaskDescriptionsPayload {
  images: Record<string, ITaskImageEntry>;
  total_images: number;
}
export interface ITaskResultResponse {
  completed: boolean;
  status: 'pending' | 'in_progress' | 'completed';
  total_images?: number;
  processed_images?: number;
  message?: string;
  result?: ITaskDescriptionsPayload | { descriptions?: ITaskDescriptionsPayload };
}
export interface IDescriptionValidation {
  image_index: number;
  text: string;
  model?: string | null;
}
