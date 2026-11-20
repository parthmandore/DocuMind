/**
 * Extracted Content & Section Inspector (Phase 5.5)
 *
 * Renders hierarchical document sections, headings, paragraphs, and tabular structures
 * retrieved from `/api/documents/{doc_id}/content`.
 */

import React, { useState, useMemo } from 'react';
import {
  Search,
  ListTree,
  ChevronRight,
  BookOpen,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { ErrorState } from '@/components/ui/ErrorState';
import { useDocumentContent } from '@/hooks/useQueries';
import { formatError } from '@/utils/errors';
import type { SectionSchema } from '@/types/api';

export interface ExtractedContentInspectorProps {
  documentId: string;
  className?: string;
}

export const ExtractedContentInspector: React.FC<
  ExtractedContentInspectorProps
> = ({ documentId, className = '' }) => {
  const {
    data: content,
    isLoading,
    isError,
    error,
    refetch,
  } = useDocumentContent(documentId);

  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(
    null
  );
  const [searchFilter, setSearchFilter] = useState<string>('');

  const sections = content?.sections || [];

  // Filter sections by search text
  const filteredSections = useMemo(() => {
    if (!searchFilter.trim()) return sections;
    const q = searchFilter.toLowerCase();
    return sections.filter(
      (s) =>
        s.title.toLowerCase().includes(q) || s.content.toLowerCase().includes(q)
    );
  }, [sections, searchFilter]);

  // Active section
  const activeSection: SectionSchema | undefined = useMemo(() => {
    if (selectedSectionId) {
      return sections.find((s) => s.id === selectedSectionId);
    }
    return sections[0];
  }, [sections, selectedSectionId]);

  if (isLoading) {
    return (
      <div className={`space-y-4 p-6 ${className}`}>
        <Skeleton className="h-8 w-64 rounded-lg" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Skeleton className="h-96 rounded-xl" />
          <Skeleton className="h-96 md:col-span-2 rounded-xl" />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className={`p-6 ${className}`}>
        <ErrorState
          title="Failed to Load Extracted Content"
          message={formatError(error).message}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  if (sections.length === 0) {
    return (
      <Card className={`p-8 text-center ${className}`}>
        <div className="flex flex-col items-center justify-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-surface-secondary flex items-center justify-center text-brand">
            <BookOpen className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-semibold text-content-primary">
            No Extracted Sections Found
          </h3>
          <p className="text-xs text-content-muted max-w-sm">
            This document may still be undergoing extraction or does not contain
            structured text sections.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <div
      className={`grid grid-cols-1 md:grid-cols-3 gap-6 h-[700px] border border-border-subtle rounded-xl bg-surface-primary overflow-hidden ${className}`}
    >
      {/* ----------------------------------------------------------------- */}
      {/* Left: Section Outline & Search                                    */}
      {/* ----------------------------------------------------------------- */}
      <div className="border-r border-border-subtle flex flex-col bg-surface-secondary/30 overflow-hidden">
        <div className="p-3.5 border-b border-border-subtle space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold text-content-secondary uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <ListTree className="w-3.5 h-3.5 text-brand" />
              Document Outline
            </span>
            <Badge variant="neutral">{sections.length}</Badge>
          </div>

          <div className="relative">
            <Search className="w-3.5 h-3.5 text-content-muted absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Filter sections..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-border-subtle bg-surface-primary text-xs text-content-primary placeholder:text-content-muted focus:outline-none focus:border-brand"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {filteredSections.map((sec) => {
            const isSelected = activeSection?.id === sec.id;
            const indentClass =
              sec.section_level === 2
                ? 'ml-3'
                : sec.section_level >= 3
                ? 'ml-6'
                : '';

            return (
              <button
                key={sec.id}
                onClick={() => setSelectedSectionId(sec.id)}
                className={`w-full text-left p-2.5 rounded-lg text-xs transition-all flex items-start gap-2 ${indentClass} ${
                  isSelected
                    ? 'bg-brand/10 text-brand border border-brand/30 font-medium'
                    : 'text-content-secondary hover:bg-surface-secondary hover:text-content-primary'
                }`}
              >
                <ChevronRight
                  className={`w-3.5 h-3.5 shrink-0 mt-0.5 transition-transform ${
                    isSelected ? 'rotate-90 text-brand' : 'text-content-muted'
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{sec.title}</p>
                  <p className="text-[10px] text-content-muted">
                    Page {sec.page_number} • Section #{sec.order_index + 1}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Right: Section Content View                                      */}
      {/* ----------------------------------------------------------------- */}
      <div className="md:col-span-2 flex flex-col overflow-hidden bg-surface-primary">
        {activeSection ? (
          <div className="flex flex-col h-full">
            <div className="p-4 border-b border-border-subtle bg-surface-secondary/20 flex items-center justify-between gap-4">
              <div className="min-w-0">
                <span className="text-[11px] font-semibold text-content-muted uppercase tracking-wider block">
                  Level {activeSection.section_level} Section
                </span>
                <h3 className="text-base font-bold text-content-primary truncate">
                  {activeSection.title}
                </h3>
              </div>
              <Badge variant="neutral">Page {activeSection.page_number}</Badge>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4 text-xs leading-relaxed text-content-secondary font-sans selection:bg-brand/20">
              {activeSection.content.split('\n\n').map((paragraph, idx) => (
                <p key={idx} className="leading-relaxed">
                  {paragraph}
                </p>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-xs text-content-muted">
            Select a section from the outline to inspect its extracted text.
          </div>
        )}
      </div>
    </div>
  );
};
