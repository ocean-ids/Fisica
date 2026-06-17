export interface LoginResponse {
  message: string;
  access: string;
  refresh: string;
  user: {
    id: number;
    username: string;
    email: string;
    first_name?: string;
    last_name?: string;
    full_name?: string;
    photo_url?: string | null;
    cargo?: string | null;
    is_superuser: boolean;
    groups: string[];
    permissions: string[];
  };
}