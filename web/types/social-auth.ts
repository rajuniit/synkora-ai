/**
 * Social Authentication Types
 * 
 * Type definitions for social login providers and authentication
 */

export type SocialProvider = 'google' | 'microsoft' | 'apple';

export interface SocialAuthProvider {
  provider: SocialProvider;
  provider_user_id: string;
  email: string;
  display_name?: string;
  linked_at: string;
}

export interface LinkProviderRequest {
  provider: SocialProvider;
  redirect_url?: string;
}

export interface ProviderStatus {
  linked: boolean;
  provider?: SocialProvider;
}

export interface SocialLoginCallbackParams {
  login?: string;
  provider?: string;
  email?: string;
  error?: string;
  message?: string;
}

// Provider display information
export interface ProviderInfo {
  id: SocialProvider;
  name: string;
  icon: string;
  color: string;
  bgColor: string;
  hoverColor: string;
}

export const PROVIDER_INFO: Record<SocialProvider, ProviderInfo> = {
  google: {
    id: 'google',
    name: 'Google',
    icon: 'google',
    color: '#4285F4',
    bgColor: 'bg-white',
    hoverColor: 'hover:bg-gray-50',
  },
  microsoft: {
    id: 'microsoft',
    name: 'Microsoft',
    icon: 'microsoft',
    color: '#00A4EF',
    bgColor: 'bg-white',
    hoverColor: 'hover:bg-gray-50',
  },
  apple: {
    id: 'apple',
    name: 'Apple',
    icon: 'apple',
    color: '#000000',
    bgColor: 'bg-black',
    hoverColor: 'hover:bg-gray-900',
  },
};
