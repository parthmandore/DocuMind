/**
 * Document Detail & Inspection Workspace (Phase 5.5)
 *
 * Dedicated inspection route `/documents/:documentId` providing:
 * - PDF.js reading interface with selectable text & citation highlighting
 * - Non-PDF structured text and outline inspector
 * - Semantic chunks and 768-dim vector embedding diagnostics
 * - Real-time processing progress with useJobPolling
 * - Re-indexing and cascade deletion workflows
 */

import React, { useState, useMemo, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  FileText,
  RotateCw,
  Trash2,
  Layers,
  BookOpen,
  Info,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
  Clock,
  ExternalLink,
  MessageSquare,
} from 'lucide-react';
import { useDocument, useDocumentContent, useConversations } from '@/hooks/useQueries';
import { useDeleteDocument, useReindexDocument } from '@/hooks/useMutations';
import {
  isDocumentActivelyProcessing,
  isDocumentWaitingForEmbeddings,
} from '@/hooks/useJobPolling';
import { formatFileSize } from '@/utils/file';
import { formatDate, formatRelativeTime } from '@/utils/date';
import { formatError } from '@/utils/errors';
import { useToast } from '@/hooks/useToast';
import { useRouteMetadata } from '@/hooks/useRouteMetadata';

// UI Primitives
import {
  Button,
  Card,
  Skeleton,
  ErrorState,
  Alert,
  ConfirmDialog,
  Tabs,
  Breadcrumb,
} from '@/components/ui';

// Document Components
import {
  DocumentTypeIcon,
  DocumentStatusIndicator,
  ProcessingStageLabel,
  IndexingProgressIndicator,
} from '@/components/document';
import {
  PdfViewer,
  CitationHighlightInfo,
} from '@/components/document/PdfViewer';
import { ExtractedContentInspector } from '@/components/document/ExtractedContentInspector';
import { ChunkInspector } from '@/components/document/ChunkInspector';

export const DocumentDetailPage: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const toast = useToast();

  // Queries & Mutations
  const {
    data: document,
    isLoading: isLoadingDoc,
    isError: isErrorDoc,
    error: docError,
    refetch: refetchDoc,
  } = useDocument(documentId, {
    refetchInterval: (query) => {
      return isDocumentActivelyProcessing(query.state.data) ? 2500 : false;
    },
  });

  useRouteMetadata({
    title: 'Document Inspection | DocuMind',
    dynamicEntityTitle: document?.title || document?.filename,
    isPrivate: true,
    breadcrumbs: [
      { label: 'Document Library', to: '/documents' },
      { label: document?.title || document?.filename || 'Document Inspection' },
    ],
  });

  const { data: docContent } = useDocumentContent(documentId);
  const { data: conversations } = useConversations(0, 50);

  const deleteMutation = useDeleteDocument();
  const reindexMutation = useReindexDocument();

  // Dialog State
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [reindexSuccessMsg, setReindexSuccessMsg] = useState<string | null>(
    null
  );

  // Active Tab
  const [activeTab, setActiveTab] = useState<string>('viewer');

  // Background Job Processing check
  const isProcessing = isDocumentActivelyProcessing(document);
  const isWaitingForEmbeddings = isDocumentWaitingForEmbeddings(document);

  const isPdf = useMemo(() => {
    if (!document) return false;
    return (
      document.mime_type === 'application/pdf' ||
      document.filename.toLowerCase().endsWith('.pdf')
    );
  }, [document]);

  // Match chunk if chunkId is present in URL
  const chunkIdParam = searchParams.get('chunkId');
  const matchedChunk = useMemo(() => {
    if (!chunkIdParam || !docContent?.chunks) return null;
    return docContent.chunks.find(
      (c) => c.id === chunkIdParam || String(c.chunk_index) === chunkIdParam
    );
  }, [chunkIdParam, docContent]);

  // Read citation params from URL query string if provided
  const citationInfo: CitationHighlightInfo | null = useMemo(() => {
    const pageStr = searchParams.get('page');
    let page = pageStr ? parseInt(pageStr, 10) : NaN;
    if (isNaN(page) && matchedChunk) {
      page = matchedChunk.page_number;
    }
    if (isNaN(page) || page <= 0) return null;

    let quote = searchParams.get('quote') || undefined;
    if (!quote && matchedChunk) {
      quote = matchedChunk.text.slice(0, 180);
    }

    const isVerifiedStr = searchParams.get('verified');
    const isVerified = isVerifiedStr !== null ? isVerifiedStr === 'true' : true;

    const x0 = searchParams.get('x0');
    const y0 = searchParams.get('y0');
    const x1 = searchParams.get('x1');
    const y1 = searchParams.get('y1');

    let bbox =
      x0 !== null && y0 !== null && x1 !== null && y1 !== null
        ? {
            x0: parseFloat(x0),
            y0: parseFloat(y0),
            x1: parseFloat(x1),
            y1: parseFloat(y1),
            page,
          }
        : null;

    if (!bbox && matchedChunk && matchedChunk.bboxes && matchedChunk.bboxes.length > 0) {
      const b = matchedChunk.bboxes[0];
      bbox = {
        x0: b.x0,
        y0: b.y0,
        x1: b.x1,
        y1: b.y1,
        page: b.page || page,
      };
    }

    return {
      pageNumber: page,
      quote,
      isVerified,
      bbox,
    };
  }, [searchParams, matchedChunk]);

  const fromParam = searchParams.get('from');

  const handleDismissCitation = () => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('page');
    nextParams.delete('quote');
    nextParams.delete('verified');
    nextParams.delete('x0');
    nextParams.delete('y0');
    nextParams.delete('x1');
    nextParams.delete('y1');
    nextParams.delete('chunkId');
    setSearchParams(nextParams);
  };

  const handleReindex = async () => {
    if (!documentId) return;
    try {
      const res = await reindexMutation.mutateAsync(documentId);
      setReindexSuccessMsg(res.message);
      toast.info(res.message || 'Re-indexing job queued in background.', {
        title: 'Reindexing Scheduled',
      });
      setTimeout(() => setReindexSuccessMsg(null), 4000);
      refetchDoc();
    } catch (err) {
      const errObj = formatError(err);
      toast.error(`Reindexing failed: ${errObj.message}`, { title: 'Reindexing Error' });
      console.error('Reindexing failed:', err);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!documentId) return;
    const docName = document?.title || document?.filename || 'Document';
    try {
      await deleteMutation.mutateAsync(documentId);
      toast.success(`"${docName}" was permanently removed.`, {
        title: 'Document Deleted',
      });
      navigate('/documents');
    } catch (err) {
      const errObj = formatError(err);
      toast.error(`Failed to delete "${docName}": ${errObj.message}`, {
        title: 'Deletion Failed',
      });
      console.error('Deletion failed:', err);
    }
  };

  // Define tab navigation based on document type
  const tabItems = useMemo(() => {
    const baseTabs = isPdf
      ? [
          {
            id: 'viewer',
            label: 'PDF Viewer',
            icon: <BookOpen className="w-4 h-4" />,
          },
          {
            id: 'chunks',
            label: `Chunks (${document?.total_chunks || 0})`,
            icon: <Layers className="w-4 h-4" />,
          },
          {
            id: 'outline',
            label: `Sections (${document?.total_sections || 0})`,
            icon: <FileText className="w-4 h-4" />,
          },
          {
            id: 'metadata',
            label: 'Metadata & Quality',
            icon: <Info className="w-4 h-4" />,
          },
        ]
      : [
          {
            id: 'outline',
            label: 'Extracted Content',
            icon: <BookOpen className="w-4 h-4" />,
          },
          {
            id: 'chunks',
            label: `Chunks (${document?.total_chunks || 0})`,
            icon: <Layers className="w-4 h-4" />,
          },
          {
            id: 'metadata',
            label: 'Metadata & Quality',
            icon: <Info className="w-4 h-4" />,
          },
        ];

    return [
      ...baseTabs,
      {
        id: 'history',
        label: 'Research History',
        icon: <Clock className="w-4 h-4" />,
      },
    ];
  }, [isPdf, document]);

  // Ensure default tab is appropriate if not PDF
  useEffect(() => {
    if (!isPdf && activeTab === 'viewer') {
      setActiveTab('outline');
    }
  }, [isPdf, activeTab]);

  if (isLoadingDoc) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto pb-12">
        <Skeleton className="h-6 w-32 rounded-lg" />
        <Skeleton className="h-16 w-full rounded-2xl" />
        <div className="grid grid-cols-4 gap-4">
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
        </div>
        <Skeleton className="h-[600px] rounded-2xl" />
      </div>
    );
  }

  if (isErrorDoc || !document) {
    return (
      <div className="max-w-2xl mx-auto py-12">
        <ErrorState
          title="Document Not Found"
          message={
            docError
              ? formatError(docError).message
              : `Document "${documentId}" could not be found in the local repository.`
          }
          onRetry={() => navigate('/documents')}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* ----------------------------------------------------------------- */}
      {/* Top Breadcrumb & Action Header                                    */}
      {/* ----------------------------------------------------------------- */}
      <Breadcrumb
        items={[
          { label: 'Document Library', to: '/documents' },
          { label: document.title || document.filename },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/documents')}
            icon={<ArrowLeft className="w-4 h-4" />}
          >
            Library
          </Button>
          <div className="h-4 w-px bg-border-subtle" />
          <div className="flex items-center gap-2.5 truncate">
            <DocumentTypeIcon filename={document.filename} size="md" />
            <div className="truncate">
              <h1 className="text-lg sm:text-xl font-bold tracking-tight text-content-primary truncate">
                {document.title || document.filename}
              </h1>
              <p className="text-xs text-content-muted font-mono truncate">
                {document.filename}
              </p>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2.5 shrink-0">
          <Button
            variant="primary"
            size="sm"
            onClick={() => navigate(`/research?docId=${document.id}`)}
            icon={<Sparkles className="w-3.5 h-3.5" />}
          >
            Research This Doc
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={handleReindex}
            isLoading={reindexMutation.isPending}
            icon={<RotateCw className="w-3.5 h-3.5" />}
          >
            Reindex
          </Button>

          <Button
            variant="danger"
            size="sm"
            onClick={() => setIsDeleteOpen(true)}
            icon={<Trash2 className="w-3.5 h-3.5" />}
          >
            Delete
          </Button>
        </div>
      </div>

      {/* Citation Return Banner when navigated from Research or Conversations */}
      {fromParam && (
        <div className="flex items-center justify-between p-3.5 rounded-xl border border-brand/40 bg-brand/10 text-brand-light">
          <div className="flex items-center gap-2.5 text-xs">
            <Sparkles className="w-4 h-4 text-brand shrink-0" />
            <span>
              Navigated from <strong>{fromParam === 'research' ? 'Research Workspace' : 'Conversation Thread'}</strong> citing this document.
              {citationInfo?.pageNumber && ` (Jumped to Page ${citationInfo.pageNumber})`}
            </span>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              if (fromParam === 'research') navigate('/research');
              else if (fromParam === 'conversations') navigate('/conversations');
              else navigate(-1);
            }}
            icon={<ArrowLeft className="w-3.5 h-3.5" />}
          >
            Return to {fromParam === 'research' ? 'Research' : 'Conversation'}
          </Button>
        </div>
      )}

      {/* Reindex Feedback Banner */}
      {reindexSuccessMsg && (
        <Alert
          variant="success"
          title="Reindexing Scheduled"
          icon={<CheckCircle2 className="w-4 h-4" />}
        >
          {reindexSuccessMsg}
        </Alert>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Active Processing Ingestion Pipeline Banner                      */}
      {/* ----------------------------------------------------------------- */}
      {isProcessing && (
        <Card className="p-4 border-brand/40 bg-brand/5 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-brand animate-pulse" />
              <span className="font-semibold text-content-primary">
                Ingestion Pipeline Active
              </span>
              <span className="text-content-muted">•</span>
              <ProcessingStageLabel
                status={document.status}
                errorMessage={document.error_message}
              />
            </div>
            <DocumentStatusIndicator
              status={document.status}
              errorMessage={document.error_message}
              size="sm"
            />
          </div>
          <IndexingProgressIndicator
            status={document.status}
            embeddingProgress={document.doc_metadata?.embedding_progress}
          />
        </Card>
      )}

      {/* Paused / Failed Ingestion Banner */}
      {!isProcessing && document.error_message && (
        <Alert
          variant={isWaitingForEmbeddings ? 'warning' : 'error'}
          title={
            isWaitingForEmbeddings
              ? 'Semantic Embeddings Paused — Lexical Search Ready'
              : 'Ingestion Pipeline Failed'
          }
          icon={<AlertTriangle className="w-4 h-4" />}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-2 flex-1">
              <p className="text-xs leading-relaxed">{document.error_message}</p>
              {isWaitingForEmbeddings && (
                <IndexingProgressIndicator
                  status={document.status}
                  isPaused
                  embeddingProgress={document.doc_metadata?.embedding_progress}
                />
              )}
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleReindex}
              isLoading={reindexMutation.isPending}
              icon={<RotateCw className="w-3.5 h-3.5" />}
              className="shrink-0"
            >
              {isWaitingForEmbeddings ? 'Retry Embeddings' : 'Retry Indexing'}
            </Button>
          </div>
        </Alert>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Document Overview Metadata Cards                                 */}
      {/* ----------------------------------------------------------------- */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
        <Card className="p-4 space-y-1">
          <span className="text-[11px] font-semibold text-content-muted uppercase tracking-wider block">
            Format & Size
          </span>
          <p className="text-base font-bold text-content-primary">
            {formatFileSize(document.file_size_bytes)}
          </p>
          <p className="text-[11px] text-content-secondary font-mono truncate">
            {document.mime_type}
          </p>
        </Card>

        <Card className="p-4 space-y-1">
          <span className="text-[11px] font-semibold text-content-muted uppercase tracking-wider block">
            Document Scope
          </span>
          <p className="text-base font-bold text-content-primary">
            {document.total_pages} {document.total_pages === 1 ? 'Page' : 'Pages'}
          </p>
          <p className="text-[11px] text-content-secondary">
            {document.total_words.toLocaleString()} words extracted
          </p>
        </Card>

        <Card className="p-4 space-y-1">
          <span className="text-[11px] font-semibold text-content-muted uppercase tracking-wider block">
            Semantic Vector Chunks
          </span>
          <p className="text-base font-bold text-content-primary">
            {document.total_chunks} Chunks
          </p>
          <p className="text-[11px] text-content-secondary">
            {document.total_sections} structural sections
          </p>
        </Card>

        <Card className="p-4 space-y-1">
          <span className="text-[11px] font-semibold text-content-muted uppercase tracking-wider block">
            Ingestion Status
          </span>
          <div className="pt-0.5">
            <DocumentStatusIndicator
              status={document.status}
              errorMessage={document.error_message}
              size="sm"
            />
          </div>
          <p className="text-[11px] text-content-muted">
            Uploaded {formatRelativeTime(document.created_at)}
          </p>
        </Card>
      </div>

      {/* Quality Warnings if present */}
      {document.quality_warnings && document.quality_warnings.length > 0 && (
        <Alert
          variant="warning"
          title="Document Quality Warnings"
          icon={<AlertTriangle className="w-4 h-4" />}
        >
          <ul className="list-disc list-inside space-y-1 text-xs">
            {document.quality_warnings.map((warn, i) => (
              <li key={i}>{warn}</li>
            ))}
          </ul>
        </Alert>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Inspection Views & Navigation Tabs                               */}
      {/* ----------------------------------------------------------------- */}
      <Tabs
        tabs={tabItems}
        activeTab={activeTab}
        onChange={(id) => setActiveTab(id)}
      />

      <div className="pt-2">
        {/* TAB 1: PDF Viewer (if PDF) */}
        {isPdf && activeTab === 'viewer' && (
          <div className="h-[800px]">
            <PdfViewer
              documentId={document.id}
              documentTitle={document.filename}
              activeCitation={citationInfo}
              onDismissCitation={handleDismissCitation}
            />
          </div>
        )}

        {/* TAB 2: Chunks Inspector */}
        {activeTab === 'chunks' && (
          <ChunkInspector
            documentId={document.id}
            docStatus={document.status}
            errorMessage={document.error_message}
          />
        )}

        {/* TAB 3: Extracted Content / Outline */}
        {activeTab === 'outline' && (
          <ExtractedContentInspector documentId={document.id} />
        )}

        {/* TAB 4: Technical Metadata & Audit */}
        {activeTab === 'metadata' && (
          <Card className="p-6 space-y-6">
            <div>
              <h3 className="text-sm font-bold text-content-primary mb-1">
                Technical Metadata & Integrity
              </h3>
              <p className="text-xs text-content-muted">
                Cryptographic hash, file attributes, and system audit logs
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
              <div className="p-3.5 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
                <span className="text-[11px] font-sans font-semibold text-content-muted uppercase">
                  SHA-256 Digest
                </span>
                <p className="text-content-primary break-all select-all">
                  {document.file_hash}
                </p>
              </div>

              <div className="p-3.5 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
                <span className="text-[11px] font-sans font-semibold text-content-muted uppercase">
                  Document ID (UUID)
                </span>
                <p className="text-content-primary select-all">{document.id}</p>
              </div>

              <div className="p-3.5 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
                <span className="text-[11px] font-sans font-semibold text-content-muted uppercase">
                  Created At
                </span>
                <p className="text-content-primary">
                  {formatDate(document.created_at)} ({document.created_at})
                </p>
              </div>

              <div className="p-3.5 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
                <span className="text-[11px] font-sans font-semibold text-content-muted uppercase">
                  Updated At
                </span>
                <p className="text-content-primary">
                  {formatDate(document.updated_at)} ({document.updated_at})
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* TAB 5: Research History */}
        {activeTab === 'history' && (
          <Card className="p-6 space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-content-primary mb-1">
                  Research History & Threads
                </h3>
                <p className="text-xs text-content-muted">
                  Past multi-turn conversations and grounded queries referencing this document
                </p>
              </div>
              <Button
                variant="primary"
                size="sm"
                onClick={() => navigate(`/research?docId=${document.id}`)}
                icon={<Sparkles className="w-3.5 h-3.5" />}
              >
                New Research Query
              </Button>
            </div>

            {conversations && conversations.length > 0 ? (
              <div className="space-y-3">
                {conversations.map((c) => (
                  <div
                    key={c.id}
                    className="p-4 rounded-xl border border-border-subtle hover:border-brand/40 bg-surface-secondary/50 hover:bg-surface-secondary transition-all flex items-center justify-between gap-4"
                  >
                    <div className="min-w-0 flex items-center gap-3">
                      <div className="w-9 h-9 rounded-lg bg-brand/10 border border-brand/20 flex items-center justify-center text-brand shrink-0">
                        <MessageSquare className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-content-primary truncate">
                          {c.title}
                        </p>
                        <p className="text-xs text-content-muted flex items-center gap-1.5 mt-0.5">
                          <Clock className="w-3 h-3" />
                          <span>Last active {formatRelativeTime(c.updated_at)}</span>
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate(`/conversations?id=${c.id}`)}
                      icon={<ExternalLink className="w-3.5 h-3.5" />}
                    >
                      Open Thread
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 px-4 border border-dashed border-border-subtle rounded-xl">
                <MessageSquare className="w-8 h-8 text-content-muted mx-auto mb-2 opacity-50" />
                <p className="text-sm font-semibold text-content-secondary mb-1">
                  No Conversation Threads Yet
                </p>
                <p className="text-xs text-content-muted max-w-sm mx-auto mb-4">
                  Start an interactive grounded research session on this document to synthesize claims and extract verifiable citations.
                </p>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => navigate(`/research?docId=${document.id}`)}
                  icon={<Sparkles className="w-3.5 h-3.5" />}
                >
                  Start Research
                </Button>
              </div>
            )}
          </Card>
        )}
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Cascade Delete Confirmation Dialog                                */}
      {/* ----------------------------------------------------------------- */}
      <ConfirmDialog
        isOpen={isDeleteOpen}
        onClose={() => setIsDeleteOpen(false)}
        onConfirm={handleDeleteConfirm}
        title="Delete Document"
        message={`Are you sure you want to permanently delete "${document.filename}"? This will remove the document file, its ${document.total_chunks} vector chunks, all extracted sections, and associated citations from the local repository. This action cannot be undone.`}
        confirmLabel="Delete Document"
        cancelLabel="Keep Document"
        variant="danger"
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
};
