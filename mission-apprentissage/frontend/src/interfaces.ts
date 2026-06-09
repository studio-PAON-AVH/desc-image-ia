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
  model_name: string;
  model_key: string;
  is_written_by_ai: boolean;
  is_written_by_human: boolean;
  validated_by_human: boolean;
}
export interface IImage {
  image_id: number;
  image_file_name: string;
  image_position_in_epub: number;
  descriptions: IDescription[];
}
export interface IDescriptionResponse { task_id: string; status: string; total_images: number; images: IImage[]; }
export interface IDescriptionValidation {
  image_index: number;
  text: string;
  model?: string;
  is_written_by_ai: boolean;
  is_written_by_human: boolean;
}