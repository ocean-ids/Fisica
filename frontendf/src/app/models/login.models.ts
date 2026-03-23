export interface LoginResponse {
  message: string;
  access: string;
  refresh: string;
  user: {
    id: number;
    username: string;
    email: string;
    is_superuser: boolean;
    groups: string[];
    permissions: string[];
  };
}