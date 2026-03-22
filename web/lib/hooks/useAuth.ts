'use client'

import { useEffect } from 'react'
import { useAuthStore } from '../store/authStore'
import { secureStorage } from '../auth/secure-storage'

export function useAuth() {
  const { user, isAuthenticated, isLoading, signIn, signUp, signOut, fetchUser } = useAuthStore()

  useEffect(() => {
    if (typeof window !== 'undefined') {
      // Clean up any legacy localStorage tokens from older versions
      secureStorage.migrateFromLocalStorage()

      // Always attempt session restoration on mount.
      // fetchUser() will use the in-memory access token if available, or
      // silently call /refresh (sending the HttpOnly cookie automatically).
      // If neither exists the backend returns 401 and the user sees the login page.
      fetchUser()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run once on mount

  return {
    user,
    isAuthenticated,
    isLoading,
    signIn,
    signUp,
    signOut,
  }
}
