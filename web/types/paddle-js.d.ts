// Type declarations for @paddle/paddle-js
// This file provides type declarations when the package is not installed

declare module '@paddle/paddle-js' {
  export interface Paddle {
    Checkout: {
      open: (options: CheckoutOpenOptions) => void
      close: () => void
    }
  }

  export interface CheckoutOpenOptions {
    items?: Array<{ priceId: string; quantity: number }>
    customer?: { id: string }
    customData?: Record<string, string>
    transactionId?: string
    settings?: {
      displayMode?: 'overlay' | 'inline'
      theme?: 'light' | 'dark'
      locale?: string
      successUrl?: string
    }
  }

  export interface InitializePaddleOptions {
    token: string
    environment: 'sandbox' | 'production'
  }

  export const Environments: {
    sandbox: 'sandbox'
    production: 'production'
  }

  export function initializePaddle(options: InitializePaddleOptions): Promise<Paddle | null>
}
