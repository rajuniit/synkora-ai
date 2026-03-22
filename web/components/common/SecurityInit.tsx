'use client'

import { useEffect } from 'react'
import { initializeSecureStorage } from '../../lib/auth/secure-storage'

/**
 * Security Initialization Component
 * CRITICAL: Initializes secure storage and token management on app start
 */
export function SecurityInit() {
  useEffect(() => {
    // Initialize secure storage system
    initializeSecureStorage()
  }, [])

  return null // This component doesn't render anything
}
