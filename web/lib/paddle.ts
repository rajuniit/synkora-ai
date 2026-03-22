/**
 * Paddle.js Integration
 *
 * Standard Paddle.js overlay checkout implementation.
 * Uses event callbacks for checkout.completed and checkout.closed events.
 */

type PaddleEnvironment = 'sandbox' | 'production'

interface PaddleInstance {
  Checkout: {
    open: (options: CheckoutOptions) => void
    close: () => void
  }
}

interface CheckoutOptions {
  transactionId?: string
  items?: Array<{ priceId: string; quantity: number }>
  customer?: { id: string }
  customData?: Record<string, string>
  settings?: {
    displayMode?: 'overlay' | 'inline'
    theme?: 'light' | 'dark'
    locale?: string
    successUrl?: string
  }
}

interface PaddleEvent {
  name?: string
  type?: string
  data?: any
}

export interface PaddleConfig {
  clientToken: string
  environment: PaddleEnvironment
}

export interface CheckoutCallbacks {
  onComplete?: (data: any) => void
  onClose?: () => void
}

let paddleInstance: PaddleInstance | null = null
let currentCallbacks: CheckoutCallbacks | null = null

/**
 * Initialize Paddle.js with event handling
 */
export async function initPaddle(config: PaddleConfig): Promise<PaddleInstance> {
  if (paddleInstance) {
    return paddleInstance
  }

  const { initializePaddle } = await import('@paddle/paddle-js')

   
  paddleInstance = await (initializePaddle as any)({
    token: config.clientToken,
    environment: config.environment,
    eventCallback: (event: PaddleEvent) => {
      const eventName = event.name || event.type || ''

      if (eventName === 'checkout.completed') {
        // Close the checkout overlay
        if (paddleInstance) {
          paddleInstance.Checkout.close()
        }
        if (currentCallbacks?.onComplete) {
          currentCallbacks.onComplete(event.data)
        }
        currentCallbacks = null
      } else if (eventName === 'checkout.closed') {
        if (currentCallbacks?.onClose) {
          currentCallbacks.onClose()
        }
        currentCallbacks = null
      }
    },
  }) as PaddleInstance

  if (!paddleInstance) {
    throw new Error('Failed to initialize Paddle')
  }

  return paddleInstance
}

/**
 * Open Paddle checkout overlay with a transaction ID
 */
export async function openCheckout(
  config: PaddleConfig,
  transactionId: string,
  callbacks?: CheckoutCallbacks
): Promise<void> {
  const paddle = await initPaddle(config)

  // Set callbacks for this checkout session
  currentCallbacks = callbacks || null

  paddle.Checkout.open({
    transactionId,
    settings: {
      displayMode: 'overlay',
      theme: 'light',
      locale: 'en',
    },
  })
}

/**
 * Close any open checkout
 */
export async function closeCheckout(config: PaddleConfig): Promise<void> {
  if (paddleInstance) {
    paddleInstance.Checkout.close()
  }
}
