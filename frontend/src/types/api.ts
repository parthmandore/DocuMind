/**
 * DocuMind API TypeScript Contracts (Phase 5.0 / 5.1)
 *
 * Defines strictly-typed interfaces mirroring the FastAPI backend schemas
 * for local document intelligence, search, grounded generation, and conversations.
 */

// --- System & Health ---

export type AIProviderType = 'ollama' | 'groq';

export interface HealthResponse {
  status: 'healthy' | 'degraded';
  app_name: string;
  database: string;
  ollama_status: string;
  free_disk_gb: number;
  active_provider?: AIProviderType;
  generation_provider_status?: string;
  embedding_provider_status?: string;
  groq_configured?: boolean;
  arbiter_status?: string;
  ram_total_gb?: number;
  ram_available_gb?: number;
  ram_used_percent?: number;
  cpu_count?: number;
}

export interface AIProviderHealth {
  status: string;
  model: string;
  available: boolean;
  message?: string | null;
}

export interface AIProviderSettingsResponse {
  active_provider: AIProviderType;
  available_providers: string[];
  generation_model: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dimension: number;
  embedding_available: boolean;
  groq_configured: boolean;
  provider_health: AIProviderHealth;
  warning?: string | null;
}

export interface UpdateAIProviderRequest {
  provider: AIProviderType;
}

// --- Documents ---

export type DocumentStatus =
  | 'PENDING'
  | 'PROCESSING'
  | 'EXTRACTED'
  | 'CHUNKED'
  | 'EMBEDDING'
  | 'INDEXED'
  | 'COMPLETED'
  | 'FAILED';

export interface BoundingBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  page: number;
}

export interface SectionSchema {
  id: string;
  title: string;
  section_level: number;
  page_number: number;
  order_index: number;
  content: string;
  metadata?: Record<string, unknown>;
}

export interface ChunkSchema {
  id: string;
  chunk_index: number;
  page_number: number;
  text: string;
  token_count: number;
  bboxes: BoundingBox[];
}

export interface DocumentResponse {
  id: string;
  title: string;
  filename: string;
  mime_type: string;
  file_size_bytes: number;
  file_hash: string;
  status: DocumentStatus;
  error_message?: string | null;
  quality_warnings: string[];
  total_pages: number;
  total_words: number;
  total_sections: number;
  total_chunks: number;
  doc_metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResponse {
  document: DocumentResponse;
  job_id: string;
  is_duplicate: boolean;
  message: string;
}

export interface DocumentContentResponse {
  document_id: string;
  title: string;
  total_pages: number;
  total_words: number;
  quality_warnings: string[];
  sections: SectionSchema[];
  chunks: ChunkSchema[];
}

export interface IndexingStatusResponse {
  document_id: string;
  status: string;
  total_chunks: number;
  embedded_chunks: number;
  embedding_model?: string | null;
  embedding_dimension?: number | null;
  indexed_at?: string | null;
  is_indexed: boolean;
  percent_complete?: number;
  is_lexical_ready?: boolean;
}

export interface ReindexResponse {
  document_id: string;
  job_id: string;
  status: string;
  message: string;
}

// --- Processing Jobs ---

export type JobStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';

export interface JobResponse {
  id: string;
  document_id: string;
  job_type: string;
  status: JobStatus;
  attempts: number;
  error_details?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}

// --- Search & Retrieval ---

export type RetrievalMode = 'hybrid' | 'dense' | 'lexical';

export interface SearchHitSchema {
  chunk_id: string;
  document_id: string;
  section_id?: string | null;
  page_number: number;
  text: string;
  bboxes: BoundingBox[];
  dense_score?: number | null;
  lexical_score?: number | null;
  fused_score: number;
  rank: number;
  metadata: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  mode: RetrievalMode;
  total_results: number;
  results: SearchHitSchema[];
}

// --- Grounded Question Answering & Citations ---

export type ClaimSupportState =
  | 'supported'
  | 'partially_supported'
  | 'unsupported'
  | 'contradicted'
  | 'insufficient_evidence';

export interface SupportingClaim {
  claim_id: string;
  claim_text: string;
  supporting_chunk_ids: string[];
  citation_ids: string[];
  verification_status: 'verified' | 'unverified' | 'partially_verified';
  support_state: ClaimSupportState;
  numerical_verified?: boolean | null;
  entities_verified?: boolean | null;
  temporal_verified?: boolean | null;
  reasoning: string;
}

export interface CitationItem {
  citation_id: string;
  document_id: string;
  document_filename: string;
  chunk_id: string;
  page_number: number;
  section_title: string;
  exact_quote: string;
  bounding_boxes: BoundingBox[];
  verification_status: 'verified' | 'quote_mismatch' | 'page_mismatch' | 'source_missing';
  claim_support_status: 'supported' | 'unsupported' | 'partial';
}

export interface GroundedAnswer {
  answer_id: string;
  conversation_id?: string | null;
  question: string;
  answer: string;
  status: 'answered' | 'partially_answered' | 'abstained';
  abstained: boolean;
  confidence: number;
  evidence_assessment: string;
  supporting_claims: SupportingClaim[];
  citations: CitationItem[];
  unsupported_parts: string[];
  contradictions: string[];
  processing_metadata: {
    latency_seconds: number;
    query_processing_ms: number;
    evidence_selection_ms: number;
    llm_latency_seconds: number;
    verification_ms: number;
    candidate_chunks_evaluated: number;
    evidence_tokens: number;
  };
}

export interface QueryRequest {
  question: string;
  document_ids?: string[] | null;
  conversation_id?: string | null;
}

// --- Conversations & History ---

export interface MessageCitationResponse {
  id: string;
  message_id: string;
  chunk_id: string;
  document_id?: string | null;
  document_filename?: string | null;
  page_number: number;
  exact_quote: string;
  bbox?: Record<string, unknown> | null;
  is_verified: boolean;
  grounding_score: number;
  created_at: string;
}

export interface MessageResponse {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  thinking_trace?: string | null;
  message_metadata?: Record<string, any> | null;
  created_at: string;
  citations: MessageCitationResponse[];
}

export interface ConversationResponse {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetailResponse {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: MessageResponse[];
}

export interface CreateConversationRequest {
  title?: string | null;
}

export interface UpdateConversationRequest {
  title: string;
}

// --- Citation Analytics (Phase 5.9) ---

export interface CorpusOverview {
  total_documents: number;
  total_chunks: number;
  total_indexed_chunks: number;
  total_queries: number;
  total_answers: number;
  total_citations: number;
  verified_citations: number;
  unverified_citations: number;
  abstained_answers: number;
}

export interface CitationQualityMetrics {
  citation_verification_rate: number;
  claim_support_rate: number;
  supported_claims_count: number;
  partially_supported_claims_count: number;
  unsupported_claims_count: number;
  contradicted_claims_count: number;
  insufficient_evidence_count: number;
  total_evaluated_claims: number;
  total_contradictions_detected: number;
}

export interface ClaimDistributionItem {
  status: string;
  count: number;
  percentage: number;
}

export interface DocumentAnalyticsItem {
  document_id: string;
  title: string;
  filename: string;
  total_chunks: number;
  total_citations: number;
  verified_citations: number;
  verification_rate: number;
}

export interface ContradictionLogItem {
  message_id: string;
  created_at: string;
  claim_text: string;
  conflicting_passage: string;
  source_document_title?: string | null;
  page_number?: number | null;
}

export interface DailyActivityItem {
  date: string;
  queries: number;
  citations: number;
  verified_citations: number;
}

export interface InsightsResponse {
  overview: CorpusOverview;
  quality: CitationQualityMetrics;
  claim_distribution: ClaimDistributionItem[];
  top_cited_documents: DocumentAnalyticsItem[];
  contradiction_logs: ContradictionLogItem[];
  daily_activity: DailyActivityItem[];
}

// --- Support & Contact API ---

export interface ContactRequest {
  name: string;
  email: string;
  category: 'bug' | 'feedback' | 'feature' | 'general';
  subject: string;
  message: string;
  website?: string;
}

export interface ContactResponse {
  status: string;
  message: string;
  reference_id: string;
  timestamp?: string;
}

// --- Generic API Error Envelope ---

export interface ApiErrorDetail {
  detail: string | Array<{ loc: (string | number)[]; msg: string; type: string }>;
  status?: number;
}
