'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { useAuth } from '@/lib/hooks/useAuth'
import { secureStorage } from '@/lib/auth/secure-storage'
import { SocialLoginButton } from '@/components/social-auth'
import { Zap, Shield, Users, BarChart3, Bot, Sparkles } from 'lucide-react'

function SignInContent() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { signIn, isAuthenticated, isLoading } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()

  // Get redirect URL from query params
  const redirectUrl = searchParams.get('redirect')

  // Redirect to dashboard if already authenticated
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace(redirectUrl ? decodeURIComponent(redirectUrl) : '/agents')
    }
  }, [isAuthenticated, isLoading, redirectUrl, router])

  // Handle OAuth callback
  useEffect(() => {
    const loginStatus = searchParams.get('login')
    const provider = searchParams.get('provider')
    const exchangeCode = searchParams.get('exchange_code')

    if (loginStatus === 'success' && exchangeCode) {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      fetch(`${apiUrl}/api/v1/auth/token-exchange?code=${exchangeCode}`, { credentials: 'include' })
        .then((res) => {
          if (!res.ok) throw new Error('Exchange failed')
          return res.json()
        })
        .then(({ access_token, expires_in }) => {
          secureStorage.storeTokens({ access_token, expires_in })
          toast.success(`Signed in successfully with ${provider}!`)
          window.location.href = redirectUrl ? decodeURIComponent(redirectUrl) : '/agents'
        })
        .catch(() => {
          const msg = 'Sign-in failed. Please try again.'
          setError(msg)
          toast.error(msg)
        })
    } else if (loginStatus === 'error') {
      const message = searchParams.get('message') || 'Social login failed'
      toast.error(message)
      setError(message)
    }
  }, [searchParams, router])

  // Show loader while checking auth state — must be after all hooks
  if (isLoading && !isSubmitting) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-500"></div>
      </div>
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      await signIn(email, password)
      toast.success('Signed in successfully!')
      // Redirect to original page or default to dashboard
      const targetUrl = redirectUrl ? decodeURIComponent(redirectUrl) : '/dashboard'
      router.push(targetUrl)
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail
        ? (typeof err.response.data.detail === 'string'
            ? err.response.data.detail
            : 'Invalid email or password')
        : err.message || 'Failed to sign in'
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSocialLogin = (provider: 'google' | 'microsoft' | 'apple') => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    window.location.href = `${apiUrl}/api/v1/auth/${provider}/login`
  }

  return (
    <div className="min-h-screen flex">
      {/* Left Side - Illustration & Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-red-500 via-rose-500 to-pink-600 relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-10">
          <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
            <defs>
              <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
                <path d="M 10 0 L 0 0 0 10" fill="none" stroke="white" strokeWidth="0.5"/>
              </pattern>
            </defs>
            <rect width="100" height="100" fill="url(#grid)" />
          </svg>
        </div>

        {/* Floating Elements */}
        <div className="absolute top-20 left-20 w-20 h-20 bg-white/10 rounded-3xl backdrop-blur-sm animate-pulse" />
        <div className="absolute top-40 right-32 w-16 h-16 bg-white/10 rounded-2xl backdrop-blur-sm animate-bounce" style={{ animationDuration: '3s' }} />
        <div className="absolute bottom-32 left-32 w-24 h-24 bg-white/10 rounded-full backdrop-blur-sm animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute bottom-48 right-20 w-14 h-14 bg-white/10 rounded-xl backdrop-blur-sm animate-bounce" style={{ animationDuration: '4s' }} />

        {/* Main Content */}
        <div className="relative z-10 flex flex-col justify-center px-16 py-12">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 mb-16">
            <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center shadow-lg">
              <Zap className="w-7 h-7 text-red-500" />
            </div>
            <span className="text-3xl font-bold text-white">Synkora</span>
          </Link>

          {/* AI Roles Grid */}
          <div className="mb-12">
            <div className="grid grid-cols-2 gap-4 max-w-md">
              <div className="bg-white/20 backdrop-blur-lg rounded-2xl p-5 border border-white/30">
                <div className="text-3xl mb-3">🧑‍💼</div>
                <div className="text-white font-semibold">AI Product Manager</div>
                <div className="text-white/60 text-sm">Backlog & planning</div>
              </div>
              <div className="bg-white/20 backdrop-blur-lg rounded-2xl p-5 border border-white/30">
                <div className="text-3xl mb-3">👨‍💻</div>
                <div className="text-white font-semibold">AI Engineer</div>
                <div className="text-white/60 text-sm">Code review & docs</div>
              </div>
              <div className="bg-white/20 backdrop-blur-lg rounded-2xl p-5 border border-white/30">
                <div className="text-3xl mb-3">📢</div>
                <div className="text-white font-semibold">AI Marketing</div>
                <div className="text-white/60 text-sm">Content & SEO</div>
              </div>
              <div className="bg-white/20 backdrop-blur-lg rounded-2xl p-5 border border-white/30">
                <div className="text-3xl mb-3">🎧</div>
                <div className="text-white font-semibold">AI Support</div>
                <div className="text-white/60 text-sm">24/7 responses</div>
              </div>
            </div>
          </div>

          {/* Text Content */}
          <h2 className="text-4xl font-bold text-white mb-4">
            Welcome back to your AI team
          </h2>
          <p className="text-white/80 text-lg mb-8 max-w-md">
            Your AI teammates are ready. Check in on their progress and deploy new agents.
          </p>

          {/* Features */}
          <div className="flex flex-wrap gap-3">
            <div className="flex items-center gap-2 bg-white/20 backdrop-blur-sm rounded-full px-4 py-2">
              <span className="text-white text-sm font-medium">Your LLM Keys</span>
            </div>
            <div className="flex items-center gap-2 bg-white/20 backdrop-blur-sm rounded-full px-4 py-2">
              <span className="text-white text-sm font-medium">Open Source</span>
            </div>
            <div className="flex items-center gap-2 bg-white/20 backdrop-blur-sm rounded-full px-4 py-2">
              <span className="text-white text-sm font-medium">Self-Host Option</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right Side - Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center bg-gray-50 px-6 py-12">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden text-center mb-8">
            <Link href="/" className="inline-flex items-center gap-3">
              <div className="w-12 h-12 bg-red-500 rounded-xl flex items-center justify-center">
                <Zap className="w-7 h-7 text-white" />
              </div>
              <span className="text-2xl font-bold text-gray-900">Synkora</span>
            </Link>
          </div>

          {/* Header */}
          <div className="text-center lg:text-left mb-10">
            <h1 className="text-2xl sm:text-4xl font-bold text-gray-900 mb-3">Sign in</h1>
            <p className="text-gray-600 text-lg">
              Welcome back! Please enter your details.
            </p>
          </div>

          {/* Form Card */}
          <div className="bg-white rounded-3xl shadow-xl border border-gray-100 p-5 sm:p-8">
            {/* Social Login */}
            <div className="mb-8">
              <SocialLoginButton
                provider="google"
                onClick={() => handleSocialLogin('google')}
                variant="full"
              />
            </div>

            {/* Divider */}
            <div className="relative my-8">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-white text-gray-500 font-medium">or continue with email</span>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm flex items-center gap-2">
                  <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  {error}
                </div>
              )}

              <div>
                <label htmlFor="email" className="block text-sm font-semibold text-gray-700 mb-2">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full px-4 py-4 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent transition-all text-gray-900 placeholder-gray-400"
                  placeholder="Enter your email"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-semibold text-gray-700 mb-2">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full px-4 py-4 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent transition-all text-gray-900 placeholder-gray-400"
                  placeholder="Enter your password"
                />
              </div>

              <div className="flex items-center justify-between">
                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="w-5 h-5 text-red-500 border-gray-300 rounded focus:ring-red-500 cursor-pointer"
                  />
                  <span className="ml-2 text-sm text-gray-600">Remember me</span>
                </label>
                <Link href="/forgot-password" className="text-sm font-semibold text-red-500 hover:text-red-600 transition-colors">
                  Forgot password?
                </Link>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-gradient-to-r from-red-500 to-rose-600 hover:from-red-600 hover:to-rose-700 text-white font-bold py-4 px-6 rounded-xl transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed text-lg"
              >
                {isSubmitting ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Signing in...
                  </span>
                ) : (
                  'Sign in'
                )}
              </button>
            </form>

            <div className="mt-8 text-center">
              <p className="text-gray-600">
                Don&apos;t have an account?{' '}
                <Link href="/signup" className="font-bold text-red-500 hover:text-red-600 transition-colors">
                  Sign up for free
                </Link>
              </p>
            </div>
          </div>

          {/* Footer */}
          <p className="mt-8 text-center text-sm text-gray-500">
            By signing in, you agree to our{' '}
            <Link href="/terms" className="text-red-500 hover:text-red-600 font-medium">Terms</Link>
            {' '}and{' '}
            <Link href="/privacy" className="text-red-500 hover:text-red-600 font-medium">Privacy Policy</Link>
          </p>

          {/* Trust Badges */}
          <div className="mt-6 flex flex-nowrap items-center justify-center gap-6 text-sm text-gray-500 whitespace-nowrap">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4" />
              <span>256-bit SSL</span>
            </div>
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span>Data encrypted at rest</span>
            </div>
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span>Your data stays private</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function SignInPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-500"></div>
      </div>
    }>
      <SignInContent />
    </Suspense>
  )
}
