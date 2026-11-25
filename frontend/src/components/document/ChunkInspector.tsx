/**
 * Semantic Chunk & Embedding Inspector (Phase 5.5)
 *
 * Inspects all 768-dim semantic chunks, token counts, bounding boxes,
 * and vector indexing state from `/api/documents/{doc_id}/content`
 * and `/api/documents/{doc_id}/indexing-status`.
 */

import React, { useState, useMemo } from 'react';
import {
  Layers,
  Search,
  CheckCircle2,
  Clock,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Cpu,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { ErrorState } from '@/components/ui/ErrorState';
import { useDocumentContent, useIndexingStatus } from '@/hooks/useQueries';
import { formatError } from '@/utils/errors';
import { useToast } from '@/hooks/useToast';

export interface ChunkInspectorProps {
  documentId: string;
  docStatus?: string;
  errorMessage?: string | null;
  className?: string;
}

export const ChunkInspector: React.FC<ChunkInspectorProps> = ({
  documentId,
  docStatus,
  errorMessage,
  className = '',
}) => {
  const toast = useToast();
  const {
    data: content,
    isLoading: isLoadingContent,
    isError: isErrorContent,
    error: contentError,
    refetch: refetchContent,
  } = useDocumentContent(documentId);

  const { data: indexingStatus } = useIndexingStatus(documentId);

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPage, setSelectedPage] = useState<string>('all');
  const [expandedChunkId, setExpandedChunkId] = useState<string | null>(null);
  const [copiedChunkId, setCopiedChunkId] = useState<string | null>(null);

  const chunks = content?.chunks || [];

  // Available pages for filtering
  const availablePages = useMemo(() => {
    const pageSet = new Set<number>();
    chunks.forEach((c) => pageSet.add(c.page_number));
    return Array.from(pageSet).sort((a, b) => a - b);
  }, [chunks]);

  // Filtered chunks
  const filteredChunks = useMemo(() => {
    return chunks.filter((c) => {
      const matchesSearch =
        !searchTerm.trim() ||
        c.text.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesPage =
        selectedPage === 'all' || c.page_number === parseInt(selectedPage, 10);
      return matchesSearch && matchesPage;
    });
  }, [chunks, searchTerm, selectedPage]);

  const handleCopyText = async (id: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedChunkId(id);
      toast.success('Chunk text copied to clipboard.', { duration: 2500 });
      setTimeout(() => setCopiedChunkId(null), 2000);
    } catch {
      toast.error('Could not copy to clipboard.');
    }
  };

  if (isLoadingContent) {
    return (
      <div className={`space-y-4 p-6 ${className}`}>
        <Skeleton className="h-20 w-full rounded-xl" />
        <Skeleton className="h-40 w-full rounded-xl" />
        <Skeleton className="h-40 w-full rounded-xl" />
      </div>
    );
  }

  if (isErrorContent) {
    return (
      <div className={`p-6 ${className}`}>
        <ErrorState
          title="Failed to Load Document Chunks"
          message={formatError(contentError).message}
          onRetry={() => refetchContent()}
        />
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* ----------------------------------------------------------------- */}
      {/* Indexing Status Overview Header                                   */}
      {/* ----------------------------------------------------------------- */}
      <Card className="p-5 bg-surface-primary border-border-subtle">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand/10 border border-brand/20 flex items-center justify-center text-brand">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-content-primary">
                Semantic Vector Chunks ({chunks.length})
              </h3>
              <p className="text-xs text-content-muted">
                Extracted with sliding overlap and mapped to page bounding boxes
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap text-xs">
            {indexingStatus && (
              <>
                <div className="px-3 py-1.5 rounded-lg bg-surface-secondary border border-border-subtle flex items-center gap-2">
                  <Cpu className="w-3.5 h-3.5 text-brand" />
                  <span className="text-content-muted">Model:</span>
                  <span className="font-mono font-medium text-content-primary">
                    {indexingStatus.embedding_model || 'nomic-embed-text'}
                  </span>
                </div>

                <div className="px-3 py-1.5 rounded-lg bg-surface-secondary border border-border-subtle flex items-center gap-2">
                  <span className="text-content-muted">Dim:</span>
                  <span className="font-mono font-medium text-content-primary">
                    {indexingStatus.embedding_dimension || 768}
                  </span>
                </div>

                <Badge
                  variant={
                    indexingStatus.is_indexed
                      ? 'success'
                      : errorMessage || docStatus === 'FAILED'
                      ? 'warning'
                      : 'processing'
                  }
                >
                  {indexingStatus.is_indexed ? (
                    <>
                      <CheckCircle2 className="w-3 h-3 mr-1 inline" />
                      100% Embedded
                    </>
                  ) : errorMessage ? (
                    <>
                      <Clock className="w-3 h-3 mr-1 inline" />
                      Lexical Only ({indexingStatus.embedded_chunks}/{indexingStatus.total_chunks} Embedded)
                    </>
                  ) : (
                    <>
                      <Clock className="w-3 h-3 mr-1 inline" />
                      {indexingStatus.embedded_chunks} of{' '}
                      {indexingStatus.total_chunks} Embedded
                    </>
                  )}
                </Badge>
              </>
            )}
          </div>
        </div>
      </Card>

      {/* ----------------------------------------------------------------- */}
      {/* Filters: Search & Page Selector                                   */}
      {/* ----------------------------------------------------------------- */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-3.5 h-3.5 text-content-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            placeholder="Search chunk text..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-xl border border-border-subtle bg-surface-primary text-xs text-content-primary placeholder:text-content-muted focus:outline-none focus:border-brand"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <span className="text-xs text-content-muted shrink-0">Filter Page:</span>
          <select
            value={selectedPage}
            onChange={(e) => setSelectedPage(e.target.value)}
            className="py-1.5 px-3 rounded-lg border border-border-subtle bg-surface-primary text-xs text-content-primary focus:outline-none focus:border-brand"
          >
            <option value="all">All Pages ({chunks.length} chunks)</option>
            {availablePages.map((page) => (
              <option key={page} value={page}>
                Page {page}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Chunks List                                                       */}
      {/* ----------------------------------------------------------------- */}
      {filteredChunks.length === 0 ? (
        <Card className="p-8 text-center text-xs text-content-muted">
          No chunks match your search criteria.
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredChunks.map((chunk) => {
            const isExpanded = expandedChunkId === chunk.id;
            const isCopied = copiedChunkId === chunk.id;

            return (
              <Card
                key={chunk.id}
                className="p-4 border-border-subtle space-y-3 hover:border-border-muted transition-all"
              >
                <div className="flex items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono font-bold text-brand bg-brand/10 px-2 py-0.5 rounded text-[11px]">
                      Chunk #{chunk.chunk_index}
                    </span>
                    <Badge variant="neutral">Page {chunk.page_number}</Badge>
                    <span className="text-content-muted font-mono text-[11px]">
                      {chunk.token_count} tokens
                    </span>
                    {chunk.bboxes && chunk.bboxes.length > 0 && (
                      <span className="text-content-muted text-[11px]">
                        • {chunk.bboxes.length} bounding box(es)
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleCopyText(chunk.id, chunk.text)}
                      className="p-1 rounded text-content-muted hover:text-content-primary hover:bg-surface-secondary transition-colors"
                      title="Copy chunk text"
                    >
                      {isCopied ? (
                        <Check className="w-3.5 h-3.5 text-status-success" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                    {chunk.bboxes && chunk.bboxes.length > 0 && (
                      <button
                        onClick={() =>
                          setExpandedChunkId(isExpanded ? null : chunk.id)
                        }
                        className="p-1 rounded text-content-muted hover:text-content-primary hover:bg-surface-secondary transition-colors"
                        title={isExpanded ? 'Hide coordinates' : 'View coordinates'}
                      >
                        {isExpanded ? (
                          <ChevronUp className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5" />
                        )}
                      </button>
                    )}
                  </div>
                </div>

                {/* Chunk Text */}
                <p className="text-xs text-content-primary leading-relaxed bg-surface-secondary/40 p-3 rounded-lg border border-border-subtle font-mono selection:bg-brand/20 whitespace-pre-wrap">
                  {chunk.text}
                </p>

                {/* Expandable Bounding Box Coordinates */}
                {isExpanded && chunk.bboxes && (
                  <div className="pt-2 border-t border-border-subtle text-[11px] font-mono text-content-muted space-y-1">
                    <p className="font-sans font-semibold text-content-secondary uppercase text-[10px]">
                      Bounding Box Coordinates (x0, y0, x1, y1)
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                      {chunk.bboxes.map((box, bIdx) => (
                        <div
                          key={bIdx}
                          className="bg-surface-secondary/70 p-2 rounded border border-border-subtle"
                        >
                          <span>Box #{bIdx + 1}: </span>
                          <span className="text-content-primary">
                            [{box.x0.toFixed(1)}, {box.y0.toFixed(1)},{' '}
                            {box.x1.toFixed(1)}, {box.y1.toFixed(1)}]
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};
