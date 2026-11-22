import { request } from './client';

export type User = {
  id: string;
  email: string;
  student_id: string | null;
  full_name: string;
  role: 'student' | 'admin';
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
  user: User;
};

export type RegisterInput = { full_name: string; email: string; student_id?: string | null; password: string };

type Message = { message: string };

export const authApi = {
  register: (body: RegisterInput) => request<TokenResponse>('/auth/register', { method: 'POST', body }),
  login: (body: { identifier: string; password: string; remember_me: boolean }) =>
    request<TokenResponse>('/auth/login', { method: 'POST', body }),
  refresh: (refresh_token: string) =>
    request<TokenResponse>('/auth/refresh', { method: 'POST', body: { refresh_token } }),
  logout: (token: string | null, refresh_token: string | null) =>
    request<Message>('/auth/logout', { method: 'POST', body: { refresh_token }, token }),
  me: (token: string) => request<User>('/auth/me', { token }),
  forgotPassword: (email: string) => request<Message>('/auth/forgot-password', { method: 'POST', body: { email } }),
  resetPassword: (token: string, new_password: string) =>
    request<Message>('/auth/reset-password', { method: 'POST', body: { token, new_password } }),
};
