'use client'

import { useAuthStore } from '../store/authStore'

// Pure state reader — no side effects.
// Session initialization (fetchUser) must be called once in the root layout,
// not here. Each field is a separate selector so components re-render only
// when the specific field they consume changes.
export function useAuth() {
  const user = useAuthStore((state) => state.user)
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const isLoading = useAuthStore((state) => state.isLoading)
  const signIn = useAuthStore((state) => state.signIn)
  const signUp = useAuthStore((state) => state.signUp)
  const signOut = useAuthStore((state) => state.signOut)

  return { user, isAuthenticated, isLoading, signIn, signUp, signOut }
}
