/**
 * Base API Client Configuration
 * Axios instance with interceptors, error handling, and token management
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { ApiResponse, ApiError, User } from '../types/api';

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
    // Request interceptor: Add auth token
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

    // Response interceptor: Handle errors and token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const config = error.config as RequestConfig;

        // Handle 401 Unauthorized - try to refresh token
        if (error.response?.status === 401 && !config?._retry) {
          config!._retry = true;

          if (!this.isRefreshing) {
            this.isRefreshing = true;

            try {
              const newToken = await this.refreshAccessToken();
              this.isRefreshing = false;

              // Retry queued requests with new token
              this.refreshSubscribers.forEach((callback) => callback(newToken));
              this.refreshSubscribers = [];

              // Retry original request
              return this.client(config);
            } catch (refreshError) {
              this.isRefreshing = false;
              this.clearAuth();
              return Promise.reject(this.handleError(refreshError));
            }
          }

          // Queue this request to retry after refresh
          return new Promise((resolve, reject) => {
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
    const token = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (token) {
      // Token exists, but user info needs to be fetched
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

  /**
   * Refresh access token using refresh token
   */
  private async refreshAccessToken(): Promise<string> {
    const refreshToken = this.getRefreshToken();

    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await this.client.post<ApiResponse>('/auth/refresh', {
        refreshToken,
      });

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

  /**
   * Store access token with expiration
   */
  private setAccessToken(token: string, expiresIn: number) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
    const expirationTime = new Date().getTime() + expiresIn * 1000;
    localStorage.setItem(`${TOKEN_STORAGE_KEY}_expires`, String(expirationTime));
  }

  /**
   * Get stored access token if valid
   */
  private getAccessToken(): string | null {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY);
    const expiresAt = localStorage.getItem(`${TOKEN_STORAGE_KEY}_expires`);

    if (!token || !expiresAt) return null;

    if (new Date().getTime() > parseInt(expiresAt)) {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      localStorage.removeItem(`${TOKEN_STORAGE_KEY}_expires`);
      return null;
    }

    return token;
  }

  /**
   * Get stored refresh token
   */
  private getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY);
  }

  /**
   * Store refresh token
   */
  private setRefreshToken(token: string) {
    localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token);
  }

  /**
   * Clear all authentication data
   */
  private clearAuth() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(`${TOKEN_STORAGE_KEY}_expires`);
    localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
    this.currentUser = null;
  }

  /**
   * Set current user
   */
  public setUser(user: User | null) {
    this.currentUser = user;
  }

  /**
   * Get current user
   */
  public getUser(): User | null {
    return this.currentUser;
  }

  /**
   * Check if user is authenticated
   */
  public isAuthenticated(): boolean {
    return this.getAccessToken() !== null && this.currentUser !== null;
  }

  /**
   * Store login credentials
   */
  public setAuthTokens(accessToken: string, refreshToken: string, expiresIn: number) {
    this.setAccessToken(accessToken, expiresIn);
    this.setRefreshToken(refreshToken);
  }

  /**
   * Logout - clear all auth data
   */
  public logout() {
    this.clearAuth();
  }

  /**
   * GET request
   */
  public async get<T = unknown>(url: string, config?: any) {
    const response = await this.client.get<ApiResponse<T>>(url, config);
    return response.data;
  }

  /**
   * POST request
   */
  public async post<T = unknown>(url: string, data?: any, config?: any) {
    const response = await this.client.post<ApiResponse<T>>(url, data, config);
    return response.data;
  }

  /**
   * PUT request
   */
  public async put<T = unknown>(url: string, data?: any, config?: any) {
    const response = await this.client.put<ApiResponse<T>>(url, data, config);
    return response.data;
  }

  /**
   * PATCH request
   */
  public async patch<T = unknown>(url: string, data?: any, config?: any) {
    const response = await this.client.patch<ApiResponse<T>>(url, data, config);
    return response.data;
  }

  /**
   * DELETE request
   */
  public async delete<T = unknown>(url: string, config?: any) {
    const response = await this.client.delete<ApiResponse<T>>(url, config);
    return response.data;
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export type
export type { ApiClient };
