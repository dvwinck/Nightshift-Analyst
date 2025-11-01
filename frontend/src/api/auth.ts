import { request } from "./client";
import { User } from "../types";

export type LoginCredentials = {
  username: string;
  password: string;
};

export type RegisterPayload = {
  email: string;
  username: string;
  password: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export async function login(
  credentials: LoginCredentials
): Promise<LoginResponse> {
  const formData = new URLSearchParams();
  formData.append("username", credentials.username);
  formData.append("password", credentials.password);

  return request<LoginResponse>("/auth/jwt/login", {
    method: "POST",
    body: formData,
  });
}

export async function register(payload: RegisterPayload): Promise<User> {
  return request<User>("/auth/register", {
    method: "POST",
    body: payload,
  });
}

export async function fetchCurrentUser(token: string): Promise<User> {
  return request<User>("/auth/users/me", {
    method: "GET",
    token,
  });
}
