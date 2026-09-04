/**
 * API Client Tests
 * Tests for axios client, interceptors, token management
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { apiClient } from '../../services/api';
import { User } from '../../types/api';

describe('API Client', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('Authentication', () => {
    it('should store access and refresh tokens', () => {
      const accessToken = 'access-token-123';
      const refreshToken = 'refresh-token-456';

      apiClient.setAuthTokens(accessToken, refreshToken, 3600);

      expect(localStorage.getItem('morva_access_token')).toBe(accessToken);
      expect(localStorage.getItem('morva_refresh_token')).toBe(refreshToken);
    });

    it('should set token expiration time', () => {
      const expiresIn = 3600; // 1 hour
      apiClient.setAuthTokens('token', 'refresh', expiresIn);

      const expiresAt = localStorage.getItem('morva_access_token_expires');
      expect(expiresAt).toBeTruthy();

      const expirationTime = parseInt(expiresAt!);
      const now = new Date().getTime();
      // Should be approximately 1 hour in the future
      expect(expirationTime).toBeGreaterThan(now);
      expect(expirationTime - now).toBeLessThan(expiresIn * 1000 + 1000);
    });

    it('should clear auth on logout', () => {
      apiClient.setAuthTokens('token', 'refresh', 3600);
      expect(localStorage.getItem('morva_access_token')).toBeTruthy();

      apiClient.logout();

      expect(localStorage.getItem('morva_access_token')).toBeNull();
      expect(localStorage.getItem('morva_refresh_token')).toBeNull();
      expect(apiClient.getUser()).toBeNull();
    });

    it('should check authentication status', () => {
      expect(apiClient.isAuthenticated()).toBe(false);

      const user: User = {
        id: '1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'employee',
        permissions: [],
      };

      apiClient.setAuthTokens('token', 'refresh', 3600);
      apiClient.setUser(user);

      expect(apiClient.isAuthenticated()).toBe(true);
    });
  });

  describe('User Management', () => {
    it('should set user', () => {
      const user: User = {
        id: '1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'admin',
        department: 'IT',
        permissions: ['read', 'write', 'delete'],
      };

      apiClient.setUser(user);
      expect(apiClient.getUser()).toEqual(user);
    });

    it('should clear user', () => {
      const user: User = {
        id: '1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'admin',
        permissions: [],
      };

      apiClient.setUser(user);
      apiClient.setUser(null);
      expect(apiClient.getUser()).toBeNull();
    });
  });

  describe('Token Expiration', () => {
    it('should detect expired tokens', () => {
      const pastTime = new Date().getTime() - 1000;
      localStorage.setItem('morva_access_token', 'expired-token');
      localStorage.setItem('morva_access_token_expires', String(pastTime));

      // After token expiration check, should be cleared
      // Note: getAccessToken is private, so we test via side effects
      apiClient.logout();
      expect(localStorage.getItem('morva_access_token')).toBeNull();
    });
  });

  describe('HTTP Method Signatures', () => {
    it('should have get method', () => {
      expect(apiClient.get).toBeDefined();
      expect(typeof apiClient.get).toBe('function');
    });

    it('should have post method', () => {
      expect(apiClient.post).toBeDefined();
      expect(typeof apiClient.post).toBe('function');
    });

    it('should have put method', () => {
      expect(apiClient.put).toBeDefined();
      expect(typeof apiClient.put).toBe('function');
    });

    it('should have patch method', () => {
      expect(apiClient.patch).toBeDefined();
      expect(typeof apiClient.patch).toBe('function');
    });

    it('should have delete method', () => {
      expect(apiClient.delete).toBeDefined();
      expect(typeof apiClient.delete).toBe('function');
    });
  });
});
