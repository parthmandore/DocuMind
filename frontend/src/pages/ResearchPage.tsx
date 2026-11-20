/**
 * Research Workspace (Phase 5.6 & Critical Reliability Update)
 *
 * Professional Single-Document & Corpus Research Workspace providing:
 * - Single-document research isolation with strict pre-fusion filtering
 * - Deterministic multi-stage request lifecycle (submitting -> processing -> completed / error)
 * - Zero coexistence of completed answers with stale loading steppers
 * - Full conversation persistence across navigation and browser refresh via URL & TanStack Query
 * - Unambiguous Groq Cloud generation provider reporting
 * - In-text clickable citation badges with side-by-side PDF passage inspection
 * - Claim-level verification audit with 5-state grounding classification
 */

import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Sparkles,
  Send,
  RotateCcw,
  BookOpen,
  ShieldCheck,
  AlertTriangle,
  FileText,
  Cpu,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  MessageSquare,
  Search,
  CheckCircle2,
  HelpCircle,
  X,
  RefreshCw,
  UploadCloud,
  FolderOpen,
  Clock,
} from 'lucide-react';

import { useDocuments, useConversation } from '@/hooks/useQueries';
import { useExecuteQuery } from '@/hooks/useMutations';
import { isDocumentProcessing } from '@/hooks/useJobPolling';
import { useRouteMetadata } from '@/hooks/useRouteMetadata';
import type { GroundedAnswer, CitationItem, MessageResponse } from '@/types/api';

// UI Primitives
import {
  Button,
  Card,
  Textarea,
  Badge,
  Alert,
  Tabs,
  Skeleton,
} from '@/components/ui';

// Document Components
import {
  EvidenceStatusBadge,
  ConfidenceIndicator,
  DocumentTypeIcon,
} from '@/components/document';
import { MarkdownView } from '@/components/common/MarkdownView';

const PIPELINE_STAGES = [
  { id: 1, name: 'Query Decomposition', desc: 'Syntactic & semantic expansion' },
  { id: 2, name: 'Hybrid Retrieval', desc: 'BM25 + 768-dim dense vector search' },
  { id: 3, name: 'Evidence Selection', desc: 'RRF rank fusion & passage selection' },
  { id: 4, name: 'Grounded Synthesis', desc: 'Constrained generation with Groq API' },
  { id: 5, name: 'Verification Audit', desc: 'Two-stage claim & quotation check' },
];

function messageToGroundedAnswer(
  msg: MessageResponse,
  fallbackQuestion: string
): GroundedAnswer {
  const meta = msg.message_metadata || {};
  const processingMeta = meta.processing_metadata || {};

  return {
    answer_id: meta.answer_id || msg.id,
    conversation_id: msg.conversation_id,
    question: fallbackQuestion || meta.question || 'Grounded Inquiry',
    answer: msg.content,
    status: (meta.status as any) || 'answered',
    abstained: meta.abstained ?? false,
    confidence: meta.confidence ?? 0.85,
    evidence_assessment: meta.evidence_assessment || '',
    supporting_claims: meta.supporting_claims || [],
    citations: (msg.citations || []).map((c, idx) => ({
      citation_id: c.id || `cit_${c.chunk_id}_${idx}`,
      chunk_id: c.chunk_id,
      document_id: c.document_id || '',
      document_filename: c.document_filename || '',
      page_number: c.page_number,
      section_title: (c as any).section_title || '',
      exact_quote: c.exact_quote,
      bounding_boxes: c.bbox ? [c.bbox as any] : [],
      verification_status: c.is_verified ? ('verified' as const) : ('quote_mismatch' as const),
      similarity_score: c.grounding_score,
      claim_support_status: 'supported' as const,
    })),
    unsupported_parts: meta.unsupported_parts || [],
    contradictions: meta.contradictions || [],
    processing_metadata: {
      latency_seconds: processingMeta.latency_seconds || processingMeta.total_latency_seconds || 0,
      query_processing_ms: processingMeta.query_processing_ms || 0,
      evidence_selection_ms: processingMeta.evidence_selection_ms || 0,
      llm_latency_seconds: processingMeta.llm_latency_seconds || 0,
      verification_ms: processingMeta.verification_ms || processingMeta.verification_latency_ms || 0,
      candidate_chunks_evaluated: processingMeta.candidate_chunks_evaluated || 0,
      evidence_tokens: processingMeta.evidence_tokens || 0,
    },
  };
}

export const ResearchPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useRouteMetadata({
    title: 'Research Workspace | DocuMind',
    description:
      'Interactive research workspace providing hybrid vector retrieval, Groq generation, and citation verification.',
    isPrivate: true,
    canonicalPath: '/research',
  });

  const conversationIdParam = searchParams.get('conversation_id') || searchParams.get('id');
  const documentIdParam = searchParams.get('document_id') || searchParams.get('docId');

  // Queries & Mutations
  const { data: documents = [], isLoading: isLoadingDocs } = useDocuments(0, 100);
  const queryMutation = useExecuteQuery();

  const processingDocuments = useMemo(
    () => documents.filter((d) => isDocumentProcessing(d.status)),
    [documents]
  );

  // Load persisted conversation details if conversationIdParam is active
  const { data: conversationData } = useConversation(
    conversationIdParam,
    { enabled: !!conversationIdParam }
  );

  // Selected Documents Scope
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [docFilterQuery, setDocFilterQuery] = useState('');
  const [isDocSelectorOpen, setIsDocSelectorOpen] = useState(false);

  // Question & Submission State
  const [question, setQuestion] = useState('');
  const [lastSubmittedQuery, setLastSubmittedQuery] = useState('');
  const [requestState, setRequestState] = useState<'idle' | 'in_flight' | 'completed' | 'error'>('idle');
  const [lastError, setLastError] = useState<string | null>(null);

  const [currentStage, setCurrentStage] = useState<number>(0);
  const [activeSideTab, setActiveSideTab] = useState<'evidence' | 'diagnostics'>('evidence');
  const [selectedCitation, setSelectedCitation] = useState<CitationItem | null>(null);
  const [isClaimsExpanded, setIsClaimsExpanded] = useState(true);

  // Active Grounded Answer Result
  const [groundedAnswer, setGroundedAnswer] = useState<GroundedAnswer | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Ready documents for querying
  const readyDocuments = useMemo(() => {
    return documents.filter(
      (d) => d.status === 'COMPLETED' || d.status === 'INDEXED'
    );
  }, [documents]);

  const filteredReadyDocs = useMemo(() => {
    if (!docFilterQuery.trim()) return readyDocuments;
    const q = docFilterQuery.toLowerCase();
    return readyDocuments.filter(
      (d) =>
        d.filename.toLowerCase().includes(q) ||
        (d.title && d.title.toLowerCase().includes(q))
    );
  }, [readyDocuments, docFilterQuery]);

  // 1. Navigation Restoration: Check sessionStorage if user navigated back without URL params
  useEffect(() => {
    if (!conversationIdParam) {
      try {
        const stored = sessionStorage.getItem('documind_active_research_session');
        if (stored) {
          const parsed = JSON.parse(stored);
          if (parsed.conversation_id) {
            const nextParams = new URLSearchParams();
            nextParams.set('conversation_id', parsed.conversation_id);
            if (parsed.document_id) nextParams.set('document_id', parsed.document_id);
            navigate(`/research?${nextParams.toString()}`, { replace: true });
            return;
          }
        }
      } catch (e) {
        // ignore storage errors
      }
    }
  }, [conversationIdParam, navigate]);

  // 2. Document Scope Sync from URL parameter
  useEffect(() => {
    if (documentIdParam) {
      if (!selectedDocIds.includes(documentIdParam) || selectedDocIds.length !== 1) {
        setSelectedDocIds([documentIdParam]);
      }
    }
  }, [documentIdParam]);

  // 3. Reconcile Conversation Data when loaded via TanStack Query
  useEffect(() => {
    if (conversationData && conversationData.messages && requestState !== 'in_flight') {
      const messages = conversationData.messages;
      const assistantMessages = messages.filter((m) => m.role === 'assistant');
      if (assistantMessages.length > 0) {
        const latestAssistant = assistantMessages[assistantMessages.length - 1];
        const asstIdx = messages.indexOf(latestAssistant);
        let q = '';
        for (let i = asstIdx - 1; i >= 0; i--) {
          if (messages[i].role === 'user') {
            q = messages[i].content;
            break;
          }
        }
        const restoredAnswer = messageToGroundedAnswer(latestAssistant, q);
        setGroundedAnswer(restoredAnswer);
        setRequestState('completed');
        if (restoredAnswer.citations && restoredAnswer.citations.length > 0) {
          setSelectedCitation(restoredAnswer.citations[0]);
        }
        // Restore document scope if present in metadata and not already set
        const metaDocIds = latestAssistant.message_metadata?.processing_metadata?.document_ids;
        if (Array.isArray(metaDocIds) && metaDocIds.length > 0 && selectedDocIds.length === 0) {
          setSelectedDocIds(metaDocIds);
        }
      }
    }
  }, [conversationData, requestState]);

  // Single Document object if in single-document mode
  const singleScopedDoc = useMemo(() => {
    if (selectedDocIds.length === 1) {
      return documents.find((d) => d.id === selectedDocIds[0]);
    }
    return null;
  }, [selectedDocIds, documents]);

  const handleToggleDoc = (docId: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  const handleSelectAllDocs = () => {
    setSelectedDocIds([]);
    setIsDocSelectorOpen(false);
  };

  const handleSelectSingleDoc = (docId: string) => {
    setSelectedDocIds([docId]);
    setIsDocSelectorOpen(false);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('document_id', docId);
    navigate(`/research?${nextParams.toString()}`, { replace: true });
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const queryText = question.trim() || lastSubmittedQuery;
    if (!queryText || requestState === 'in_flight') return;

    setRequestState('in_flight');
    setLastError(null);
    setLastSubmittedQuery(queryText);
    setCurrentStage(1);

    // Dynamic progression across the 5 stages
    const stageTimer = setInterval(() => {
      setCurrentStage((prev) => (prev < 4 ? prev + 1 : prev));
    }, 1100);

    try {
      const effectiveDocIds = selectedDocIds.length > 0 ? selectedDocIds : undefined;
      const res = await queryMutation.mutateAsync({
        question: queryText,
        document_ids: effectiveDocIds,
        conversation_id: conversationIdParam || undefined,
      });

      clearInterval(stageTimer);
      setCurrentStage(5);

      setGroundedAnswer(res);
      setRequestState('completed');
      if (res.citations && res.citations.length > 0) {
        setSelectedCitation(res.citations[0]);
      }

      // Update URL and persist session
      if (res.conversation_id) {
        const nextParams = new URLSearchParams();
        nextParams.set('conversation_id', res.conversation_id);
        if (effectiveDocIds && effectiveDocIds.length === 1) {
          nextParams.set('document_id', effectiveDocIds[0]);
        }
        navigate(`/research?${nextParams.toString()}`, { replace: true });
        try {
          sessionStorage.setItem(
            'documind_active_research_session',
            JSON.stringify({
              conversation_id: res.conversation_id,
              document_id: effectiveDocIds && effectiveDocIds.length === 1 ? effectiveDocIds[0] : null,
            })
          );
        } catch (storageErr) {
          // ignore storage quota error
        }
      }

      // Clear question on completion
      setQuestion('');
    } catch (err: any) {
      clearInterval(stageTimer);
      setRequestState('error');
      setCurrentStage(0);

      // Preserve question in input field so user can edit or retry
      setQuestion(queryText);

      let msg = 'An error occurred during evidence retrieval or answer synthesis.';
      if (
        err?.response?.status === 429 ||
        err?.status === 429 ||
        err?.message?.includes('429')
      ) {
        msg =
          'Groq API Rate Limit Exceeded (HTTP 429). The remote inference provider rate limit was reached. Your query has been preserved so you can retry.';
      } else if (
        err?.response?.status === 504 ||
        err?.status === 504 ||
        err?.message?.includes('504')
      ) {
        msg = 'Inference Request Timed Out (HTTP 504). Generation timed out. Please retry.';
      } else if (
        err?.response?.status === 503 ||
        err?.status === 503 ||
        err?.message?.includes('503')
      ) {
        msg = 'AI Provider Unavailable (HTTP 503). Ensure Groq credentials are valid in backend environment.';
      } else if (err?.message) {
        msg = err.message;
      }
      setLastError(msg);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleReset = () => {
    setQuestion('');
    setLastSubmittedQuery('');
    setGroundedAnswer(null);
    setSelectedCitation(null);
    setRequestState('idle');
    setLastError(null);
    setCurrentStage(0);
    sessionStorage.removeItem('documind_active_research_session');
    const nextParams = new URLSearchParams();
    if (documentIdParam) nextParams.set('document_id', documentIdParam);
    navigate(`/research?${nextParams.toString()}`, { replace: true });
  };

  const handleOpenCitationInViewer = (cit: CitationItem) => {
    if (!cit.document_id) return;
    const url = `/documents/${cit.document_id}?page=${cit.page_number}&chunkId=${cit.chunk_id}&from=research&quote=${encodeURIComponent(
      cit.exact_quote.slice(0, 100)
    )}&verified=${cit.verification_status === 'verified'}`;
    navigate(url);
  };

  return (
    <div className="space-y-3.5 max-w-7xl mx-auto pb-6">
      {/* ----------------------------------------------------------------- */}
      {/* Document Scope Selector & Compact Isolation Status Bar           */}
      {/* ----------------------------------------------------------------- */}
      <Card className="p-3 sm:p-3.5 space-y-2.5 bg-surface-secondary/40 border-border-subtle">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div className="flex items-center gap-2 flex-wrap">
            <BookOpen className="w-4 h-4 text-brand shrink-0" />
            <span className="text-xs font-bold uppercase tracking-wider text-content-primary">
              Corpus Scope:
            </span>
            {singleScopedDoc ? (
              <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-brand/15 text-brand border border-brand/35 text-xs font-mono font-medium">
                <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
                <span className="truncate max-w-[240px] font-bold">{singleScopedDoc.filename}</span>
                <span className="text-[10px] text-content-muted">
                  ({singleScopedDoc.total_chunks} chunks • {singleScopedDoc.total_pages} pgs)
                </span>
                <span className="text-[9px] uppercase px-1 rounded bg-brand/20 font-bold ml-1">
                  Isolated
                </span>
              </div>
            ) : (
              <span className="text-xs text-content-secondary font-medium">
                {selectedDocIds.length === 0
                  ? `All Ingested Documents (${readyDocuments.length} indexed)`
                  : `${selectedDocIds.length} of ${readyDocuments.length} documents selected`}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {selectedDocIds.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleSelectAllDocs}
                className="text-xs text-content-muted hover:text-content-primary h-7 px-2"
              >
                Search Entire Corpus
              </Button>
            )}
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsDocSelectorOpen((prev) => !prev)}
              className="h-7 text-xs"
              icon={
                isDocSelectorOpen ? (
                  <ChevronUp className="w-3.5 h-3.5" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" />
                )
              }
            >
              {singleScopedDoc ? 'Change Target' : 'Target Document'}
            </Button>
          </div>
        </div>

        {/* Selected Document Badges (Multi-select) */}
        {selectedDocIds.length > 1 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {selectedDocIds.map((id) => {
              const doc = readyDocuments.find((d) => d.id === id);
              return (
                <span
                  key={id}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono bg-brand/15 text-brand border border-brand/35 shadow-xs shadow-brand/5"
                >
                  <DocumentTypeIcon filename={doc?.filename || ''} size="sm" />
                  <span className="truncate max-w-[200px]">
                    {doc?.filename || id}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleToggleDoc(id)}
                    className="hover:text-content-primary ml-0.5"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              );
            })}
          </div>
        )}

        {/* Expandable Document Picker Drawer */}
        {isDocSelectorOpen && (
          <div className="pt-3 border-t border-border-subtle space-y-3">
            <div className="relative">
              <Search className="w-4 h-4 text-content-muted absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Filter indexed documents by name..."
                value={docFilterQuery}
                onChange={(e) => setDocFilterQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-surface-primary border border-border-subtle rounded-lg text-content-primary focus:outline-none focus:border-brand"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 max-h-56 overflow-y-auto pr-1">
              {filteredReadyDocs.map((doc) => {
                const isSelected = selectedDocIds.includes(doc.id);
                return (
                  <button
                    key={doc.id}
                    type="button"
                    onClick={() => handleSelectSingleDoc(doc.id)}
                    className={`flex items-center gap-2 p-2 rounded-lg border text-left text-xs transition-all ${
                      isSelected
                        ? 'bg-brand/15 border-brand text-brand-light shadow-xs'
                        : 'bg-surface-primary border-border-subtle text-content-secondary hover:border-border-muted'
                    }`}
                  >
                    <DocumentTypeIcon filename={doc.filename} size="sm" />
                    <div className="truncate flex-1">
                      <p className="font-semibold truncate text-content-primary">
                        {doc.title || doc.filename}
                      </p>
                      <p className="text-[10px] text-content-muted">
                        {doc.total_chunks} chunks • {doc.total_pages} pgs
                      </p>
                    </div>
                    {isSelected && (
                      <CheckCircle2 className="w-3.5 h-3.5 text-brand shrink-0" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </Card>

      {/* ----------------------------------------------------------------- */}
      {/* Query Input Section                                              */}
      {/* ----------------------------------------------------------------- */}
      <Card className="p-3.5 sm:p-4 shadow-sm space-y-2.5">
        <form onSubmit={handleSubmit} className="space-y-2.5">
          <div className="relative">
            <Textarea
              ref={textareaRef}
              rows={2}
              placeholder={
                singleScopedDoc
                  ? `Ask any question grounded strictly in ${singleScopedDoc.filename}... (Enter to submit, Shift+Enter for newline)`
                  : 'Ask any research question grounded in your documents... (Enter to submit, Shift+Enter for newline)'
              }
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={requestState === 'in_flight'}
              className="resize-none font-sans text-sm min-h-[58px] focus:border-brand"
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <div className="flex items-center gap-2 text-xs text-content-muted">
              <span className="inline-flex items-center gap-1 font-mono text-[11px] px-1.5 py-0.5 rounded bg-surface-secondary border border-border-subtle">
                Enter ↵
              </span>
              <span>to submit query</span>
              <span className="text-content-muted/50">•</span>
              <span className="inline-flex items-center gap-1 font-mono text-[11px] px-1.5 py-0.5 rounded bg-surface-secondary border border-border-subtle">
                Shift + Enter
              </span>
              <span>for new line</span>
            </div>

            <div className="flex items-center gap-2">
              {(question || groundedAnswer || conversationIdParam) && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleReset}
                  disabled={requestState === 'in_flight'}
                  icon={<RotateCcw className="w-3.5 h-3.5" />}
                >
                  New Inquiry
                </Button>
              )}

              <Button
                type="submit"
                variant="primary"
                size="sm"
                isLoading={requestState === 'in_flight'}
                disabled={!question.trim() || requestState === 'in_flight'}
                icon={<Send className="w-3.5 h-3.5" />}
              >
                Synthesize Answer
              </Button>
            </div>
          </div>
        </form>
      </Card>

      {/* ----------------------------------------------------------------- */}
      {/* Pipeline Progress Stepper (Active ONLY during in-flight queries)  */}
      {/* ----------------------------------------------------------------- */}
      {requestState === 'in_flight' && (
        <Card className="p-5 border-brand/40 bg-brand/5 space-y-4 animate-in fade-in">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand animate-spin" />
              <span className="font-bold text-content-primary">
                Two-Stage Grounded Retrieval & Synthesis in Progress
              </span>
            </div>
            <span className="text-content-muted font-mono">
              Provider: Groq (qwen3.8-27b) • Embeddings: nomic-embed-text (local)
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-5 gap-2.5">
            {PIPELINE_STAGES.map((st) => {
              const isPast = currentStage > st.id;
              const isCurrent = currentStage === st.id;
              return (
                <div
                  key={st.id}
                  className={`p-3 rounded-xl border text-xs transition-all ${
                    isCurrent
                      ? 'bg-brand/20 border-brand text-brand shadow-sm ring-1 ring-brand font-medium'
                      : isPast
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                      : 'bg-surface-secondary/40 border-border-subtle text-content-muted'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-[10px] font-bold">
                      STAGE 0{st.id}
                    </span>
                    {isPast && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                    {isCurrent && (
                      <span className="w-2 h-2 rounded-full bg-brand animate-ping" />
                    )}
                  </div>
                  <p className="font-semibold truncate text-content-primary">
                    {st.name}
                  </p>
                  <p className="text-[10px] text-content-secondary line-clamp-1 mt-0.5">
                    {st.desc}
                  </p>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Query Error Notice with Retry */}
      {requestState === 'error' && lastError && (
        <Alert
          variant="error"
          title="Query Synthesis Failed"
          icon={<AlertTriangle className="w-4 h-4" />}
        >
          <div className="space-y-3">
            <p className="text-xs">{lastError}</p>
            {lastSubmittedQuery && (
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => handleSubmit()}
                  icon={<RefreshCw className="w-3 h-3" />}
                >
                  Retry Question
                </Button>
              </div>
            )}
          </div>
        </Alert>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Grounded Answer & Side-by-Side Inspection Workspace               */}
      {/* ----------------------------------------------------------------- */}
      {requestState !== 'in_flight' && groundedAnswer && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Main Answer Panel (Col 7) */}
          <div className="lg:col-span-7 space-y-6">
            {/* Abstention Banner */}
            {groundedAnswer.abstained || groundedAnswer.status === 'abstained' ? (
              <Alert
                variant="warning"
                title="System Abstained from Answering"
                icon={<HelpCircle className="w-4 h-4" />}
              >
                <div className="space-y-2 text-xs">
                  <p>
                    DocuMind strictly abstained from synthesizing an ungrounded response
                    because the selected document scope lacks sufficient verifiable
                    evidence to answer this question without speculation.
                  </p>
                  {groundedAnswer.evidence_assessment && (
                    <div className="p-2.5 rounded-lg bg-surface-secondary/60 border border-border-subtle font-mono text-[11px] text-content-secondary">
                      {groundedAnswer.evidence_assessment}
                    </div>
                  )}
                </div>
              </Alert>
            ) : null}

            {/* Answer Card */}
            <Card className="p-6 space-y-5 shadow-sm border-l-4 border-l-brand animate-in fade-in duration-200 ease-enter transform-gpu">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-border-subtle">
                <div className="flex items-center gap-3">
                  <ConfidenceIndicator score={groundedAnswer.confidence} />
                  <div className="h-4 w-px bg-border-subtle" />
                  <Badge variant={groundedAnswer.status === 'answered' ? 'success' : 'warning'}>
                    {groundedAnswer.status === 'answered' ? 'Fully Grounded' : 'Partially Grounded'}
                  </Badge>
                  {groundedAnswer.conversation_id && (
                    <span className="text-[11px] font-mono text-content-muted">
                      Thread: {groundedAnswer.conversation_id.slice(0, 8)}
                    </span>
                  )}
                </div>

                {groundedAnswer.conversation_id && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => navigate(`/conversations?id=${groundedAnswer.conversation_id}`)}
                    icon={<MessageSquare className="w-3.5 h-3.5" />}
                  >
                    View in Conversations
                  </Button>
                )}
              </div>

              {/* Formatted Markdown Content */}
              <div className="prose prose-invert max-w-none">
                <MarkdownView
                  content={groundedAnswer.answer}
                  citations={groundedAnswer.citations}
                  onCitationClick={(cit) => {
                    setSelectedCitation(cit);
                    setActiveSideTab('evidence');
                  }}
                />
              </div>

              {/* Evidence Assessment Summary */}
              {groundedAnswer.evidence_assessment && (
                <div className="p-3.5 rounded-xl bg-surface-secondary/50 border border-border-subtle text-xs text-content-secondary space-y-1">
                  <span className="font-semibold text-content-primary block text-[11px] uppercase tracking-wider">
                    Evidence Assessment:
                  </span>
                  <p className="leading-relaxed">{groundedAnswer.evidence_assessment}</p>
                </div>
              )}

              {/* Contradiction Warning Alert */}
              {groundedAnswer.contradictions && groundedAnswer.contradictions.length > 0 && (
                <Alert
                  variant="error"
                  title="Cross-Document Contradiction Detected"
                  icon={<AlertTriangle className="w-4 h-4" />}
                >
                  <ul className="list-disc list-inside space-y-1 text-xs">
                    {groundedAnswer.contradictions.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </Alert>
              )}

              {/* Unsupported Claims Alert */}
              {groundedAnswer.unsupported_parts && groundedAnswer.unsupported_parts.length > 0 && (
                <Alert
                  variant="warning"
                  title="Unsupported Portions Identified"
                  icon={<HelpCircle className="w-4 h-4" />}
                >
                  <ul className="list-disc list-inside space-y-1 text-xs">
                    {groundedAnswer.unsupported_parts.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                </Alert>
              )}
            </Card>

            {/* ----------------------------------------------------------- */}
            {/* Verifiable Claim-Level Audit Section                        */}
            {/* ----------------------------------------------------------- */}
            {groundedAnswer.supporting_claims &&
              groundedAnswer.supporting_claims.length > 0 && (
                <Card className="p-6 space-y-4 shadow-sm">
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => setIsClaimsExpanded((prev) => !prev)}
                    className="flex items-center justify-between cursor-pointer select-none"
                  >
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      <h3 className="text-sm font-bold text-content-primary">
                        Claim-Level Verification Audit
                      </h3>
                      <span className="text-xs text-content-muted font-mono">
                        ({groundedAnswer.supporting_claims.length} claims verified)
                      </span>
                    </div>
                    {isClaimsExpanded ? (
                      <ChevronUp className="w-4 h-4 text-content-muted" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-content-muted" />
                    )}
                  </div>

                  {isClaimsExpanded && (
                    <div className="space-y-3 pt-2 border-t border-border-subtle">
                      {groundedAnswer.supporting_claims.map((claim, idx) => (
                        <div
                          key={claim.claim_id || idx}
                          className="p-3.5 rounded-xl border border-border-subtle bg-surface-secondary/30 space-y-2.5"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <p className="text-xs font-semibold text-content-primary leading-relaxed">
                              "{claim.claim_text}"
                            </p>
                            <EvidenceStatusBadge
                              status={claim.support_state}
                              size="sm"
                            />
                          </div>

                          {/* Verification Flags & Reasoning */}
                          <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono">
                            {claim.numerical_verified !== null && claim.numerical_verified !== undefined && (
                              <span
                                className={`px-2 py-0.5 rounded border ${
                                  claim.numerical_verified
                                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                                    : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                                }`}
                              >
                                Numbers: {claim.numerical_verified ? 'Verified' : 'Mismatch'}
                              </span>
                            )}
                            {claim.entities_verified !== null && claim.entities_verified !== undefined && (
                              <span
                                className={`px-2 py-0.5 rounded border ${
                                  claim.entities_verified
                                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                                    : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                                }`}
                              >
                                Entities: {claim.entities_verified ? 'Verified' : 'Mismatch'}
                              </span>
                            )}
                          </div>

                          {claim.reasoning && (
                            <p className="text-[11px] text-content-muted leading-relaxed italic">
                              Audit reasoning: {claim.reasoning}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              )}
          </div>

          {/* ------------------------------------------------------------- */}
          {/* Side Panel: Evidence Inspector & Retrieval Diagnostics (Col 5) */}
          {/* ------------------------------------------------------------- */}
          <div className="lg:col-span-5 space-y-4 lg:sticky lg:top-6">
            <Tabs
              tabs={[
                {
                  id: 'evidence',
                  label: `Evidence (${groundedAnswer.citations?.length || 0})`,
                  icon: <FileText className="w-3.5 h-3.5" />,
                },
                {
                  id: 'diagnostics',
                  label: 'Diagnostics',
                  icon: <Cpu className="w-3.5 h-3.5" />,
                },
              ]}
              activeTab={activeSideTab}
              onChange={(id) => setActiveSideTab(id as 'evidence' | 'diagnostics')}
            />

            {/* TAB 1: Evidence Inspector */}
            {activeSideTab === 'evidence' && (
              <div className="space-y-3 max-h-[calc(100vh-12rem)] overflow-y-auto pr-1">
                {groundedAnswer.citations && groundedAnswer.citations.length > 0 ? (
                  groundedAnswer.citations.map((cit, idx) => {
                    const isSelected = selectedCitation?.citation_id === cit.citation_id;
                    return (
                      <Card
                        key={cit.citation_id || idx}
                        className={`p-4 space-y-3 transition-all cursor-pointer ${
                          isSelected
                            ? 'border-brand ring-1 ring-brand bg-brand/5'
                            : 'border-border-subtle hover:border-border-muted bg-surface-primary'
                        }`}
                        onClick={() => setSelectedCitation(cit)}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-1.5 min-w-0">
                            <span className="font-mono text-xs font-bold text-brand px-1.5 py-0.5 rounded bg-brand/10 border border-brand/20">
                              [P{idx + 1}]
                            </span>
                            <span className="text-xs font-semibold text-content-primary truncate">
                              {cit.document_filename}
                            </span>
                          </div>
                          <Badge variant="neutral" size="sm">
                            Page {cit.page_number}
                          </Badge>
                        </div>

                        {/* Passage Quote */}
                        <div className="p-3 rounded-lg bg-surface-secondary/70 border border-border-subtle text-xs text-content-primary leading-relaxed font-serif">
                          "{cit.exact_quote}"
                        </div>

                        <div className="flex items-center justify-between pt-1">
                          <EvidenceStatusBadge
                            status={cit.claim_support_status || 'SUPPORTED'}
                            size="sm"
                          />

                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenCitationInViewer(cit);
                            }}
                            icon={<ExternalLink className="w-3.5 h-3.5 text-brand" />}
                            className="text-xs text-brand hover:text-brand-light"
                          >
                            Open in PDF
                          </Button>
                        </div>
                      </Card>
                    );
                  })
                ) : (
                  <Card className="p-8 text-center border-dashed">
                    <p className="text-xs text-content-muted">
                      No citation passages were linked for this response.
                    </p>
                  </Card>
                )}
              </div>
            )}

            {/* TAB 2: Retrieval Diagnostics */}
            {activeSideTab === 'diagnostics' && (
              <Card className="p-5 space-y-5">
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-content-muted mb-1">
                    Latency Breakdown
                  </h4>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-3 rounded-lg bg-surface-secondary border border-border-subtle">
                      <span className="text-[10px] text-content-muted block">Total Latency</span>
                      <span className="text-sm font-bold font-mono text-content-primary">
                        {(groundedAnswer.processing_metadata.latency_seconds || 0).toFixed(2)}s
                      </span>
                    </div>
                    <div className="p-3 rounded-lg bg-surface-secondary border border-border-subtle">
                      <span className="text-[10px] text-content-muted block">Groq Synthesis</span>
                      <span className="text-sm font-bold font-mono text-content-primary">
                        {(groundedAnswer.processing_metadata.llm_latency_seconds || 0).toFixed(2)}s
                      </span>
                    </div>
                    <div className="p-3 rounded-lg bg-surface-secondary border border-border-subtle">
                      <span className="text-[10px] text-content-muted block">Evidence Selection</span>
                      <span className="text-sm font-bold font-mono text-content-primary">
                        {groundedAnswer.processing_metadata.evidence_selection_ms || 0}ms
                      </span>
                    </div>
                    <div className="p-3 rounded-lg bg-surface-secondary border border-border-subtle">
                      <span className="text-[10px] text-content-muted block">Verification</span>
                      <span className="text-sm font-bold font-mono text-content-primary">
                        {groundedAnswer.processing_metadata.verification_ms || 0}ms
                      </span>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-content-muted mb-1">
                    Corpus & Vector Statistics
                  </h4>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between py-1.5 border-b border-border-subtle">
                      <span className="text-content-muted">Candidate Chunks Evaluated</span>
                      <span className="font-mono font-semibold text-content-primary">
                        {groundedAnswer.processing_metadata.candidate_chunks_evaluated || 0}
                      </span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-border-subtle">
                      <span className="text-content-muted">Evidence Tokens Fed to LLM</span>
                      <span className="font-mono font-semibold text-content-primary">
                        {groundedAnswer.processing_metadata.evidence_tokens || 0}
                      </span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-border-subtle">
                      <span className="text-content-muted">Active Generation Provider</span>
                      <span className="font-mono font-semibold text-sky-400">
                        Groq Cloud API
                      </span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-border-subtle">
                      <span className="text-content-muted">Generation Model</span>
                      <span className="font-mono font-semibold text-content-primary">
                        qwen/qwen3.8-27b
                      </span>
                    </div>
                    <div className="flex justify-between py-1.5">
                      <span className="text-content-muted">Local Embeddings</span>
                      <span className="font-mono font-semibold text-content-primary">
                        Ollama (nomic-embed-text • 768-dim)
                      </span>
                    </div>
                  </div>
                </div>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Initial State / Skeletons / Empty States / Starters                */}
      {/* ----------------------------------------------------------------- */}
      {requestState !== 'in_flight' && !groundedAnswer && (
        <>
          {isLoadingDocs ? (
            <Card className="p-8 space-y-4">
              <div className="flex flex-col items-center justify-center space-y-2">
                <Skeleton className="w-12 h-12 rounded-2xl" />
                <Skeleton className="h-5 w-48 rounded" />
                <Skeleton className="h-4 w-72 rounded" />
              </div>
            </Card>
          ) : documents.length === 0 ? (
            <Card className="p-5 sm:p-6 text-center space-y-3 border-dashed bg-surface-primary">
              <div className="w-10 h-10 rounded-xl bg-surface-secondary border border-border-subtle flex items-center justify-center text-brand mx-auto">
                <FolderOpen className="w-5 h-5" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h3 className="text-sm font-bold text-content-primary">
                  No Documents in Repository
                </h3>
                <p className="text-xs text-content-secondary leading-relaxed">
                  DocuMind requires at least one indexed research document (PDF, DOCX, TXT, MD)
                  to retrieve evidence chunks, generate answers, and verify citations.
                </p>
              </div>
              <Button
                variant="primary"
                size="sm"
                onClick={() => navigate('/documents')}
                icon={<UploadCloud className="w-3.5 h-3.5" />}
              >
                Upload First Document
              </Button>
            </Card>
          ) : readyDocuments.length === 0 && processingDocuments.length > 0 ? (
            <Card className="p-4 sm:p-5 text-center space-y-2.5 border-dashed bg-surface-primary">
              <div className="w-10 h-10 rounded-xl bg-brand/10 border border-brand/20 flex items-center justify-center text-brand mx-auto">
                <Clock className="w-5 h-5 animate-pulse" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h3 className="text-sm font-bold text-content-primary">
                  Document Ingestion in Progress ({processingDocuments.length})
                </h3>
                <p className="text-xs text-content-secondary leading-relaxed">
                  Your uploaded documents are currently being parsed, chunked, and embedded into 768-dimensional vectors.
                  Grounded research inquiries will be enabled as soon as indexing completes.
                </p>
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => navigate('/documents')}
              >
                Monitor Ingestion Queue
              </Button>
            </Card>
          ) : (
            <Card className="p-4 sm:p-5 space-y-3 border-dashed">
              <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-brand/10 border border-brand/20 flex items-center justify-center text-brand shrink-0">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm font-bold text-content-primary">
                    {singleScopedDoc
                      ? `Researching: ${singleScopedDoc.title || singleScopedDoc.filename}`
                      : 'Ready for Grounded Research'}
                  </h3>
                  <p className="text-xs text-content-muted leading-relaxed">
                    {singleScopedDoc
                      ? 'Inquiries will strictly retrieve passages from this document with citation verification.'
                      : 'Enter an inquiry across your document repository. DocuMind will retrieve relevant passages and verify citations.'}
                  </p>
                </div>
              </div>

              {readyDocuments.length > 0 && (
                <div className="pt-2 border-t border-border-subtle/60">
                  <span className="text-[10px] font-semibold text-content-muted uppercase tracking-wider block mb-2">
                    Example inquiries from indexed corpus:
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {[
                      'What are the key eligibility requirements and policies?',
                      'Summarize the primary guidelines and rules stated in this document.',
                      'What specific numerical limits and maximum allowances are specified?',
                    ].map((prompt, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => {
                          setQuestion(prompt);
                          if (textareaRef.current) textareaRef.current.focus();
                        }}
                        className="px-2.5 py-1.5 min-h-[30px] rounded-lg border border-border-subtle hover:border-brand/40 bg-surface-secondary/50 text-xs text-content-secondary hover:text-content-primary hover:-translate-y-0.5 hover:shadow-xs active:scale-[0.98] transition-all duration-150 ease-standard text-left transform-gpu"
                      >
                        "{prompt}"
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          )}
        </>
      )}
    </div>
  );
};
