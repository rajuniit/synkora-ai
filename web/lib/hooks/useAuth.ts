'use client'

import { useAuthStore } from '../store/authStore'

// Pure state reader — no side effects.
// Session initialization (fetchUser) must be called once in the root layout,
// not here. Calling fetchUser() in every component that reads auth state
// causes multiple concurrent /me requests on each page load.
//
// Per-field selectors: each component re-renders only when the specific field
// it consumes changes, instead of on every auth store update.
export function useAuth() {
  const user = useAuthStore((state) => state.user)
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const isLoading = useAuthStore((state) => state.isLoading)
  const signIn = useAuthStore((state) => state.signIn)
  const signUp = useAuthStore((state) => state.signUp)
  const signOut = useAuthStore((state) => state.signOut)
  const fetchUser = useAuthStore((state) => state.fetchUser)

  return { user, isAuthenticated, isLoading, signIn, signUp, signOut, fetchUser }
}
