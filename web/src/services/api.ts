/**
 * Base API Client Configuration
 * Axios instance with interceptors, error handling, and token management
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { ApiResponse, ApiError, User } from '../types/api';
import {
  DEMO_MODE,
  DEMO_SESSION,
  DEMO_SESSION_TTL,
  DEMO_USER_STORAGE_KEY,
  demoGet,
  demoMutation,
  demoUser,
} from './demo';

// API base URL configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://api.morva.local/api/v1';
const TOKEN_STORAGE_KEY = 'morva_access_token';
const REFRESH_TOKEN_STORAGE_KEY = 'morva_refresh_token';

interface RequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

class ApiClient {
  private client: AxiosInstance;
  private currentUser: User | null = null;
  private isRefreshing = false;
  private refreshSubscribers: ((token: string) => void)[] = [];

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
        'X-Client-Version': '1.0.0',
      },
    });

    this.setupInterceptors();
    this.loadStoredAuth();
  }

  /**
   * Setup axios interceptors for request/response handling
   */
  private setupInterceptors() {
    this.client.interceptors.request.use(
      (config: RequestConfig) => {
        const token = this.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(this.handleError(error))
    );

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const config = error.config as RequestConfig;

        if (error.response?.status === 401 && !config?._retry) {
          config!._retry = true;

          if (!this.isRefreshing) {
            this.isRefreshing = true;

            try {
              const newToken = await this.refreshAccessToken();
              this.isRefreshing = false;
              this.refreshSubscribers.forEach((callback) => callback(newToken));
              this.refreshSubscribers = [];
              return this.client(config);
            } catch (refreshError) {
              this.isRefreshing = false;
              this.clearAuth();
              return Promise.reject(this.handleError(refreshError));
            }
          }

          return new Promise((resolve) => {
            this.refreshSubscribers.push((token: string) => {
              config.headers.Authorization = `Bearer ${token}`;
              resolve(this.client(config));
            });
          }).catch((err) => Promise.reject(this.handleError(err)));
        }

        return Promise.reject(this.handleError(error));
      }
    );
  }

  /**
   * Load stored authentication from localStorage
   */
  private loadStoredAuth() {
    if (!DEMO_MODE) return;
    const storedUser = localStorage.getItem(DEMO_USER_STORAGE_KEY);
    if (!storedUser) return;
    try {
      this.currentUser = JSON.parse(storedUser) as User;
    } catch {
      localStorage.removeItem(DEMO_USER_STORAGE_KEY);
    }
  }

  /**
   * Handle API errors and transform to consistent format
   */
  private handleError(error: unknown): ApiError {
    if (axios.isAxiosError(error)) {
      const response = error.response?.data as any;
      return {
        code: response?.error?.code || 'INTERNAL_ERROR',
        message: response?.error?.message || error.message || 'Unknown error occurred',
        statusCode: error.response?.status || 0,
        details: response?.error?.details,
      };
    }

    if (error instanceof Error) {
      return {
        code: 'NETWORK_ERROR',
        message: error.message,
        statusCode: 0,
      };
    }

    return {
      code: 'INTERNAL_ERROR',
      message: 'An unexpected error occurred',
      statusCode: 0,
    };
  }

  private async refreshAccessToken(): Promise<string> {
    if (DEMO_MODE) {
      this.setAccessToken(DEMO_SESSION, DEMO_SESSION_TTL);
      return DEMO_SESSION;
    }

    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await this.client.post<ApiResponse>('/auth/refresh', { refreshToken });
      if (!response.data.success || !response.data.data) {
        throw new Error('Token refresh failed');
      }
      const { accessToken, expiresIn } = response.data.data as any;
      this.setAccessToken(accessToken, expiresIn);
      return accessToken;
    } catch (error) {
      this.clearAuth();
      throw error;
    }
  }

  private setAccessToken(token: string, expiresIn: number) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
    const expirationTime = new Date().getTime() + expiresIn * 1000;
    localStorage.setItem(`${TOKEN_STORAGE_KEY}_expires`, String(expirationTime));
  }

  private getAccessToken(): string | null {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY);
    const expiresAt = localStorage.getItem(`${TOKEN_STORAGE_KEY}_expires`);
    if (!token || !expiresAt) return null;

    if (new Date().getTime() > parseInt(expiresAt, 10)) {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      localStorage.removeItem(`${TOKEN_STORAGE_KEY}_expires`);
      return null;
    }
    return token;
  }

  private getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY);
  }

  private setRefreshToken(token: string) {
    localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token);
  }

  private clearAuth() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(`${TOKEN_STORAGE_KEY}_expires`);
    localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
    if (DEMO_MODE) localStorage.removeItem(DEMO_USER_STORAGE_KEY);
    this.currentUser = null;
  }

  public setUser(user: User | null) {
    this.currentUser = user;
    if (DEMO_MODE) {
      if (user) localStorage.setItem(DEMO_USER_STORAGE_KEY, JSON.stringify(user));
      else localStorage.removeItem(DEMO_USER_STORAGE_KEY);
    }
  }

  public getUser(): User | null {
    return this.currentUser;
  }

  public isAuthenticated(): boolean {
    return this.getAccessToken() !== null && this.currentUser !== null;
  }

  public setAuthTokens(accessToken: string, refreshToken: string, expiresIn: number) {
    this.setAccessToken(accessToken, expiresIn);
    this.setRefreshToken(refreshToken);
  }

  public logout() {
    this.clearAuth();
  }

  public async get<T = unknown>(url: string, config?: any) {
    const demoResponse = demoGet<T>(url);
    if (demoResponse) return demoResponse;
    const response = await this.client.get<ApiResponse<T>>(url, config);
    return response.data;
  }

  public async post<T = unknown>(url: string, data?: any, config?: any) {
    const demoResponse = demoMutation<T>();
    if (demoResponse) return demoResponse;
    const response = await this.client.post<ApiResponse<T>>(url, data, config);
    return response.data;
  }

  public async put<T = unknown>(url: string, data?: any, config?: any) {
    const demoResponse = demoMutation<T>();
    if (demoResponse) return demoResponse;
    const response = await this.client.put<ApiResponse<T>>(url, data, config);
    return response.data;
  }

  public async patch<T = unknown>(url: string, data?: any, config?: any) {
    const demoResponse = demoMutation<T>();
    if (demoResponse) return demoResponse;
    const response = await this.client.patch<ApiResponse<T>>(url, data, config);
    return response.data;
  }

  public async delete<T = unknown>(url: string, config?: any) {
    const demoResponse = demoMutation<T>();
    if (demoResponse) return demoResponse;
    const response = await this.client.delete<ApiResponse<T>>(url, config);
    return response.data;
  }
}

export const apiClient = new ApiClient();
export type { ApiClient };
