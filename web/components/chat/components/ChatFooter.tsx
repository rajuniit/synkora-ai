'use client'

import { ChatConfigResponse } from '@/lib/api/chat-config'

interface ChatFooterProps {
  chatConfig?: ChatConfigResponse | null
}

export function ChatFooter({ chatConfig }: ChatFooterProps) {
  const primaryColor = chatConfig?.chat_page_config?.colors?.primary || '#0d9488'
  const footerText = chatConfig?.chat_page_config?.marketing?.footer_text || '© 2025 All rights reserved'
  const footerLinks = chatConfig?.chat_page_config?.marketing?.footer_links || []

  return (
    <div 
      className="border-t bg-gradient-to-br from-gray-50 via-white to-gray-50 backdrop-blur-sm"
      style={{
        borderColor: `${primaryColor}20`,
      }}
    >
      <div className="px-6 py-4">
        {/* Main Footer Content */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          {/* Footer Text with Icon */}
          <div className="flex items-center gap-3">
            <div 
              className="flex items-center justify-center w-8 h-8 rounded-lg shadow-sm"
              style={{
                background: `linear-gradient(135deg, ${primaryColor}15, ${primaryColor}05)`,
                border: `1px solid ${primaryColor}20`,
              }}
            >
              <svg 
                className="w-4 h-4" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
                style={{ color: primaryColor }}
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M13 10V3L4 14h7v7l9-11h-7z" 
                />
              </svg>
            </div>
            <span className="text-sm font-medium text-gray-700">
              {footerText}
            </span>
          </div>

          {/* Footer Links */}
          {footerLinks.length > 0 && (
            <div className="flex items-center gap-1">
              {footerLinks.map((link, index) => (
                <a
                  key={index}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 text-sm font-medium rounded-lg transition-all duration-200 hover:shadow-sm"
                  style={{
                    color: primaryColor,
                    background: `${primaryColor}08`,
                    border: `1px solid ${primaryColor}15`,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = `${primaryColor}15`
                    e.currentTarget.style.transform = 'translateY(-1px)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = `${primaryColor}08`
                    e.currentTarget.style.transform = 'translateY(0)'
                  }}
                >
                  {link.text}
                </a>
              ))}
            </div>
          )}
        </div>

        {/* Powered By Section */}
        <div className="mt-3 pt-3 border-t flex items-center justify-center gap-2"
          style={{
            borderColor: `${primaryColor}10`,
          }}
        >
          <span className="text-xs text-gray-500">Powered by</span>
          <div className="flex items-center gap-1.5">
            <div 
              className="w-5 h-5 rounded flex items-center justify-center"
              style={{
                background: `linear-gradient(135deg, ${primaryColor}, ${primaryColor}dd)`,
              }}
            >
              <svg 
                className="w-3 h-3 text-white" 
                fill="currentColor" 
                viewBox="0 0 20 20"
              >
                <path 
                  fillRule="evenodd" 
                  d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" 
                  clipRule="evenodd" 
                />
              </svg>
            </div>
            <span 
              className="text-xs font-semibold"
              style={{ color: primaryColor }}
            >
              AI Agent
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
