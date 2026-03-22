import { create } from 'zustand'
import { apiClient } from '../api/client'
import { secureStorage } from '../auth/secure-storage'
import type { User } from '../types'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string, name: string) => Promise<void>
  signOut: () => Promise<void>
  fetchUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true, // Start as true to prevent premature redirects

  signIn: async (email, password) => {
    set({ isLoading: true })
    try {
      const data = await apiClient.login(email, password)
      if (typeof window !== 'undefined') {
        // Use secure storage instead of localStorage
        secureStorage.storeTokens({
          access_token: data.access_token,
          refresh_token: data.refresh_token,
          expires_in: data.expires_in
        })
      }
      set({ user: data.account, isAuthenticated: true })
    } finally {
      set({ isLoading: false })
    }
  },

  signUp: async (email, password, name) => {
    set({ isLoading: true })
    try {
      await apiClient.signup(email, password, name)
      // Don't store tokens or set user - account needs email verification first
      // User will need to verify email and then login
      // No need to store tokens or set authenticated state
    } finally {
      set({ isLoading: false })
    }
  },

  signOut: async () => {
    await apiClient.logout()
    if (typeof window !== 'undefined') {
      // Use secure storage for logout
      secureStorage.clearTokens()
    }
    set({ user: null, isAuthenticated: false })
  },

  fetchUser: async () => {
    try {
      // If the access token is absent (e.g. after a page refresh or new tab),
      // proactively restore it via the HttpOnly refresh token cookie.
      // We cannot read the cookie from JS — just attempt the refresh and see if
      // the backend accepts it (it will if the cookie is present and valid).
      if (!secureStorage.getAccessToken()) {
        const refreshed = await secureStorage.refreshAccessToken()
        if (!refreshed) {
          set({ user: null, isAuthenticated: false, isLoading: false })
          return
        }
      }
      const data = await apiClient.getCurrentUser()
      set({ user: data, isAuthenticated: true, isLoading: false })
    } catch {
      // Only clear auth if token is invalid, not on network errors
      if (typeof window !== 'undefined') {
        secureStorage.clearTokens()
      }
      set({ user: null, isAuthenticated: false, isLoading: false })
    }
  },
}))
