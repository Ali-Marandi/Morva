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
import {
  DEMO_LOGIN,
  DEMO_MODE,
  DEMO_PIN,
  DEMO_SESSION,
  DEMO_SESSION_TTL,
  demoUser,
} from './demo';

export const authService = {
  /**
   * Login with email and password
   */
  async login(credentials: LoginRequest) {
    if (DEMO_MODE) {
      const valid = credentials.email.trim().toLowerCase() === DEMO_LOGIN && credentials.password === DEMO_PIN;
      if (!valid) {
        return {
          success: false,
          error: {
            code: 'INVALID_LOGIN',
            message: 'برای ورود نمایشی، از حساب نمایشی ارائه‌شده استفاده کنید.',
            statusCode: 401,
          },
        };
      }

      apiClient.setAuthTokens(DEMO_SESSION, DEMO_SESSION, DEMO_SESSION_TTL);
      apiClient.setUser(demoUser);
      return {
        success: true,
        data: {
          accessToken: DEMO_SESSION,
          refreshToken: DEMO_SESSION,
          expiresIn: DEMO_SESSION_TTL,
          user: demoUser,
        },
      } satisfies { success: true; data: LoginResponse };
    }

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
      if (!DEMO_MODE) await apiClient.post('/auth/logout');
    } finally {
      apiClient.logout();
    }
  },

  /**
   * Get current user profile
   */
  async getProfile() {
    if (DEMO_MODE) {
      return { success: true, data: apiClient.getUser() ?? demoUser };
    }
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
    if (DEMO_MODE) {
      return {
        success: true,
        data: { email },
      };
    }
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
    if (DEMO_MODE) {
      return {
        success: true,
        data: {
          accessToken: DEMO_SESSION,
          expiresIn: DEMO_SESSION_TTL,
        },
      } satisfies { success: true; data: RefreshTokenResponse };
    }
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
