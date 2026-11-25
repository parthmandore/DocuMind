/**
 * DocuMind Document Library & Repository Management (Phase 5.5)
 *
 * Professional document management workspace featuring:
 * - Real-time corpus statistics (Total, Ready, Processing, Failed)
 * - Multi-file drag-and-drop upload modal with client validation (PDF, DOCX, TXT, MD, <=50MB)
 * - Searchable, sortable, and status-filtered document table
 * - Document status lifecycle indicators and processing stage descriptions
 * - Re-indexing and cascade deletion dialogs
 * - Dedicated navigation to document inspection and PDF viewer
 */

import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  FileText,
  RotateCw,
  Trash2,
  ExternalLink,
  CheckCircle2,
  Clock,
  AlertCircle,
  FolderOpen,
  RefreshCw,
} from 'lucide-react';
import { useDocuments } from '@/hooks/useQueries';
import { useDeleteDocument, useReindexDocument } from '@/hooks/useMutations';
import {
  isDocumentActivelyProcessing,
  isDocumentWaitingForEmbeddings,
} from '@/hooks/useJobPolling';
import { formatFileSize } from '@/utils/file';
import { formatRelativeTime } from '@/utils/date';
import { formatError } from '@/utils/errors';
import { useToast } from '@/hooks/useToast';
import { useRouteMetadata } from '@/hooks/useRouteMetadata';
import type { DocumentResponse } from '@/types/api';

// UI Primitives
import {
  Button,
  Card,
  MetricCard,
  Badge,
  Skeleton,
  ErrorState,
  Alert,
  ConfirmDialog,
  SearchInput,
  Select,
} from '@/components/ui';

// Document Components
import {
  DocumentTypeIcon,
  DocumentStatusIndicator,
  IndexingProgressIndicator,
} from '@/components/document';
import { DocumentUploadModal } from '@/components/document/DocumentUploadModal';

type SortOption = 'newest' | 'oldest' | 'name_asc' | 'pages_desc' | 'chunks_desc' | 'size_desc';
type StatusFilter = 'all' | 'ready' | 'processing' | 'failed';

export const DocumentsPage: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();

  useRouteMetadata({
    title: 'Document Library | DocuMind',
    description:
      'Manage and inspect your research document repository with automated chunking and 768-dim vector embeddings.',
    isPrivate: true,
    canonicalPath: '/documents',
  });

  // Queries & Mutations
  const {
    data: documents = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useDocuments(0, 200, {
    refetchInterval: (query) => {
      const docs = query.state.data;
      return docs?.some((d) => isDocumentActivelyProcessing(d)) ? 2000 : false;
    },
  });

  const deleteMutation = useDeleteDocument();
  const reindexMutation = useReindexDocument();

  // Modal & Dialog States
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState<DocumentResponse | null>(null);
  const [reindexSuccessMsg, setReindexSuccessMsg] = useState<string | null>(null);

  // Search, Filter, Sort, Pagination
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [sortBy, setSortBy] = useState<SortOption>('newest');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 12;

  // ---------------------------------------------------------------------------
  // 1. Statistics Calculation (100% Real Backend Data)
  // ---------------------------------------------------------------------------
  const stats = useMemo(() => {
    const total = documents.length;
    const ready = documents.filter(
      (d) => d.status === 'COMPLETED' || d.status === 'INDEXED'
    ).length;
    const processing = documents.filter((d) => isDocumentActivelyProcessing(d)).length;
    const failed = documents.filter((d) => d.status === 'FAILED').length;

    return { total, ready, processing, failed };
  }, [documents]);

  // ---------------------------------------------------------------------------
  // 2. Filter & Sort Logic
  // ---------------------------------------------------------------------------
  const filteredAndSortedDocs = useMemo(() => {
    let result = [...documents];

    // Status Filter
    if (statusFilter === 'ready') {
      result = result.filter(
        (d) => d.status === 'COMPLETED' || d.status === 'INDEXED'
      );
    } else if (statusFilter === 'processing') {
      result = result.filter((d) => isDocumentActivelyProcessing(d));
    } else if (statusFilter === 'failed') {
      result = result.filter((d) => d.status === 'FAILED');
    }

    // Search Query (Filename or Title)
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (d) =>
          d.filename.toLowerCase().includes(q) ||
          d.title.toLowerCase().includes(q)
      );
    }

    // Sorting
    result.sort((a, b) => {
      switch (sortBy) {
        case 'oldest':
          return (
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          );
        case 'name_asc':
          return a.filename.localeCompare(b.filename);
        case 'pages_desc':
          return (b.total_pages || 0) - (a.total_pages || 0);
        case 'chunks_desc':
          return (b.total_chunks || 0) - (a.total_chunks || 0);
        case 'size_desc':
          return (b.file_size_bytes || 0) - (a.file_size_bytes || 0);
        case 'newest':
        default:
          return (
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          );
      }
    });

    return result;
  }, [documents, statusFilter, searchQuery, sortBy]);

  // Pagination
  const totalPages = Math.ceil(filteredAndSortedDocs.length / pageSize) || 1;
  const paginatedDocs = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredAndSortedDocs.slice(start, start + pageSize);
  }, [filteredAndSortedDocs, currentPage, pageSize]);

  // Actions
  const handleReindex = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const res = await reindexMutation.mutateAsync(docId);
      setReindexSuccessMsg(res.message);
      toast.info(res.message || 'Document re-indexing scheduled in background.', {
        title: 'Reindexing Scheduled',
      });
      setTimeout(() => setReindexSuccessMsg(null), 4000);
      refetch();
    } catch (err) {
      const errObj = formatError(err);
      toast.error(`Reindexing failed: ${errObj.message}`, { title: 'Reindexing Error' });
      console.error('Reindexing failed:', err);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!docToDelete) return;
    const docName = docToDelete.title || docToDelete.filename;
    try {
      await deleteMutation.mutateAsync(docToDelete.id);
      toast.success(`"${docName}" was permanently removed from repository.`, {
        title: 'Document Deleted',
      });
      setDocToDelete(null);
      refetch();
    } catch (err) {
      const errObj = formatError(err);
      toast.error(`Failed to delete "${docName}": ${errObj.message}`, {
        title: 'Deletion Failed',
      });
      console.error('Delete failed:', err);
    }
  };

  return (
    <div className="space-y-8 pb-12">
      {/* ----------------------------------------------------------------- */}
      {/* SECTION A: Page Header                                            */}
      {/* ----------------------------------------------------------------- */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-content-primary">
              Document Library
            </h1>
            {!isLoading && (
              <Badge variant="neutral" className="font-mono">
                {stats.total} {stats.total === 1 ? 'Doc' : 'Docs'}
              </Badge>
            )}
          </div>
          <p className="text-sm text-content-secondary mt-1">
            Manage your documents, monitor indexing, and explore your research sources.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Button
            variant="outline"
            size="md"
            onClick={() => refetch()}
            icon={<RefreshCw className="w-4 h-4" />}
            title="Refresh repository"
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            size="md"
            onClick={() => setIsUploadOpen(true)}
            icon={<UploadCloud className="w-4 h-4" />}
          >
            Upload Documents
          </Button>
        </div>
      </div>

      {/* Reindex Feedback Alert */}
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
      {/* SECTION B: Document Statistics                                    */}
      {/* ----------------------------------------------------------------- */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
        <MetricCard
          label="Total Documents"
          value={isLoading ? <Skeleton className="h-7 w-12" /> : stats.total}
          icon={<FileText className="w-4 h-4 text-brand" />}
          description="Stored in local repository"
        />

        <MetricCard
          label="Indexed & Ready"
          value={isLoading ? <Skeleton className="h-7 w-12" /> : stats.ready}
          icon={<CheckCircle2 className="w-4 h-4 text-emerald-500" />}
          badge={
            !isLoading && stats.total > 0 ? (
              <Badge variant={stats.ready === stats.total ? 'success' : 'warning'}>
                {Math.round((stats.ready / stats.total) * 100)}%
              </Badge>
            ) : undefined
          }
          description={
            isLoading
              ? undefined
              : `${stats.ready} of ${stats.total} ready for search`
          }
        />

        <MetricCard
          label="Currently Processing"
          value={
            isLoading ? (
              <Skeleton className="h-7 w-12" />
            ) : (
              stats.processing
            )
          }
          icon={<Clock className="w-4 h-4 text-indigo-400" />}
          badge={
            !isLoading ? (
              <Badge variant={stats.processing > 0 ? 'processing' : 'neutral'}>
                {stats.processing > 0 ? 'Active' : 'Idle'}
              </Badge>
            ) : undefined
          }
          description={
            stats.processing > 0
              ? 'Ingestion in progress'
              : 'Queue is idle'
          }
        />

        <MetricCard
          label="Failed Documents"
          value={isLoading ? <Skeleton className="h-7 w-12" /> : stats.failed}
          icon={<AlertCircle className="w-4 h-4 text-rose-500" />}
          badge={
            !isLoading && stats.failed > 0 ? (
              <Badge variant="error">Needs Attention</Badge>
            ) : undefined
          }
          description={
            stats.failed > 0
              ? `${stats.failed} failed extraction`
              : 'Zero pipeline errors'
          }
        />
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* SECTION C & D: Controls, Filters & Document Table                  */}
      {/* ----------------------------------------------------------------- */}
      <Card className="overflow-hidden border-border-subtle">
        {/* Filter and Search Bar */}
        <div className="p-4 border-b border-border-subtle bg-surface-primary flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Status Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
            <button
              onClick={() => {
                setStatusFilter('all');
                setCurrentPage(1);
              }}
              className={`px-3.5 py-2 min-h-[36px] rounded-lg text-xs font-semibold transition-all duration-120 ease-standard active:scale-[0.98] shrink-0 ${
                statusFilter === 'all'
                  ? 'bg-brand text-[#08090B] font-bold shadow-xs'
                  : 'text-content-secondary hover:bg-surface-hover hover:text-content-primary'
              }`}
            >
              All ({stats.total})
            </button>
            <button
              onClick={() => {
                setStatusFilter('ready');
                setCurrentPage(1);
              }}
              className={`px-3.5 py-2 min-h-[36px] rounded-lg text-xs font-semibold transition-all duration-120 ease-standard active:scale-[0.98] shrink-0 flex items-center gap-1.5 ${
                statusFilter === 'ready'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 font-bold'
                  : 'text-content-secondary hover:bg-surface-hover hover:text-content-primary'
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              Ready ({stats.ready})
            </button>
            <button
              onClick={() => {
                setStatusFilter('processing');
                setCurrentPage(1);
              }}
              className={`px-3.5 py-2 min-h-[36px] rounded-lg text-xs font-semibold transition-all duration-120 ease-standard active:scale-[0.98] shrink-0 flex items-center gap-1.5 ${
                statusFilter === 'processing'
                  ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/40 font-bold'
                  : 'text-content-secondary hover:bg-surface-hover hover:text-content-primary'
              }`}
            >
              <Clock className="w-3.5 h-3.5" />
              Processing ({stats.processing})
            </button>
            <button
              onClick={() => {
                setStatusFilter('failed');
                setCurrentPage(1);
              }}
              className={`px-3.5 py-2 min-h-[36px] rounded-lg text-xs font-semibold transition-all duration-120 ease-standard active:scale-[0.98] shrink-0 flex items-center gap-1.5 ${
                statusFilter === 'failed'
                  ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40 font-bold'
                  : 'text-content-secondary hover:bg-surface-hover hover:text-content-primary'
              }`}
            >
              <AlertCircle className="w-3.5 h-3.5" />
              Failed ({stats.failed})
            </button>
          </div>

          {/* Search & Sort Controls */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="w-full sm:w-64">
              <SearchInput
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(val) => {
                  setSearchQuery(val);
                  setCurrentPage(1);
                }}
                onClear={() => setSearchQuery('')}
              />
            </div>

            <Select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              options={[
                { value: 'newest', label: 'Date Added (Newest)' },
                { value: 'oldest', label: 'Date Added (Oldest)' },
                { value: 'name_asc', label: 'Filename (A-Z)' },
                { value: 'pages_desc', label: 'Pages (High to Low)' },
                { value: 'chunks_desc', label: 'Chunks (High to Low)' },
                { value: 'size_desc', label: 'Size (Largest first)' },
              ]}
              className="w-48 text-xs"
            />
          </div>
        </div>

        {/* --------------------------------------------------------------- */}
        {/* Document Table / Content List                                    */}
        {/* --------------------------------------------------------------- */}
        {isLoading ? (
          <div className="p-6 space-y-3">
            <Skeleton className="h-12 w-full rounded-lg" />
            <Skeleton className="h-12 w-full rounded-lg" />
            <Skeleton className="h-12 w-full rounded-lg" />
            <Skeleton className="h-12 w-full rounded-lg" />
          </div>
        ) : isError ? (
          <div className="p-8">
            <ErrorState
              title="Unable to load documents"
              message={formatError(error).message}
              onRetry={() => refetch()}
            />
          </div>
        ) : documents.length === 0 ? (
          <div className="p-12 text-center flex flex-col items-center justify-center">
            <div className="w-14 h-14 rounded-full bg-surface-secondary border border-border-subtle flex items-center justify-center text-brand mb-4">
              <FolderOpen className="w-7 h-7" />
            </div>
            <h3 className="text-base font-bold text-content-primary mb-1">
              Document repository is empty
            </h3>
            <p className="text-xs text-content-secondary max-w-sm mb-6 leading-relaxed">
              Upload PDF, DOCX, TXT, or Markdown documents to parse structure,
              generate semantic chunks, and start grounded research.
            </p>
            <Button
              variant="primary"
              size="md"
              onClick={() => setIsUploadOpen(true)}
              icon={<UploadCloud className="w-4 h-4" />}
            >
              Upload First Document
            </Button>
          </div>
        ) : filteredAndSortedDocs.length === 0 ? (
          <div className="p-12 text-center flex flex-col items-center justify-center text-xs">
            <p className="text-content-primary font-medium mb-1">
              No documents matched your criteria
            </p>
            <p className="text-content-muted mb-4">
              Try adjusting your search terms or clearing status filters.
            </p>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setSearchQuery('');
                setStatusFilter('all');
              }}
            >
              Reset Filters
            </Button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-border-subtle bg-surface-secondary/40 text-content-muted font-semibold uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-4">Document</th>
                  <th className="py-3 px-3">Type</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3 text-right">Pages</th>
                  <th className="py-3 px-3 text-right">Chunks</th>
                  <th className="py-3 px-3 text-right">Size</th>
                  <th className="py-3 px-3">Uploaded</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {paginatedDocs.map((doc) => (
                  <tr
                    key={doc.id}
                    onClick={() => navigate(`/documents/${doc.id}`)}
                    className="hover:bg-surface-secondary/60 transition-all duration-150 ease-standard cursor-pointer group select-none"
                  >
                    {/* Document Name & Title */}
                    <td className="py-3.5 px-4 min-w-[240px]">
                      <div className="flex items-center gap-3">
                        <DocumentTypeIcon filename={doc.filename} size="sm" />
                        <div className="min-w-0">
                          <p className="font-semibold text-content-primary truncate group-hover:text-brand transition-colors">
                            {doc.title || doc.filename}
                          </p>
                          <p className="text-[11px] text-content-muted font-mono truncate">
                            {doc.filename}
                          </p>
                        </div>
                      </div>
                    </td>

                    {/* MIME / File Type */}
                    <td className="py-3.5 px-3 whitespace-nowrap">
                      <span className="font-mono text-[11px] text-content-secondary uppercase">
                        {doc.filename.split('.').pop() || 'file'}
                      </span>
                    </td>

                    {/* Status & Processing Indicator */}
                    <td className="py-3.5 px-3 whitespace-nowrap">
                      <div className="space-y-1">
                        <DocumentStatusIndicator
                          status={doc.status}
                          errorMessage={doc.error_message}
                          size="sm"
                        />
                        {isDocumentActivelyProcessing(doc) && (
                          <div className="max-w-[160px]">
                            <IndexingProgressIndicator
                              status={doc.status}
                              embeddingProgress={doc.doc_metadata?.embedding_progress}
                            />
                          </div>
                        )}
                        {isDocumentWaitingForEmbeddings(doc) && (
                          <p className="text-[10px] text-amber-400 max-w-[180px] truncate" title={doc.error_message || undefined}>
                            Embeddings paused (click Reindex)
                          </p>
                        )}
                      </div>
                    </td>

                    {/* Pages */}
                    <td className="py-3.5 px-3 text-right font-mono text-content-secondary whitespace-nowrap">
                      {doc.total_pages || '--'}
                    </td>

                    {/* Chunks */}
                    <td className="py-3.5 px-3 text-right font-mono text-content-secondary whitespace-nowrap">
                      {doc.total_chunks || 0}
                    </td>

                    {/* File Size */}
                    <td className="py-3.5 px-3 text-right font-mono text-content-secondary whitespace-nowrap">
                      {formatFileSize(doc.file_size_bytes)}
                    </td>

                    {/* Uploaded Timestamp */}
                    <td className="py-3.5 px-3 whitespace-nowrap text-content-muted">
                      {formatRelativeTime(doc.created_at)}
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <div
                        className="flex items-center justify-end gap-1"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/documents/${doc.id}`)}
                          icon={<ExternalLink className="w-3.5 h-3.5" />}
                          title="Open document inspection"
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => handleReindex(doc.id, e)}
                          isLoading={reindexMutation.isPending}
                          icon={<RotateCw className="w-3.5 h-3.5" />}
                          title="Trigger reindexing"
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDocToDelete(doc)}
                          className="hover:text-status-error"
                          icon={<Trash2 className="w-3.5 h-3.5" />}
                          title="Delete document"
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="p-4 border-t border-border-subtle bg-surface-primary flex items-center justify-between text-xs">
                <span className="text-content-muted">
                  Showing {(currentPage - 1) * pageSize + 1} to{' '}
                  {Math.min(currentPage * pageSize, filteredAndSortedDocs.length)}{' '}
                  of {filteredAndSortedDocs.length} documents
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage <= 1}
                  >
                    Previous
                  </Button>
                  <span className="font-mono text-content-primary px-2">
                    {currentPage} / {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setCurrentPage((p) => Math.min(totalPages, p + 1))
                    }
                    disabled={currentPage >= totalPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* ----------------------------------------------------------------- */}
      {/* Upload Modal                                                      */}
      {/* ----------------------------------------------------------------- */}
      <DocumentUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onSuccess={() => refetch()}
      />

      {/* ----------------------------------------------------------------- */}
      {/* Cascade Delete Confirmation Dialog                                */}
      {/* ----------------------------------------------------------------- */}
      <ConfirmDialog
        isOpen={!!docToDelete}
        onClose={() => setDocToDelete(null)}
        onConfirm={handleDeleteConfirm}
        title="Delete Document"
        message={
          docToDelete
            ? `Are you sure you want to permanently delete "${docToDelete.filename}"? This removes the document file, its ${docToDelete.total_chunks} chunks, and all citations from the local database. This action cannot be undone.`
            : ''
        }
        confirmLabel="Delete Document"
        cancelLabel="Cancel"
        variant="danger"
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
};
