'use client'

import { useAuthStore } from '../store/authStore'

// Pure state reader — no side effects.
// Session initialization (fetchUser) must be called once in the root layout,
// not here. Calling fetchUser() in every component that reads auth state
// causes multiple concurrent /me requests on each page load.
export function useAuth() {
  const { user, isAuthenticated, isLoading, signIn, signUp, signOut, fetchUser } = useAuthStore()

  return {
    user,
    isAuthenticated,
    isLoading,
    signIn,
    signUp,
    signOut,
    fetchUser,
  }
}
