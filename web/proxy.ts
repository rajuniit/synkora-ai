import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'
const APP_DOMAIN = process.env.NEXT_PUBLIC_APP_DOMAIN || ''
const isDevelopment = process.env.NODE_ENV === 'development'

export async function proxy(request: NextRequest) {
  // In Kubernetes/proxy environments, check X-Forwarded-Host first
  // This preserves the original domain name from the client
  const forwardedHost = request.headers.get('x-forwarded-host')
  const originalHost = request.headers.get('x-original-host')
  const hostHeader = request.headers.get('host') || ''
  
  // Prefer forwarded headers over direct host header (for proxy/ingress scenarios)
  const hostname = forwardedHost || originalHost || hostHeader
  const pathname = request.nextUrl.pathname
  
  // Handle /chat?agent_name=X redirect
  if (pathname === '/chat') {
    const agentName = request.nextUrl.searchParams.get('agent_name')
    
    if (agentName) {
      // Redirect to /agents/[agentName]/chat
      const url = new URL(`/agents/${encodeURIComponent(agentName)}/chat`, request.url)
      return NextResponse.redirect(url)
    }
  }
  
  // Skip domain resolution for raw IP addresses (K8s pod IPs, health probes, etc.)
  const isIpAddress = /^\d{1,3}(\.\d{1,3}){3}(:\d+)?$/.test(hostname)

  // Skip domain resolution if the request is for the main app domain
  const isAppDomain = APP_DOMAIN && (hostname === APP_DOMAIN || hostname.endsWith(`.${APP_DOMAIN}`))

  // Handle subdomain routing (e.g., product-owner.synkora.local)
  // Check if it's a subdomain (not localhost, not a bare IP, not the main app domain) and requesting root path
  if (pathname === '/' && !isAppDomain && !hostname.startsWith('localhost:') && hostname.includes('.') && !isIpAddress) {
    try {
      // Create abort controller for timeout
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 2000) // 2 second timeout
      
      // Resolve the domain via API
      const response = await fetch(`${API_URL}/api/domains/resolve?hostname=${hostname}`, {
        signal: controller.signal,
      })
      
      clearTimeout(timeoutId)
      
      if (response.ok) {
        const data = await response.json()
        
        if (data.agent_name) {
          // Redirect to agent chat page
          const url = new URL(`/agents/${encodeURIComponent(data.agent_name)}/chat`, request.url)
          return NextResponse.redirect(url)
        }
      }
    } catch (error) {
      // Silently fail - continue to default behavior if resolution fails
      // Only log in development mode
      if (isDevelopment) {
        console.debug('Domain resolution failed:', error)
      }
    }
  }
  
  return NextResponse.next()
}

export const config = {
  matcher: ['/', '/chat'],
}
