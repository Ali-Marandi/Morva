/**
 * Authentication Service
 * Handle login, logout, token refresh, and user profile
 */

import { apiClient } from './api';
import {
  LoginRequest,
  LoginResponse,
  User,
  RefreshTokenRequest,
  RefreshTokenResponse,
} from '../types/api';

export const authService = {
  /**
   * Login with email and password
   */
  async login(credentials: LoginRequest) {
    const response = await apiClient.post<LoginResponse>('/auth/login', credentials);
    if (response.success && response.data) {
      const { accessToken, refreshToken, expiresIn, user } = response.data;
      apiClient.setAuthTokens(accessToken, refreshToken, expiresIn);
      apiClient.setUser(user);
    }
    return response;
  },

  /**
   * Logout and clear auth tokens
   */
  async logout() {
    try {
      await apiClient.post('/auth/logout');
    } finally {
      apiClient.logout();
    }
  },

  /**
   * Get current user profile
   */
  async getProfile() {
    return apiClient.get<User>('/auth/me');
  },

  /**
   * Update user profile
   */
  async updateProfile(data: Partial<User>) {
    return apiClient.put<User>('/auth/me', data);
  },

  /**
   * Change password
   */
  async changePassword(currentPassword: string, newPassword: string) {
    return apiClient.post('/auth/change-password', {
      currentPassword,
      newPassword,
    });
  },

  /**
   * Request password reset
   */
  async requestPasswordReset(email: string) {
    return apiClient.post('/auth/forgot-password', { email });
  },

  /**
   * Reset password with token
   */
  async resetPassword(token: string, newPassword: string) {
    return apiClient.post('/auth/reset-password', { token, newPassword });
  },

  /**
   * Refresh access token
   */
  async refreshToken(refreshToken: string) {
    const request: RefreshTokenRequest = { refreshToken };
    return apiClient.post<RefreshTokenResponse>('/auth/refresh', request);
  },

  /**
   * Get current user from state
   */
  getCurrentUser(): User | null {
    return apiClient.getUser();
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return apiClient.isAuthenticated();
  },
};
