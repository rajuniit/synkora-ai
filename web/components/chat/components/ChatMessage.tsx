'use client'

import { useState, useMemo } from 'react'
import Image from 'next/image'
import { Copy, Check, RefreshCw, User, Sparkles, FileText, Image as ImageIcon, Download, File, ThumbsUp, ThumbsDown, Volume2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Message, Attachment } from '../types'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { SourcesList } from './SourceCard'
import { VoicePlayer } from './VoicePlayer'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import { MermaidDiagram } from '@/components/diagrams/MermaidDiagram'
import { DiagramRenderer } from '@/components/diagrams/DiagramRenderer'
import { MarkdownViewer, detectMarkdownUrls } from './MarkdownViewer'
import { DocumentViewer, detectDocumentUrls } from './DocumentViewer'
import { ToolStatusDisplay } from './ToolStatusDisplay'

interface ToolStatus {
  tool_name: string
  status: 'started' | 'completed' | 'error'
  description: string
  details?: {
    file_path?: string
    path?: string
    command?: string
    repo_url?: string
    url?: string
    branch?: string
  }
  duration_ms?: number
  input_tokens?: number
  output_tokens?: number
}

/**
 * Detect image URLs in message content
 * Looks for URLs ending with common image extensions or containing image indicators
 */
function detectImageUrls(content: string): string[] {
  if (!content) return []

  // Regex to match URLs that look like images
  const imageUrlPatterns = [
    // URLs ending with image extensions
    /https?:\/\/[^\s<>"]+\.(?:png|jpg|jpeg|gif|webp|svg|bmp)(?:\?[^\s<>"]*)?/gi,
    // URLs with image in path or query (common for S3/CDN)
    /https?:\/\/[^\s<>"]+(?:screenshot|image|img|photo)[^\s<>"]*\.(?:png|jpg|jpeg|gif|webp)(?:\?[^\s<>"]*)?/gi,
    // S3/MinIO presigned URLs for images (detect by content type or extension before query)
    /https?:\/\/[^\s<>"]+\/[^\s<>"?]+\.(?:png|jpg|jpeg|gif|webp)\?[^\s<>"]+X-Amz-[^\s<>"]*/gi,
  ]

  const imageUrls: Set<string> = new Set()

  for (const pattern of imageUrlPatterns) {
    const matches = content.match(pattern)
    if (matches) {
      matches.forEach(url => {
        // Clean up any trailing punctuation that might have been captured
        const cleanUrl = url.replace(/[.,;:!?)]+$/, '')
        imageUrls.add(cleanUrl)
      })
    }
  }

  return Array.from(imageUrls)
}

interface ChatConfig {
  chat_title?: string
  chat_logo_url?: string
  chat_welcome_message?: string
  chat_placeholder?: string
  chat_primary_color?: string
  chat_background_color?: string
  chat_font_family?: string
}

interface ChatMessageProps {
  message: Message
  isStreaming?: boolean
  thinkingStatus?: string
  toolStatus?: ToolStatus | null
  recentTools?: ToolStatus[]
  streamStartTime?: number | null
  onCopy?: (content: string, messageId: string) => void
  onRetry?: (messageId: string) => void
  className?: string
  chatConfig?: ChatConfig | null
  agentAvatar?: string
  userAvatar?: string
  agentName?: string
}

/**
 * ChatMessage - Individual message component with rich formatting
 * Supports markdown, code highlighting, tables, and media attachments
 */
export function ChatMessage({
  message,
  isStreaming = false,
  thinkingStatus,
  toolStatus,
  recentTools = [],
  streamStartTime,
  onCopy,
  onRetry,
  className,
  chatConfig,
  agentAvatar,
  userAvatar,
  agentName,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  // Get colors from config
  const primaryColor = chatConfig?.chat_primary_color || '#0d9488'
  const fontFamily = chatConfig?.chat_font_family || 'inherit'

  // Memoize URL detection — three regex passes over message content are
  // expensive; skip entirely while streaming (URLs may be partial/incomplete)
  const imageUrls = useMemo(
    () => (!isStreaming ? detectImageUrls(message.content) : []),
    [message.content, isStreaming]
  )

  const handleCopy = async () => {
    if (onCopy) {
      onCopy(message.content, message.id)
    } else {
      await navigator.clipboard.writeText(message.content)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // User message
  if (isUser) {
    return (
      <div className={cn('group', className)}>
        <div className="flex items-center gap-2 mb-1.5">
          <div
            className="w-5 h-5 rounded-full flex items-center justify-center"
            style={{ backgroundColor: primaryColor }}
          >
            <User size={12} className="text-white" />
          </div>
          <span className="text-sm font-bold" style={{ color: primaryColor }}>You</span>
        </div>
        <div className="pl-7">
          <p className="text-[15px] text-gray-800 leading-relaxed whitespace-pre-wrap">{message.content}</p>
          {message.attachments && message.attachments.length > 0 && (
            <div className="mt-2 space-y-1.5">
              {message.attachments.map((attachment, index) => (
                <AttachmentPreview key={index} attachment={attachment} />
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  // Assistant message
  return (
    <div className={cn('group', className)}>
      <div className="flex items-center gap-2 mb-1.5">
        {agentAvatar ? (
          <div className="w-5 h-5 rounded-full overflow-hidden flex items-center justify-center bg-white relative">
            {agentAvatar.startsWith('http://') || agentAvatar.startsWith('https://') ? (
              <Image
                src={agentAvatar}
                alt="Agent"
                width={20}
                height={20}
                className="w-full h-full object-cover"
                unoptimized
              />
            ) : (
              <Image src={agentAvatar} alt="Agent" fill className="object-cover" />
            )}
          </div>
        ) : (
          <div
            className="w-5 h-5 rounded-full flex items-center justify-center"
            style={{ background: primaryColor }}
          >
            <Sparkles size={10} className="text-white" />
          </div>
        )}
        <span className="text-sm font-bold" style={{ color: primaryColor }}>{agentName || 'Assistant'}</span>
      </div>

      <div className="pl-7" style={{ fontFamily }}>
        {/* Document Viewers - Render embedded documents (PDFs, PowerPoint, Google Docs/Sheets) */}
        {/* NOTE: Only render after streaming completes to avoid loading partial/incomplete URLs */}
        {!isStreaming && (() => {
          const documents = detectDocumentUrls(message.content)
          if (documents.length > 0) {
            return documents.map((doc, index) => (
              <DocumentViewer
                key={`doc-${index}`}
                url={doc.url}
                type={doc.type as any}
                primaryColor={primaryColor}
              />
            ))
          }
          return null
        })()}

        {/* Markdown URL Viewers - Render before message content */}
        {/* NOTE: Only render after streaming completes to avoid loading partial/incomplete URLs */}
        {!isStreaming && (() => {
          const markdownUrls = detectMarkdownUrls(message.content)
          if (markdownUrls.length > 0) {
            return markdownUrls.map((url, index) => (
              <MarkdownViewer
                key={`md-${index}`}
                url={url}
                primaryColor={primaryColor}
              />
            ))
          }
          return null
        })()}

        {/* Image URL Viewers - Render embedded images from URLs in content */}
        {/* NOTE: Only render after streaming completes to avoid loading partial/incomplete URLs */}
        {imageUrls.length > 0 && (
          <div className="space-y-3 mb-3">
            {imageUrls.map((url, index) => (
              <EmbeddedImage
                key={`img-${index}`}
                url={url}
                primaryColor={primaryColor}
              />
            ))}
          </div>
        )}

        {/* Tool Status Display - Fixed height todo-list style */}
        {(toolStatus || recentTools.length > 0) && !message.content && (
          <ToolStatusDisplay
            currentTool={toolStatus ?? null}
            recentTools={recentTools}
            primaryColor={primaryColor}
            isStreaming={isStreaming}
            streamStartTime={streamStartTime}
            className="mb-3"
          />
        )}

        {/* Error Message */}
        {message.isError && (
          <div className="flex items-start gap-2 px-3 py-2.5 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 mb-2">
            <svg className="w-4 h-4 mt-0.5 flex-shrink-0 text-red-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span>{message.content}</span>
          </div>
        )}

        {/* Message Content */}
        <div className="prose prose-sm max-w-none prose-gray">
          {!message.isError && thinkingStatus && !message.content && !toolStatus && recentTools.length === 0 ? (
            <div className="flex items-center gap-2 py-1">
              <div className="flex gap-1">
                <span
                  className="w-1.5 h-1.5 rounded-full animate-bounce inline-block"
                  style={{ animationDelay: '0ms', backgroundColor: primaryColor }}
                />
                <span
                  className="w-1.5 h-1.5 rounded-full animate-bounce inline-block"
                  style={{ animationDelay: '150ms', backgroundColor: primaryColor }}
                />
                <span
                  className="w-1.5 h-1.5 rounded-full animate-bounce inline-block"
                  style={{ animationDelay: '300ms', backgroundColor: primaryColor }}
                />
              </div>
              <span className="text-sm text-gray-500">{thinkingStatus}</span>
            </div>
          ) : !message.isError ? (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code: ({ className, children, ...props }: any) => {
                  const match = /language-(\w+)/.exec(className || '')
                  const language = match ? match[1] : ''
                  const codeString = String(children).replace(/\n$/, '')

                  // Mermaid diagram: render as visual diagram instead of code block
                  if (language === 'mermaid') {
                    return (
                      <div className="my-4">
                        <MermaidDiagram code={codeString} />
                      </div>
                    )
                  }

                  // In react-markdown v9, block code is wrapped in <pre>.
                  // We detect inline code by: no language class AND no newlines in content.
                  const isInline = !className && !codeString.includes('\n')

                  if (isInline) {
                    return (
                      <code
                        className="px-1.5 py-0.5 rounded text-[13px] font-mono bg-gray-100 text-gray-800"
                        {...props}
                      >
                        {children}
                      </code>
                    )
                  }

                  return (
                    <div className="relative group/code my-3 -mx-2 max-w-full">
                      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-800 rounded-t-lg border-b border-gray-700">
                        <span className="text-xs text-gray-400 font-mono">{language || 'code'}</span>
                        <button
                          onClick={() => navigator.clipboard.writeText(codeString)}
                          className="text-xs text-gray-400 hover:text-white transition-colors flex items-center gap-1"
                        >
                          <Copy size={12} />
                          Copy
                        </button>
                      </div>
                      <div className="overflow-x-auto">
                        <SyntaxHighlighter
                          style={vscDarkPlus}
                          language={language || 'text'}
                          PreTag="div"
                          className="!rounded-t-none !rounded-b-lg !my-0 !text-[13px]"
                          customStyle={{ margin: 0, borderTopLeftRadius: 0, borderTopRightRadius: 0 }}
                          {...props}
                        >
                          {codeString}
                        </SyntaxHighlighter>
                      </div>
                    </div>
                  )
                },
                pre: ({ children, ...props }: any) => (
                  <div {...props}>{children}</div>
                ),
                table: ({ children, ...props }: any) => (
                  <div className="overflow-x-auto my-3 -mx-2 rounded-lg border border-gray-200">
                    <table className="min-w-full divide-y divide-gray-200" {...props}>
                      {children}
                    </table>
                  </div>
                ),
                thead: ({ children, ...props }: any) => (
                  <thead className="bg-gray-50" {...props}>
                    {children}
                  </thead>
                ),
                tbody: ({ children, ...props }: any) => (
                  <tbody className="bg-white divide-y divide-gray-100" {...props}>
                    {children}
                  </tbody>
                ),
                tr: ({ children, ...props }: any) => (
                  <tr className="hover:bg-gray-50 transition-colors" {...props}>{children}</tr>
                ),
                th: ({ children, ...props }: any) => (
                  <th
                    className="px-3 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide"
                    {...props}
                  >
                    {children}
                  </th>
                ),
                td: ({ children, ...props }: any) => (
                  <td className="px-3 py-2 text-sm text-gray-700" {...props}>
                    {children}
                  </td>
                ),
                a: ({ children, ...props }: any) => (
                  <a
                    className="font-medium hover:underline"
                    style={{ color: primaryColor }}
                    target="_blank"
                    rel="noopener noreferrer"
                    {...props}
                  >
                    {children}
                  </a>
                ),
                h1: ({ children, ...props }: any) => (
                  <h1 className="text-xl font-bold text-gray-900 mb-3 mt-4 first:mt-0 flex items-center gap-2" {...props}>
                    {children}
                  </h1>
                ),
                h2: ({ children, ...props }: any) => (
                  <h2 className="text-lg font-bold text-gray-900 mb-2 mt-4 first:mt-0 flex items-center gap-2" {...props}>
                    {children}
                  </h2>
                ),
                h3: ({ children, ...props }: any) => (
                  <h3 className="text-base font-semibold text-gray-900 mb-2 mt-3 first:mt-0" {...props}>
                    {children}
                  </h3>
                ),
                ul: ({ children, ...props }: any) => (
                  <ul className="list-none ml-0 mb-3 space-y-1" {...props}>
                    {children}
                  </ul>
                ),
                ol: ({ children, ...props }: any) => (
                  <ol className="list-decimal ml-4 mb-3 space-y-1" {...props}>
                    {children}
                  </ol>
                ),
                li: ({ children, ...props }: any) => (
                  <li className="text-[15px] leading-relaxed text-gray-700 relative pl-4 before:content-['•'] before:absolute before:left-0 before:text-gray-400" {...props}>
                    {children}
                  </li>
                ),
                p: ({ children, ...props }: any) => (
                  <p className="mb-3 last:mb-0 text-[15px] leading-relaxed text-gray-700" {...props}>
                    {children}
                  </p>
                ),
                blockquote: ({ children, ...props }: any) => (
                  <blockquote
                    className="border-l-3 pl-3 py-1 my-3 text-gray-600 bg-gray-50 rounded-r"
                    style={{ borderLeftColor: primaryColor, borderLeftWidth: '3px' }}
                    {...props}
                  >
                    {children}
                  </blockquote>
                ),
                hr: ({ ...props }: any) => (
                  <hr className="my-4 border-gray-200" {...props} />
                ),
                strong: ({ children, ...props }: any) => (
                  <strong className="font-semibold text-gray-900" {...props}>
                    {children}
                  </strong>
                ),
                img: ({ src, alt, ...props }: any) => {
                  // Render images inline with the markdown
                  if (!src) return null
                  return (
                    <span className="block my-3">
                      <img
                        src={src}
                        alt={alt || 'Image'}
                        className="max-w-full h-auto rounded-lg border border-gray-200"
                        loading="lazy"
                        {...props}
                      />
                    </span>
                  )
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          ) : null}

          {isStreaming && (
            <span
              className="inline-block w-0.5 h-4 animate-pulse ml-0.5"
              style={{ backgroundColor: primaryColor }}
            />
          )}
        </div>

        {/* RAG Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3">
            <SourcesList sources={message.sources} maxVisible={3} />
          </div>
        )}

        {/* Attachments */}
        {message.attachments && message.attachments.length > 0 && (
          <div className="mt-3 space-y-1.5">
            {message.attachments.map((attachment, index) => (
              <AttachmentPreview key={index} attachment={attachment} />
            ))}
          </div>
        )}

        {/* Charts */}
        {message.metadata?.charts && message.metadata.charts.length > 0 && (
          <div className={`mt-3 ${message.metadata.charts.length >= 2 ? 'grid grid-cols-1 sm:grid-cols-2 gap-3' : 'space-y-3'}`}>
            {message.metadata.charts.map((chart: any, index: number) => {
              const chartData = {
                id: `chart-${index}`,
                title: chart.title,
                description: chart.description || '',
                chart_type: (chart.chart_type || chart.type || 'bar') as string,
                library: chart.library || 'chartjs',
                config: chart.config || {},
                data: chart.data,
                table_data: chart.table_data,
                created_at: new Date().toISOString(),
              }
              return <ChartRenderer key={index} chart={chartData} />
            })}
          </div>
        )}

        {/* Diagrams */}
        {message.metadata?.diagrams && message.metadata.diagrams.length > 0 && (
          <div className="mt-3 space-y-3">
            {message.metadata.diagrams.map((diagram: any, index: number) => (
              <DiagramRenderer key={diagram.id || index} diagram={diagram} />
            ))}
          </div>
        )}

        {/* Message Actions - Inline compact design */}
        {!isStreaming && (
          <div className="flex items-center gap-1 mt-3 pt-2">
            <button
              onClick={handleCopy}
              className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
              title="Copy message"
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
            </button>

            <VoicePlayer text={message.content} className="flex-shrink-0" compact />

            {onRetry && (
              <button
                onClick={() => onRetry(message.id)}
                className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                title="Regenerate response"
              >
                <RefreshCw size={14} />
              </button>
            )}

            {/* Metrics inline */}
            {message.metadata && (message.metadata.usage || message.metadata.timing) && (
              <div className="flex items-center gap-2 ml-auto text-[11px] text-gray-400">
                {message.metadata.timing?.duration && (
                  <span>{message.metadata.timing.duration.toFixed(1)}s</span>
                )}
                {message.metadata.usage?.total_tokens != null && (
                  <span>{message.metadata.usage.total_tokens.toLocaleString()} tokens</span>
                )}
              </div>
            )}

            <span className="text-[11px] text-gray-400 ml-2">
              {formatTimestamp(message.timestamp)}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

interface AttachmentPreviewProps {
  attachment: Attachment
}

function AttachmentPreview({ attachment }: AttachmentPreviewProps) {
  const [imageError, setImageError] = useState(false)
  const [showLightbox, setShowLightbox] = useState(false)

  if (!attachment) return null

  // Get file icon based on type
  const getFileIcon = (fileType: string) => {
    if (fileType.startsWith('image/')) return <ImageIcon size={20} className="text-blue-500" />
    if (fileType === 'application/pdf') return <FileText size={20} className="text-red-500" />
    if (fileType.includes('word') || fileType.includes('document')) return <FileText size={20} className="text-blue-600" />
    return <File size={20} className="text-gray-500" />
  }

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  // Handle uploaded files from our system
  if (attachment.file_id) {
    const isImage = attachment.file_type?.startsWith('image/')

    // Image preview with lightbox
    if (isImage && attachment.file_url && !imageError) {
      return (
        <>
          <div 
            className="rounded-lg overflow-hidden border border-gray-200 cursor-pointer hover:opacity-90 transition-opacity max-w-md"
            onClick={() => setShowLightbox(true)}
          >
            <img
              src={attachment.thumbnail_url || attachment.file_url}
              alt={attachment.file_name || 'Image'}
              className="w-full h-auto"
              onError={() => setImageError(true)}
            />
          </div>

          {/* Lightbox */}
          {showLightbox && (
            <div 
              className="fixed inset-0 z-50 bg-black bg-opacity-90 flex items-center justify-center p-4"
              onClick={() => setShowLightbox(false)}
            >
              <div className="relative max-w-7xl max-h-full">
                <button
                  onClick={() => setShowLightbox(false)}
                  className="absolute top-4 right-4 text-white hover:text-gray-300 bg-black bg-opacity-50 rounded-full p-2"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
                <img
                  src={attachment.file_url}
                  alt={attachment.file_name || 'Image'}
                  className="max-w-full max-h-[90vh] object-contain"
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
            </div>
          )}
        </>
      )
    }

    // Document/file preview
    return (
      <a
        href={attachment.file_url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors border border-gray-200"
      >
        <div className="flex-shrink-0">
          {getFileIcon(attachment.file_type || '')}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">
            {attachment.file_name || 'File'}
          </p>
          <p className="text-xs text-gray-500">
            {attachment.file_size ? formatFileSize(attachment.file_size) : 'Unknown size'}
          </p>
        </div>
        <Download size={16} className="text-gray-400 flex-shrink-0" />
      </a>
    )
  }

  // Legacy attachment types (for backward compatibility)
  switch (attachment.type) {
    case 'image':
      return (
        <div className="rounded-lg overflow-hidden border border-gray-200">
          <img
            src={attachment.url}
            alt={attachment.name || 'Attachment'}
            className="w-full h-auto"
          />
        </div>
      )
    case 'link':
      return (
        <a
          href={attachment.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
        >
          {attachment.thumbnail && (
            <img
              src={attachment.thumbnail}
              alt=""
              className="w-12 h-12 rounded object-cover"
            />
          )}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">
              {attachment.name || 'Link'}
            </p>
            <p className="text-xs text-gray-500 truncate">{attachment.url}</p>
          </div>
        </a>
      )
    default:
      return null
  }
}

/**
 * EmbeddedImage - Renders an image from URL with lightbox support
 * Used for displaying images detected in message content
 */
interface EmbeddedImageProps {
  url: string
  primaryColor?: string
}

function EmbeddedImage({ url, primaryColor = '#0d9488' }: EmbeddedImageProps) {
  const [imageError, setImageError] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [showLightbox, setShowLightbox] = useState(false)

  if (imageError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600">
        <div className="flex items-center gap-2">
          <ImageIcon size={16} />
          <span>Failed to load image</span>
        </div>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs underline mt-1 inline-block"
          style={{ color: primaryColor }}
        >
          Open URL directly
        </a>
      </div>
    )
  }

  return (
    <>
      <div
        className={cn(
          "relative rounded-lg overflow-hidden border border-gray-200 cursor-pointer",
          "hover:border-gray-300 transition-all max-w-lg",
          isLoading && "min-h-[100px] bg-gray-100"
        )}
        onClick={() => setShowLightbox(true)}
      >
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div
              className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin"
              style={{ borderColor: primaryColor, borderTopColor: 'transparent' }}
            />
          </div>
        )}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={url}
          alt="Screenshot"
          loading="lazy"
          className={cn(
            "w-full h-auto transition-opacity",
            isLoading ? "opacity-0" : "opacity-100"
          )}
          onLoad={() => setIsLoading(false)}
          onError={() => {
            setIsLoading(false)
            setImageError(true)
          }}
        />
        {!isLoading && (
          <div className="absolute bottom-2 right-2 bg-black/50 text-white text-xs px-2 py-1 rounded">
            Click to expand
          </div>
        )}
      </div>

      {/* Lightbox */}
      {showLightbox && (
        <div
          className="fixed inset-0 z-50 bg-black bg-opacity-90 flex items-center justify-center p-4"
          onClick={() => setShowLightbox(false)}
        >
          <div className="relative max-w-7xl max-h-full">
            <button
              onClick={() => setShowLightbox(false)}
              className="absolute top-4 right-4 text-white hover:text-gray-300 bg-black bg-opacity-50 rounded-full p-2 z-10"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="absolute top-4 left-4 text-white hover:text-gray-300 bg-black bg-opacity-50 rounded-full p-2 z-10"
              onClick={(e) => e.stopPropagation()}
              title="Open in new tab"
            >
              <Download size={20} />
            </a>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={url}
              alt="Screenshot"
              className="max-w-full max-h-[90vh] object-contain"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        </div>
      )}
    </>
  )
}

function formatTimestamp(date: Date): string {
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (seconds < 60) return 'Just now'
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`

  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}
