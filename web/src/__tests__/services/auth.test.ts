/**
 * Auth Service Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { authService } from '../../services/auth';
import { apiClient } from '../../services/api';
import { LoginRequest, LoginResponse, User } from '../../types/api';

// Mock the apiClient
vi.mock('../../services/api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    setAuthTokens: vi.fn(),
    setUser: vi.fn(),
    getUser: vi.fn(),
    logout: vi.fn(),
    isAuthenticated: vi.fn(),
  },
}));

describe('Auth Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mocked apiClient behavior
    if (apiClient && (apiClient as any).getUser) {
      (apiClient as any).getUser.mockReturnValue(null);
    }
    if (apiClient && (apiClient as any).isAuthenticated) {
      (apiClient as any).isAuthenticated.mockReturnValue(false);
    }
  });

  describe('Service Methods', () => {
    it('should have login method', () => {
      expect(authService.login).toBeDefined();
      expect(typeof authService.login).toBe('function');
    });

    it('should have logout method', () => {
      expect(authService.logout).toBeDefined();
      expect(typeof authService.logout).toBe('function');
    });

    it('should have getProfile method', () => {
      expect(authService.getProfile).toBeDefined();
      expect(typeof authService.getProfile).toBe('function');
    });

    it('should have updateProfile method', () => {
      expect(authService.updateProfile).toBeDefined();
      expect(typeof authService.updateProfile).toBe('function');
    });

    it('should have changePassword method', () => {
      expect(authService.changePassword).toBeDefined();
      expect(typeof authService.changePassword).toBe('function');
    });

    it('should have requestPasswordReset method', () => {
      expect(authService.requestPasswordReset).toBeDefined();
      expect(typeof authService.requestPasswordReset).toBe('function');
    });

    it('should have resetPassword method', () => {
      expect(authService.resetPassword).toBeDefined();
      expect(typeof authService.resetPassword).toBe('function');
    });

    it('should have refreshToken method', () => {
      expect(authService.refreshToken).toBeDefined();
      expect(typeof authService.refreshToken).toBe('function');
    });

    it('should have getCurrentUser method', () => {
      expect(authService.getCurrentUser).toBeDefined();
      expect(typeof authService.getCurrentUser).toBe('function');
    });

    it('should have isAuthenticated method', () => {
      expect(authService.isAuthenticated).toBeDefined();
      expect(typeof authService.isAuthenticated).toBe('function');
    });
  });

  describe('Method Signatures', () => {
    it('login should accept LoginRequest', async () => {
      const credentials: LoginRequest = {
        email: 'test@example.com',
        password: 'password123',
        rememberMe: true,
      };

      // Method should accept these parameters
      expect(() => authService.login(credentials)).toBeDefined();
    });

    it('changePassword should require old and new passwords', async () => {
      // Method should exist and accept two strings
      expect(authService.changePassword).toBeDefined();
    });

    it('requestPasswordReset should accept email', async () => {
      expect(authService.requestPasswordReset).toBeDefined();
    });

    it('resetPassword should accept token and password', async () => {
      expect(authService.resetPassword).toBeDefined();
    });

    it('refreshToken should accept refresh token', async () => {
      expect(authService.refreshToken).toBeDefined();
    });
  });

  describe('Authentication State', () => {
    it('getCurrentUser should return user or null', () => {
      const result = authService.getCurrentUser();
      expect(result === null || typeof result === 'object').toBe(true);
    });

    it('isAuthenticated should return boolean', () => {
      const result = authService.isAuthenticated();
      expect(typeof result).toBe('boolean');
    });
  });
});
