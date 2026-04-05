'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { useAuth } from '@/lib/hooks/useAuth'
import { secureStorage } from '@/lib/auth/secure-storage'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { user, isLoading, fetchUser } = useAuth()
  const router = useRouter()
  const pathname = usePathname()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  // Single session initialization point — runs once for the entire dashboard.
  // Keeping fetchUser() here (not in useAuth) prevents Header, Sidebar, and
  // other consumers from each firing a separate /me request on mount.
  useEffect(() => {
    if (typeof window !== 'undefined') {
      secureStorage.migrateFromLocalStorage()
      fetchUser()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!isLoading && !user) {
      // Store the current path to redirect back after login
      const redirectUrl = encodeURIComponent(pathname)
      router.push(`/signin?redirect=${redirectUrl}`)
    }
  }, [user, isLoading, router, pathname])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-amber-50 via-yellow-50 to-white">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar
        mobileOpen={mobileMenuOpen}
        onMobileClose={() => setMobileMenuOpen(false)}
      />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Header onMobileMenuToggle={() => setMobileMenuOpen(true)} />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
