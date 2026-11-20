/**
 * DocuMind Dashboard & Workspace Overview
 *
 * Real-time workspace overview aggregating actual backend corpus metrics,
 * recent document ingestion activity, interactive research threads,
 * active processing pipeline tasks, and local engine diagnostics.
 */

import React, { useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  FileText,
  Sparkles,
  MessageSquare,
  ArrowRight,
  UploadCloud,
  Cpu,
  RefreshCw,
  FolderOpen,
  AlertTriangle,
  Compass,
  Database,
  Cloud,
} from 'lucide-react';
import { useDocuments, useConversations, useJobs } from '@/hooks/useQueries';
import { useConnectionStatus } from '@/hooks/useConnectionStatus';
import { useHealth } from '@/hooks/useHealth';
import { useRouteMetadata } from '@/hooks/useRouteMetadata';
import { isDocumentProcessing } from '@/hooks/useJobPolling';
import { getGreeting, formatRelativeTime } from '@/utils/date';
import { formatFileSize } from '@/utils/file';
import { storage } from '@/utils/storage';
import { formatError } from '@/utils/errors';
import { cn } from '@/utils/cn';

// UI Design System Primitives
import {
  Button,
  Card,
  Badge,
  Skeleton,
  ErrorState,
  Alert,
} from '@/components/ui';

// Document Components
import {
  DocumentTypeIcon,
  DocumentStatusIndicator,
  ProcessingStageLabel,
  IndexingProgressIndicator,
} from '@/components/document';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();

  useRouteMetadata({
    title: 'Dashboard | DocuMind',
    description:
      'DocuMind is a local-first AI document intelligence platform for verifiable research, hybrid vector retrieval, and automated citation verification.',
    isPrivate: false,
    canonicalPath: '/',
  });

  // Connection & Diagnostics
  const connection = useConnectionStatus();
  const { isGroqActive } = useHealth();

  // Core Data Queries
  const {
    data: documents = [],
    isLoading: isLoadingDocs,
    isError: isErrorDocs,
    error: docsError,
    refetch: refetchDocs,
  } = useDocuments(0, 100);

  const {
    data: conversations = [],
    isLoading: isLoadingConvs,
    isError: isErrorConvs,
    error: convsError,
    refetch: refetchConvs,
  } = useConversations(0, 50);

  const { refetch: refetchJobs } = useJobs(0, 20);

  // Derived Metrics & Calculations
  const greeting = useMemo(() => getGreeting(), []);

  const metrics = useMemo(() => {
    const total = documents.length;
    const indexed = documents.filter(
      (d) => d.status === 'COMPLETED' || d.status === 'INDEXED'
    ).length;
    const processing = documents.filter((d) => isDocumentProcessing(d.status));
    const totalChunks = documents.reduce(
      (acc, d) => acc + (d.total_chunks || 0),
      0
    );
    const totalConvs = conversations.length;

    return {
      total,
      indexed,
      processingCount: processing.length,
      processingDocs: processing,
      totalChunks,
      totalConvs,
      indexRatio: total > 0 ? Math.round((indexed / total) * 100) : 100,
    };
  }, [documents, conversations]);

  // Recent Documents (top 5, sorted by created_at descending)
  const recentDocuments = useMemo(() => {
    return [...documents]
      .sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )
      .slice(0, 5);
  }, [documents]);

  // Recent Conversations (top 5, sorted by updated_at descending)
  const recentConversations = useMemo(() => {
    return [...conversations]
      .sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )
      .slice(0, 5);
  }, [conversations]);

  // Active Processing Items (documents in active pipeline stages)
  const activeProcessingItems = useMemo(() => {
    return documents.filter((d) => isDocumentProcessing(d.status));
  }, [documents]);

  const handleOpenConversation = (convId: string) => {
    storage.setLastConversationId(convId);
    navigate('/conversations');
  };

  const handleRefreshAll = () => {
    refetchDocs();
    refetchConvs();
    refetchJobs();
    connection.checkConnection();
  };

  return (
    <div className="space-y-8 pb-12">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-border-subtle border-l-4 border-l-brand bg-surface-primary p-6 sm:p-8 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2 max-w-2xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-semibold tracking-wider text-brand uppercase bg-brand/10 border border-brand/20 px-2 py-0.5 rounded-md">
                {greeting}
              </span>
              <span className="text-content-muted text-xs">•</span>
              <span className="text-xs text-content-secondary font-medium">
                Research Workspace
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-content-primary">
              Document Intelligence & Research
            </h1>
            <p className="text-sm text-content-secondary leading-relaxed max-w-xl">
              An evidence-grounded research assistant powered by hybrid BM25 + dense retrieval, strict document isolation, and claim-level citation auditing.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0 flex-wrap">
            <Link to="/documents">
              <Button
                variant="primary"
                size="md"
                icon={<UploadCloud className="w-4 h-4" />}
                className="shadow-sm shadow-brand/20"
              >
                Add Documents
              </Button>
            </Link>
            <Link to="/research">
              <Button
                variant="secondary"
                size="md"
                icon={<Compass className="w-4 h-4 text-brand" />}
              >
                Start Research
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Backend Offline Warning Banner */}
      {!connection.isBackendOnline && (
        <Alert
          variant="error"
          title="Backend Disconnected"
          icon={<AlertTriangle className="w-5 h-5" />}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <span>
              Unable to reach local DocuMind service at http://127.0.0.1:8000.
              Corpus queries and live retrieval will resume once the service is started.
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefreshAll}
              icon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Retry Connection
            </Button>
          </div>
        </Alert>
      )}

      {/* Metrics Overview Grid */}
      <section aria-labelledby="stats-heading" className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <h2
            id="stats-heading"
            className="text-xs font-semibold tracking-wider text-content-muted uppercase"
          >
            Corpus Intelligence Overview
          </h2>
          <button
            onClick={handleRefreshAll}
            className="text-xs text-content-muted hover:text-content-primary flex items-center gap-1.5 transition-colors focus:outline-none"
            title="Refresh metrics"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Refresh</span>
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Main Knowledge Base Card */}
          <Card className="lg:col-span-2 p-6 flex flex-col justify-between space-y-5 bg-surface-primary border-border-subtle">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border-subtle/70 pb-4">
              <div>
                <span className="text-xs font-medium text-brand uppercase tracking-wider block">
                  Knowledge Base
                </span>
                <h3 className="text-lg font-semibold text-content-primary mt-0.5">
                  Ingested Document Corpus
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <Badge
                  variant={metrics.indexed === metrics.total && metrics.total > 0 ? 'success' : 'neutral'}
                  size="sm"
                >
                  {metrics.indexed === metrics.total && metrics.total > 0
                    ? 'Fully Indexed'
                    : metrics.processingCount > 0
                    ? `${metrics.processingCount} Processing`
                    : 'Corpus Ready'}
                </Badge>
                <Link to="/documents">
                  <Button variant="ghost" size="sm" icon={<ArrowRight className="w-3.5 h-3.5" />}>
                    Explore
                  </Button>
                </Link>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4 pt-1">
              <div>
                <p className="text-xs text-content-muted font-medium">Total Files</p>
                <div className="text-2xl sm:text-3xl font-bold text-content-primary tracking-tight mt-1">
                  {isLoadingDocs ? <Skeleton className="h-8 w-14" /> : metrics.total}
                </div>
                <p className="text-[11px] text-content-secondary mt-0.5">
                  {metrics.indexed} fully indexed
                </p>
              </div>

              <div>
                <p className="text-xs text-content-muted font-medium">Indexed Chunks</p>
                <div className="text-2xl sm:text-3xl font-bold text-content-primary tracking-tight mt-1">
                  {isLoadingDocs ? (
                    <Skeleton className="h-8 w-16" />
                  ) : (
                    metrics.totalChunks.toLocaleString()
                  )}
                </div>
                <p className="text-[11px] text-content-secondary mt-0.5">
                  768-dim embeddings
                </p>
              </div>

              <div>
                <p className="text-xs text-content-muted font-medium">Research Threads</p>
                <div className="text-2xl sm:text-3xl font-bold text-content-primary tracking-tight mt-1">
                  {isLoadingConvs ? <Skeleton className="h-8 w-12" /> : metrics.totalConvs}
                </div>
                <p className="text-[11px] text-content-secondary mt-0.5">
                  Active sessions
                </p>
              </div>
            </div>
          </Card>

          {/* Engine Status & Architecture Card */}
          <Card className="p-6 flex flex-col justify-between space-y-4 bg-surface-primary border-border-subtle">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-border-subtle/70">
                <span className="text-xs font-medium text-brand uppercase tracking-wider block">
                  AI Architecture
                </span>
                <span className="flex items-center gap-1.5 text-xs text-content-secondary">
                  <span
                    className={cn(
                      'w-2 h-2 rounded-full',
                      connection.isBackendOnline
                        ? isGroqActive
                          ? 'bg-brand'
                          : 'bg-status-success'
                        : 'bg-status-error'
                    )}
                  />
                  {isGroqActive ? 'Groq Active' : 'Ollama Active'}
                </span>
              </div>

              <div className="space-y-3 mt-4">
                <div className="flex items-start gap-2.5">
                  <Cpu className="w-4 h-4 text-brand shrink-0 mt-0.5" />
                  <div className="text-xs">
                    <p className="font-medium text-content-primary">Generation</p>
                    <p className="text-content-muted">
                      {isGroqActive
                        ? 'Groq Cloud • qwen/qwen3.8-27b'
                        : 'Ollama • Local Mistral/Qwen'}
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-2.5">
                  <Database className="w-4 h-4 text-brand shrink-0 mt-0.5" />
                  <div className="text-xs">
                    <p className="font-medium text-content-primary">Local Embeddings</p>
                    <p className="text-content-muted">
                      nomic-embed-text (768-dim) • SQLite WAL
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-2.5">
                  <Cloud className="w-4 h-4 text-brand shrink-0 mt-0.5" />
                  <div className="text-xs">
                    <p className="font-medium text-content-primary">Verification</p>
                    <p className="text-content-muted">
                      Local claim-level citation audit
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-border-subtle/70 flex justify-between items-center text-xs">
              <span className="text-content-muted">Provider Mode:</span>
              <span className="font-semibold text-content-primary">
                {isGroqActive ? 'Groq Generation' : 'Local Ollama'}
              </span>
            </div>
          </Card>
        </div>
      </section>

      {/* Active Document Processing Queue Section */}
      {activeProcessingItems.length > 0 && (
        <section aria-labelledby="active-queue-heading" className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-brand"></span>
              </span>
              <h2
                id="active-queue-heading"
                className="text-xs font-semibold tracking-wider text-content-muted uppercase"
              >
                Active Ingestion Pipeline ({activeProcessingItems.length})
              </h2>
            </div>
            <Link
              to="/documents"
              className="text-xs text-brand hover:underline font-medium"
            >
              Manage Ingestion Queue
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeProcessingItems.map((doc) => (
              <Card
                key={doc.id}
                className="p-4 space-y-3 bg-surface-primary border-border-subtle"
              >
                <div className="flex items-start gap-3">
                  <DocumentTypeIcon filename={doc.filename} mimeType={doc.mime_type} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-content-primary truncate">
                      {doc.filename}
                    </p>
                    <p className="text-xs text-content-muted">
                      Uploaded {formatRelativeTime(doc.created_at)}
                    </p>
                  </div>
                </div>
                <div className="space-y-1.5 pt-1">
                  <div className="flex items-center justify-between text-xs">
                    <ProcessingStageLabel status={doc.status} />
                    <span className="text-content-muted font-mono text-[11px]">
                      {doc.total_chunks || 0} chunks
                    </span>
                  </div>
                  <IndexingProgressIndicator status={doc.status} />
                </div>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* Two-Column Grid: Recent Documents & Recent Conversations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column: Recent Documents */}
        <section aria-labelledby="recent-docs-heading" className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h2
              id="recent-docs-heading"
              className="text-xs font-semibold tracking-wider text-content-muted uppercase flex items-center gap-2"
            >
              <FileText className="w-3.5 h-3.5 text-brand" />
              <span>Recent Documents</span>
            </h2>
            <Link
              to="/documents"
              className="text-xs text-brand hover:underline font-medium flex items-center gap-1"
            >
              <span>View all ({documents.length})</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {isLoadingDocs ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className="p-4 rounded-xl border border-border-subtle bg-surface-primary flex items-center gap-3"
                >
                  <Skeleton className="w-9 h-9 rounded-lg shrink-0" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/3" />
                  </div>
                </div>
              ))}
            </div>
          ) : isErrorDocs ? (
            <ErrorState
              title="Failed to load documents"
              message={formatError(docsError).message}
              onRetry={() => refetchDocs()}
            />
          ) : recentDocuments.length === 0 ? (
            <Card className="p-8 text-center flex flex-col items-center justify-center space-y-3 bg-surface-primary border-border-subtle">
              <FolderOpen className="w-10 h-10 text-content-muted/60" />
              <div className="space-y-1">
                <p className="text-sm font-semibold text-content-primary">
                  No documents in corpus
                </p>
                <p className="text-xs text-content-muted max-w-xs">
                  Upload PDF, DOCX, or TXT research papers to build your local retrieval corpus.
                </p>
              </div>
              <Link to="/documents">
                <Button variant="primary" size="sm" icon={<UploadCloud className="w-3.5 h-3.5" />}>
                  Upload First Document
                </Button>
              </Link>
            </Card>
          ) : (
            <div className="space-y-2.5">
              {recentDocuments.map((doc) => (
                <div
                  key={doc.id}
                  className="p-4 rounded-xl bg-surface-primary border border-border-subtle hover:border-brand/40 flex items-center justify-between gap-4 transition-all cursor-pointer group"
                  onClick={() => navigate(`/documents/${doc.id}`)}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <DocumentTypeIcon filename={doc.filename} mimeType={doc.mime_type} />
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-content-primary truncate group-hover:text-brand transition-colors">
                        {doc.filename}
                      </p>
                      <p className="text-xs text-content-muted mt-0.5">
                        {formatFileSize(doc.file_size_bytes)} • {doc.total_pages || 0} pages • {doc.total_chunks || 0} chunks • {formatRelativeTime(doc.created_at)}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <DocumentStatusIndicator status={doc.status} />
                    <ArrowRight className="w-4 h-4 text-content-muted group-hover:text-content-primary transition-colors hidden sm:block" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Right Column: Recent Research Conversations */}
        <section aria-labelledby="recent-convs-heading" className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h2
              id="recent-convs-heading"
              className="text-xs font-semibold tracking-wider text-content-muted uppercase flex items-center gap-2"
            >
              <MessageSquare className="w-3.5 h-3.5 text-brand" />
              <span>Research Conversations</span>
            </h2>
            <Link
              to="/conversations"
              className="text-xs text-brand hover:underline font-medium flex items-center gap-1"
            >
              <span>View all ({conversations.length})</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {isLoadingConvs ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className="p-4 rounded-xl border border-border-subtle bg-surface-primary flex items-center gap-3"
                >
                  <Skeleton className="w-9 h-9 rounded-lg shrink-0" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/3" />
                  </div>
                </div>
              ))}
            </div>
          ) : isErrorConvs ? (
            <ErrorState
              title="Failed to load conversations"
              message={formatError(convsError).message}
              onRetry={() => refetchConvs()}
            />
          ) : recentConversations.length === 0 ? (
            <Card className="p-8 text-center flex flex-col items-center justify-center space-y-3 bg-surface-primary border-border-subtle">
              <Sparkles className="w-10 h-10 text-content-muted/60" />
              <div className="space-y-1">
                <p className="text-sm font-semibold text-content-primary">
                  No research threads yet
                </p>
                <p className="text-xs text-content-muted max-w-xs">
                  Start an evidence-grounded research query against your documents.
                </p>
              </div>
              <Link to="/research">
                <Button variant="primary" size="sm" icon={<Sparkles className="w-3.5 h-3.5" />}>
                  Start First Research Query
                </Button>
              </Link>
            </Card>
          ) : (
            <div className="space-y-2.5">
              {recentConversations.map((conv) => (
                <div
                  key={conv.id}
                  className="p-4 rounded-xl bg-surface-primary border border-border-subtle hover:border-brand/40 flex items-center justify-between gap-4 transition-all cursor-pointer group"
                  onClick={() => handleOpenConversation(conv.id)}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-9 h-9 rounded-lg bg-brand/10 border border-brand/20 flex items-center justify-center text-brand shrink-0 group-hover:bg-brand/20 group-hover:border-brand/40 transition-colors">
                      <MessageSquare className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-content-primary truncate group-hover:text-brand transition-colors">
                        {conv.title || 'Untitled Research Inquiry'}
                      </p>
                      <p className="text-xs text-content-muted mt-0.5">
                        Updated {formatRelativeTime(conv.updated_at)}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <Button variant="ghost" size="sm" icon={<ArrowRight className="w-3.5 h-3.5" />}>
                      Open
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
};
