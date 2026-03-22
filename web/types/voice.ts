// Voice Chat Type Definitions

export interface VoiceConfig {
  enabled: boolean
  stt_provider: 'web_speech' | 'openai_whisper'
  tts_provider: 'web_speech' | 'openai_tts' | 'elevenlabs'
  voice_id?: string
  language?: string
  mode: 'push_to_talk' | 'continuous'
  auto_play_responses: boolean
}

export interface VoiceApiKey {
  id: string
  provider: 'openai' | 'elevenlabs'
  name: string
  created_at: string
  last_used_at?: string
}

export interface CreateVoiceApiKeyRequest {
  provider: 'openai' | 'elevenlabs'
  name: string
  api_key: string
}

export interface Voice {
  id: string
  name: string
  language?: string
  gender?: string
  preview_url?: string
}

export interface VoiceProviders {
  openai_tts: Voice[]
  elevenlabs: Voice[]
}

export interface VoiceUsage {
  id: string
  provider: string
  operation_type: 'stt' | 'tts'
  characters_processed?: number
  duration_seconds?: number
  cost: number
  agent_id?: string
  agent_name?: string
  created_at: string
}

export interface VoiceUsageStats {
  total_cost: number
  total_requests: number
  by_provider: {
    [key: string]: {
      cost: number
      requests: number
    }
  }
  by_operation: {
    stt: {
      cost: number
      requests: number
    }
    tts: {
      cost: number
      requests: number
    }
  }
}
