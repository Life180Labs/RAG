export type ProviderType =
  | 'openai'
  | 'anthropic'
  | 'gemini'
  | 'groq'
  | 'openrouter'
  | 'voyage'
  | 'jina'
  | 'cohere'
  | 'pinecone';

export const PROVIDER_TYPES: ProviderType[] = [
  'openai',
  'anthropic',
  'gemini',
  'groq',
  'openrouter',
  'voyage',
  'jina',
  'cohere',
  'pinecone',
];

export interface ProviderCredential {
  id: string;
  organization_id: string;
  provider: ProviderType;
  last_four: string;
  created_at: string;
  updated_at: string;
}
