import '../styles/globals.css'
import { Inter } from 'next/font/google'
import { Toaster } from 'react-hot-toast'
import { SecurityInit } from '../components/common/SecurityInit'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'Synkora - AI Application Platform',
  description: 'Build and deploy AI applications',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <SecurityInit />
        {children}
        <Toaster 
          position="top-right"
          toastOptions={{
            // Success toasts - new brand color #ff444f
            success: {
              duration: 4000,
              style: {
                background: '#ffffff',
                color: '#1f2937', // gray-800
                border: '2px solid #ff444f',
                padding: '16px',
                borderRadius: '12px',
                fontWeight: '500',
                boxShadow: '0 10px 15px -3px rgba(255, 68, 79, 0.2), 0 4px 6px -2px rgba(255, 68, 79, 0.1)',
              },
              iconTheme: {
                primary: '#ff444f',
                secondary: '#ffffff',
              },
            },
            // Error toasts
            error: {
              duration: 5000,
              style: {
                background: '#fee2e2', // red-100
                color: '#7f1d1d', // red-900
                border: '2px solid #ef4444', // red-500
                padding: '16px',
                borderRadius: '12px',
                fontWeight: '500',
                boxShadow: '0 10px 15px -3px rgba(239, 68, 68, 0.2), 0 4px 6px -2px rgba(239, 68, 68, 0.1)',
              },
              iconTheme: {
                primary: '#ef4444', // red-500
                secondary: '#fef2f2', // red-50
              },
            },
            // Loading toasts - new brand color
            loading: {
              style: {
                background: '#ffffff',
                color: '#1f2937', // gray-800
                border: '2px solid #ff444f',
                padding: '16px',
                borderRadius: '12px',
                fontWeight: '500',
                boxShadow: '0 10px 15px -3px rgba(255, 68, 79, 0.2), 0 4px 6px -2px rgba(255, 68, 79, 0.1)',
              },
              iconTheme: {
                primary: '#ff444f',
                secondary: '#ffffff',
              },
            },
            // Default/custom toasts
            style: {
              background: '#ffffff',
              color: '#1f2937', // gray-800
              border: '2px solid #ff444f',
              padding: '16px',
              borderRadius: '12px',
              fontWeight: '500',
              boxShadow: '0 10px 15px -3px rgba(255, 68, 79, 0.2), 0 4px 6px -2px rgba(255, 68, 79, 0.1)',
            },
          }}
        />
      </body>
    </html>
  )
}
