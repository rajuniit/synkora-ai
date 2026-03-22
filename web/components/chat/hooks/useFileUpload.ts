'use client'

import { useState } from 'react'
import { apiClient } from '@/lib/api/client'
import { Attachment } from '../types'

interface UploadProgress {
  fileId: string
  fileName: string
  progress: number
  status: 'uploading' | 'completed' | 'error'
  error?: string
}

interface UseFileUploadReturn {
  uploadFiles: (files: File[], conversationId: string) => Promise<Attachment[]>
  uploadProgress: UploadProgress[]
  isUploading: boolean
  clearProgress: () => void
}

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB
const MAX_FILES = 5

const ALLOWED_TYPES = [
  // Images
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  // Documents
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // DOCX
  'text/plain',
  'text/markdown',
  'text/csv',
  // Code files
  'text/javascript',
  'text/typescript',
  'text/x-python',
  'application/json',
  'text/html',
  'text/css',
]

export function useFileUpload(): UseFileUploadReturn {
  const [uploadProgress, setUploadProgress] = useState<UploadProgress[]>([])
  const [isUploading, setIsUploading] = useState(false)

  const validateFile = (file: File): string | null => {
    if (file.size > MAX_FILE_SIZE) {
      return `File "${file.name}" exceeds 10MB limit`
    }

    if (!ALLOWED_TYPES.includes(file.type) && !file.name.match(/\.(js|ts|py|md|txt|csv)$/i)) {
      return `File type "${file.type}" is not supported`
    }

    return null
  }

  const uploadFiles = async (files: File[], conversationId: string): Promise<Attachment[]> => {
    if (files.length === 0) return []

    if (files.length > MAX_FILES) {
      throw new Error(`Maximum ${MAX_FILES} files allowed per message`)
    }

    // Validate all files first
    for (const file of files) {
      const error = validateFile(file)
      if (error) {
        throw new Error(error)
      }
    }

    setIsUploading(true)
    const attachments: Attachment[] = []

    try {
      // Upload files sequentially to avoid overwhelming the server
      for (const file of files) {
        const fileId = `${Date.now()}-${file.name}`
        
        // Add to progress tracking
        setUploadProgress((prev: UploadProgress[]) => [
          ...prev,
          {
            fileId,
            fileName: file.name,
            progress: 0,
            status: 'uploading',
          },
        ])

        try {
          const response = await apiClient.uploadChatAttachment(
            conversationId,
            file,
            (progress) => {
              setUploadProgress((prev: UploadProgress[]) =>
                prev.map((p: UploadProgress) =>
                  p.fileId === fileId
                    ? { ...p, progress }
                    : p
                )
              )
            }
          )

          // Extract attachment from response - backend returns { success, message, data: { attachment } }
          const result = response.data?.attachment || response.attachment || response

          // Update progress to completed
          setUploadProgress((prev: UploadProgress[]) =>
            prev.map((p: UploadProgress) =>
              p.fileId === fileId
                ? { ...p, progress: 100, status: 'completed' }
                : p
            )
          )

          // Create attachment object matching backend structure
          const attachment = {
            file_id: result.file_id,
            file_name: result.file_name,
            file_type: result.file_type,
            file_size: result.file_size,
            file_url: result.download_url || result.file_url, // Use download_url (presigned) for display
            thumbnail_url: result.thumbnail_url,
            extracted_text: result.extracted_text,
          }

          attachments.push(attachment as any)
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Upload failed'
          
          setUploadProgress((prev: UploadProgress[]) =>
            prev.map((p: UploadProgress) =>
              p.fileId === fileId
                ? { ...p, status: 'error', error: errorMessage }
                : p
            )
          )

          throw new Error(`Failed to upload ${file.name}: ${errorMessage}`)
        }
      }

      return attachments
    } finally {
      setIsUploading(false)
    }
  }

  const clearProgress = () => {
    setUploadProgress([])
  }

  return {
    uploadFiles,
    uploadProgress,
    isUploading,
    clearProgress,
  }
}
