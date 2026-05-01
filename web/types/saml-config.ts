/**
 * SAML 2.0 SSO Types
 */

export interface SAMLConfig {
  id: string
  tenant_id: string
  idp_metadata_url: string | null
  has_idp_metadata_xml: boolean
  sp_entity_id: string
  acs_url: string
  email_attribute: string
  name_attribute: string | null
  jit_provisioning: boolean
  force_saml: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface SAMLConfigCreateRequest {
  idp_metadata_url?: string | null
  idp_metadata_xml?: string | null
  sp_entity_id: string
  acs_url: string
  email_attribute: string
  name_attribute?: string | null
  jit_provisioning: boolean
  force_saml: boolean
  is_active: boolean
}
