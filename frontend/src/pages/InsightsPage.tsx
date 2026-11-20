/**
 * Citation Analytics & Corpus Insights (Phase 5.9)
 *
 * Real-time analytics computed from persisted SQLite records:
 * - Corpus overview: documents, indexed vector chunks, and total queries
 * - Citation verification rate and claim support distribution
 * - Document-level citation density rankings with deep links
 * - Contradiction & conflict monitoring logs
 * - 14-day temporal activity histogram
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ExternalLink,
  RotateCw,
} from 'lucide-react';

import { useInsights } from '@/hooks/useQueries';
import { useRouteMetadata } from '@/hooks/useRouteMetadata';
import { formatRelativeTime } from '@/utils/date';

// UI Primitives
import {
  Button,
  Card,
  Badge,
  Skeleton,
  Alert,
  PageHeader,
} from '@/components/ui';

// Document Components
import { DocumentTypeIcon, EvidenceStatusBadge } from '@/components/document';

export const InsightsPage: React.FC = () => {
  const navigate = useNavigate();

  useRouteMetadata({
    title: 'Citation Analytics | DocuMind',
    description:
      'Corpus-wide grounding verification rates, citation frequency rankings, and contradiction monitoring logs.',
    isPrivate: true,
    canonicalPath: '/insights',
    breadcrumbs: [{ label: 'Citation Analytics' }],
  });

  const { data: insights, isLoading, isError, error, refetch, isFetching } = useInsights();

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto pb-12">
        <PageHeader
          title="Citation Analytics & Insights"
          subtitle="Loading real-time corpus metrics from SQLite..."
        />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Skeleton className="h-28 rounded-xl" />
          <Skeleton className="h-28 rounded-xl" />
          <Skeleton className="h-28 rounded-xl" />
          <Skeleton className="h-28 rounded-xl" />
        </div>
        <Skeleton className="h-72 rounded-2xl" />
        <Skeleton className="h-80 rounded-2xl" />
      </div>
    );
  }

  if (isError || !insights) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto pb-12">
        <PageHeader
          title="Citation Analytics & Insights"
          subtitle="Corpus grounding verification matrix, citation support rates, and contradiction logs."
        />
        <Alert
          variant="error"
          title="Failed to Load Citation Analytics"
          icon={<AlertTriangle className="w-4 h-4" />}
        >
          {error?.message || 'Could not fetch insights from the analytics API endpoint.'}
          <div className="mt-3">
            <Button variant="secondary" size="sm" onClick={() => refetch()}>
              Retry
            </Button>
          </div>
        </Alert>
      </div>
    );
  }

  const {
    overview,
    quality,
    claim_distribution,
    top_cited_documents,
    contradiction_logs,
    daily_activity,
  } = insights;

  const citRatePercent = Math.round(quality.citation_verification_rate * 100);
  const claimRatePercent = Math.round(quality.claim_support_rate * 100);

  // Maximum activity count for chart scaling
  const maxDailyCount = Math.max(
    1,
    ...daily_activity.map((d) => Math.max(d.queries, d.citations))
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header with Refresh Control */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <PageHeader
          title="Citation Analytics & Insights"
          subtitle="Corpus-wide grounding verification matrix, citation support rates, and contradiction logs calculated from SQLite."
          breadcrumbs={[{ label: 'Citation Analytics' }]}
        />

        <div className="shrink-0">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => refetch()}
            isLoading={isFetching}
            icon={<RotateCw className="w-3.5 h-3.5" />}
          >
            Refresh Metrics
          </Button>
        </div>
      </div>

      {overview.total_documents === 0 && (
        <Alert
          variant="info"
          title="No Corpus Analytics Available Yet"
        >
          Your document repository is currently empty. Upload research papers in the Document Library
          and execute inquiries in the Research Workspace to generate citation density charts, claim support audits,
          and contradiction detection metrics.
        </Alert>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Overview Stat Cards                                               */}
      {/* ----------------------------------------------------------------- */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        <Card className="p-4 space-y-1">
          <span className="text-[11px] font-semibold text-content-muted uppercase tracking-wider block">
            Documents
          </span>
          <p className="text-2xl font-bold font-mono text-content-primary">
            {overview.total_documents}
          </p>
          <p className="text-[11px] text-content-secondary">Local repository</p>
        </Card>

        <Card className="p-4 space-y-1">
          <span className="text-[11px] font-semibold text-content-muted uppercase tracking-wider block">
            Indexed Chunks
          </span>
          <p className="text-2xl font-bold font-mono text-content-primary">
            {overview.total_indexed_chunks}
          </p>
          <p className="text-[11px] text-content-secondary">768-dim vectors</p>
        </Card>

        <Card className="p-4 space-y-1">
          <span className="text-[11px] font-semibold text-content-muted uppercase tracking-wider block">
            Total Queries
          </span>
          <p className="text-2xl font-bold font-mono text-content-primary">
            {overview.total_queries}
          </p>
          <p className="text-[11px] text-content-secondary">
            {overview.abstained_answers} abstained
          </p>
        </Card>

        <Card className="p-4 space-y-1">
          <span className="text-[11px] font-semibold text-content-muted uppercase tracking-wider block">
            Citation Passages
          </span>
          <p className="text-2xl font-bold font-mono text-content-primary">
            {overview.total_citations}
          </p>
          <p className="text-[11px] text-emerald-400 font-mono">
            {overview.verified_citations} verified
          </p>
        </Card>

        <Card className="p-4 space-y-1">
          <span className="text-[11px] font-semibold text-content-muted uppercase tracking-wider block">
            Citation Grounding
          </span>
          <p className="text-2xl font-bold font-mono text-brand">
            {citRatePercent}%
          </p>
          <p className="text-[11px] text-content-secondary">Exact passage match</p>
        </Card>

        <Card className="p-4 space-y-1">
          <span className="text-[11px] font-semibold text-content-muted uppercase tracking-wider block">
            Claim Support
          </span>
          <p className="text-2xl font-bold font-mono text-emerald-400">
            {claimRatePercent}%
          </p>
          <p className="text-[11px] text-content-secondary">
            {quality.supported_claims_count} / {quality.total_evaluated_claims} claims
          </p>
        </Card>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Two Column Grid: Claim Distribution & 14-Day Activity             */}
      {/* ----------------------------------------------------------------- */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Claim Verification Distribution (Col 6) */}
        <Card className="lg:col-span-6 p-6 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-content-primary mb-0.5">
                Claim Verification Distribution
              </h3>
              <p className="text-xs text-content-muted">
                Audit breakdown across {quality.total_evaluated_claims} evaluated claims
              </p>
            </div>
            <Badge variant="neutral" size="sm">
              {quality.total_evaluated_claims} Claims
            </Badge>
          </div>

          {/* Stacked Multi-Segment Progress Bar */}
          <div className="h-3 w-full rounded-full bg-surface-secondary overflow-hidden flex border border-border-subtle">
            {claim_distribution.map((item) => {
              if (item.percentage <= 0) return null;
              let bg = 'bg-slate-500';
              if (item.status === 'SUPPORTED') bg = 'bg-emerald-500';
              else if (item.status === 'PARTIALLY_SUPPORTED') bg = 'bg-amber-500';
              else if (item.status === 'CONTRADICTED') bg = 'bg-rose-500';
              else if (item.status === 'INSUFFICIENT_EVIDENCE') bg = 'bg-indigo-500';

              return (
                <div
                  key={item.status}
                  style={{ width: `${item.percentage}%` }}
                  className={`h-full ${bg} transition-all duration-300`}
                  title={`${item.status}: ${item.count} (${item.percentage}%)`}
                />
              );
            })}
          </div>

          {/* Breakdown Rows */}
          <div className="space-y-2.5 pt-1">
            {claim_distribution.map((item) => (
              <div
                key={item.status}
                className="flex items-center justify-between text-xs py-1 px-2.5 rounded-lg bg-surface-secondary/40 border border-border-subtle"
              >
                <div className="flex items-center gap-2">
                  <EvidenceStatusBadge status={item.status} size="sm" />
                </div>
                <div className="flex items-center gap-3 font-mono">
                  <span className="font-semibold text-content-primary">
                    {item.count} claims
                  </span>
                  <span className="text-content-muted w-12 text-right">
                    {item.percentage}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* 14-Day Activity Histogram (Col 6) */}
        <Card className="lg:col-span-6 p-6 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-content-primary mb-0.5">
                14-Day Research Activity
              </h3>
              <p className="text-xs text-content-muted">
                Daily query volume and extracted verified citations
              </p>
            </div>
            <div className="flex items-center gap-3 text-[11px] font-mono text-content-muted">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-brand" />
                <span>Queries</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-emerald-500" />
                <span>Citations</span>
              </span>
            </div>
          </div>

          {/* Daily Histogram Bars */}
          <div className="h-44 flex items-end justify-between gap-1.5 pt-4 pb-2 border-b border-border-subtle">
            {daily_activity.map((day) => {
              const queryHeight = Math.round((day.queries / maxDailyCount) * 100);
              const citHeight = Math.round((day.citations / maxDailyCount) * 100);

              return (
                <div
                  key={day.date}
                  className="flex-1 flex flex-col items-center gap-1 h-full justify-end group relative"
                >
                  {/* Tooltip on hover */}
                  <div className="absolute -top-10 hidden group-hover:flex flex-col items-center z-20 pointer-events-none">
                    <div className="px-2 py-1 rounded bg-surface-primary border border-border-subtle shadow-md text-[10px] font-mono whitespace-nowrap">
                      <p className="font-bold">{day.date}</p>
                      <p className="text-brand">Queries: {day.queries}</p>
                      <p className="text-emerald-400">Citations: {day.citations}</p>
                    </div>
                  </div>

                  <div className="w-full flex items-end justify-center gap-0.5 h-32">
                    <div
                      style={{ height: `${Math.max(queryHeight, 4)}%` }}
                      className="w-1.5 sm:w-2 bg-brand/80 group-hover:bg-brand rounded-t transition-all"
                    />
                    <div
                      style={{ height: `${Math.max(citHeight, 4)}%` }}
                      className="w-1.5 sm:w-2 bg-emerald-500/80 group-hover:bg-emerald-500 rounded-t transition-all"
                    />
                  </div>
                  <span className="text-[9px] font-mono text-content-muted truncate max-w-[28px]">
                    {day.date.slice(5)}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="flex items-center justify-between text-xs text-content-muted">
            <span>Past 14 days activity trend</span>
            <span className="font-mono">
              Peak single-day activity: {maxDailyCount} events
            </span>
          </div>
        </Card>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Document Grounding Rankings Table                                 */}
      {/* ----------------------------------------------------------------- */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-content-primary mb-0.5">
              Document Grounding Rankings
            </h3>
            <p className="text-xs text-content-muted">
              Most frequently cited and verified documents across research sessions
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/documents')}
            icon={<ExternalLink className="w-3.5 h-3.5" />}
          >
            Manage Library
          </Button>
        </div>

        {top_cited_documents.length === 0 ? (
          <div className="text-center py-10 text-xs text-content-muted border border-dashed border-border-subtle rounded-xl">
            No document citations recorded yet. Perform queries in the Research Workspace
            to generate citation statistics.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border-subtle text-content-muted font-semibold uppercase tracking-wider text-[10px]">
                  <th className="pb-3 pl-1">Document</th>
                  <th className="pb-3 text-right">Vector Chunks</th>
                  <th className="pb-3 text-right">Total Citations</th>
                  <th className="pb-3 text-right">Verified Citations</th>
                  <th className="pb-3 text-right">Grounding Rate</th>
                  <th className="pb-3 text-right pr-1">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y border-border-subtle">
                {top_cited_documents.map((doc) => {
                  const ratePercent = Math.round(doc.verification_rate * 100);
                  return (
                    <tr
                      key={doc.document_id}
                      className="hover:bg-surface-secondary/40 transition-colors"
                    >
                      <td className="py-3 pl-1">
                        <div className="flex items-center gap-2.5 truncate max-w-sm">
                          <DocumentTypeIcon filename={doc.filename} size="sm" />
                          <div className="truncate">
                            <p className="font-semibold text-content-primary truncate">
                              {doc.title || doc.filename}
                            </p>
                            <p className="text-[10px] text-content-muted font-mono truncate">
                              {doc.filename}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 text-right font-mono text-content-secondary">
                        {doc.total_chunks}
                      </td>
                      <td className="py-3 text-right font-mono text-content-primary font-bold">
                        {doc.total_citations}
                      </td>
                      <td className="py-3 text-right font-mono text-emerald-400 font-bold">
                        {doc.verified_citations}
                      </td>
                      <td className="py-3 text-right">
                        <div className="inline-flex items-center gap-1.5 font-mono">
                          <div className="w-16 h-1.5 rounded-full bg-surface-secondary overflow-hidden hidden sm:block">
                            <div
                              className="h-full bg-emerald-500 rounded-full"
                              style={{ width: `${ratePercent}%` }}
                            />
                          </div>
                          <span className="font-bold text-content-primary">
                            {ratePercent}%
                          </span>
                        </div>
                      </td>
                      <td className="py-3 text-right pr-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/documents/${doc.document_id}`)}
                          icon={<ExternalLink className="w-3 h-3 text-brand" />}
                          className="text-xs text-brand hover:text-brand-light p-1"
                        >
                          View Doc
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* ----------------------------------------------------------------- */}
      {/* Contradiction & Quality Monitoring Logs                           */}
      {/* ----------------------------------------------------------------- */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-content-primary mb-0.5">
              Cross-Document Contradiction & Conflict Log
            </h3>
            <p className="text-xs text-content-muted">
              Audit log of contradicting claims and conflicting evidence across documents
            </p>
          </div>
          <Badge
            variant={contradiction_logs.length > 0 ? 'error' : 'success'}
            size="sm"
          >
            {contradiction_logs.length}{' '}
            {contradiction_logs.length === 1 ? 'Contradiction' : 'Contradictions'}
          </Badge>
        </div>

        {contradiction_logs.length === 0 ? (
          <div className="p-6 rounded-xl bg-emerald-500/5 border border-emerald-500/20 text-center space-y-1">
            <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto" />
            <p className="text-xs font-semibold text-content-primary">
              Clean Corpus Grounding Audit
            </p>
            <p className="text-[11px] text-content-muted max-w-md mx-auto">
              No cross-document contradictions or conflicting claims have been detected
              among verified citations in the local repository.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {contradiction_logs.map((log, idx) => (
              <div
                key={log.message_id || idx}
                className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/5 space-y-2"
              >
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 text-rose-400 font-semibold">
                    <XCircle className="w-4 h-4 shrink-0" />
                    <span>Contradictory Claim Detected</span>
                  </div>
                  <span className="text-[10px] text-content-muted font-mono">
                    {formatRelativeTime(log.created_at)}
                  </span>
                </div>

                <div className="text-xs text-content-primary font-semibold">
                  "{log.claim_text}"
                </div>

                <div className="p-2.5 rounded bg-surface-primary border border-border-subtle text-xs text-content-secondary font-serif italic">
                  Conflicting Source Passage: "{log.conflicting_passage}"
                </div>

                {log.source_document_title && (
                  <p className="text-[10px] text-content-muted font-mono">
                    Document: {log.source_document_title}
                    {log.page_number && ` • Page ${log.page_number}`}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};
