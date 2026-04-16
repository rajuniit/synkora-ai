import axios, { AxiosInstance, AxiosError } from 'axios'
import { secureStorage } from '../auth/secure-storage'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'

export class APIClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      // Send the HttpOnly cookie set by the backend on login.
      // Required for cookie-based auth (OAuth redirects, SSR) and ensures
      // the browser automatically uses the backend-managed session cookie.
      withCredentials: true,
    })

    this.client.interceptors.request.use(
      (config) => {
        if (typeof window !== 'undefined') {
          // Use secure token storage instead of localStorage
          const token = secureStorage.getAccessToken()
          if (token) {
            config.headers.Authorization = `Bearer ${token}`
          }
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as any

        // Skip token refresh for authentication endpoints (login, signup, etc.)
        // NOTE: '/oauth/' alone is too broad — it would match /api/v1/oauth/apps CRUD.
        // Only skip refresh for the actual OAuth flow URLs (authorize/callback/redirect).
        const url = originalRequest?.url || ''
        const isAuthEndpoint = url.includes('/auth/') ||
                              /\/oauth\/[^/]+\/(authorize|callback|redirect)/.test(url) ||
                              url.includes('/signin') ||
                              url.includes('/signup') ||
                              url.includes('/login') ||
                              url.includes('/register') ||
                              url.includes('/refresh') ||
                              url.includes('/logout')

        // Check if this is a 401 error and we haven't already retried this request
        // Skip token refresh for auth endpoints - they should return 401 directly
        if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint && typeof window !== 'undefined') {
          originalRequest._retry = true

          // Try to refresh token
          const refreshSuccess = await secureStorage.refreshAccessToken()

          if (refreshSuccess) {
            // Update the authorization header with the new token
            const newToken = secureStorage.getAccessToken()
            if (newToken) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`
            }

            // Retry the original request with the new token
            return this.client(originalRequest)
          } else {
            // If refresh fails, clear tokens and redirect
            secureStorage.clearTokens()
            window.location.href = '/signin'
          }
        }

        return Promise.reject(error)
      }
    )
  }

  // Generic request method for custom API calls
  async request(method: string, url: string, data?: any, config?: any): Promise<any> {
    const response = await this.client.request({
      method,
      url,
      data,
      ...config
    })
    return response.data
  }

  // Expose axios instance for domain modules
  get axios(): AxiosInstance {
    return this.client
  }
}

export const apiClient = new APIClient()
