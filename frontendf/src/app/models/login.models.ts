export interface LoginResponse {
  message: string;
  access: string;
  refresh: string;
  user: {
    id: number;
    username: string;
    email: string;
    groups: string[];
    permissions: string[];
  };
}