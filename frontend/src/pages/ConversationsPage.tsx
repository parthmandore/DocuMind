/**
 * Multi-Turn Conversations Workspace (Phase 5.8)
 *
 * Full-featured conversational document research interface:
 * - Thread management: create, rename, delete, search
 * - Multi-turn follow-ups maintaining conversation context
 * - Rich markdown responses with in-text citation badges
 * - Clickable citation links jumping directly to exact PDF bounding boxes
 * - Expandable cited evidence drawer per assistant response
 * - Persistent across page reloads and browser sessions
 */

import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  MessageSquare,
  Plus,
  Search,
  Trash2,
  Edit2,
  Check,
  X,
  Send,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Clock,
  User,
  Bot,
} from 'lucide-react';

import {
  useConversations,
  useConversation,
} from '@/hooks/useQueries';
import {
  useCreateConversation,
  useRenameConversation,
  useDeleteConversation,
  useExecuteQuery,
} from '@/hooks/useMutations';
import type {
  MessageResponse,
  MessageCitationResponse,
  CitationItem,
} from '@/types/api';
import { formatRelativeTime, formatDate } from '@/utils/date';
import { useToast } from '@/hooks/useToast';
import { useRouteMetadata } from '@/hooks/useRouteMetadata';
import { formatError } from '@/utils/errors';

// UI Primitives
import {
  Button,
  Card,
  Textarea,
  Badge,
  ConfirmDialog,
  Skeleton,
} from '@/components/ui';

// Document Components
import { EvidenceStatusBadge } from '@/components/document';
import { MarkdownView } from '@/components/common/MarkdownView';

export const ConversationsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();

  useRouteMetadata({
    title: 'Research Threads | DocuMind',
    description:
      'Persistent multi-turn research conversations with grounded evidence passages and verification traces.',
    isPrivate: true,
    canonicalPath: '/conversations',
    breadcrumbs: [{ label: 'Conversations' }],
  });

  // URL state
  const selectedConvId = searchParams.get('id');

  // Search filter for threads
  const [threadSearch, setThreadSearch] = useState('');

  // Queries
  const {
    data: conversations = [],
    isLoading: isLoadingConvs,
    refetch: refetchConvs,
  } = useConversations(0, 100, threadSearch.trim() || undefined);

  const {
    data: activeConversation,
    isLoading: isLoadingActive,
    refetch: refetchActive,
  } = useConversation(selectedConvId);

  // Mutations
  const createMutation = useCreateConversation();
  const renameMutation = useRenameConversation();
  const deleteMutation = useDeleteConversation();
  const queryMutation = useExecuteQuery();

  // UI State
  const [question, setQuestion] = useState('');
  const [editingConvId, setEditingConvId] = useState<string | null>(null);
  const [editTitleValue, setEditTitleValue] = useState('');
  const [convToDelete, setConvToDelete] = useState<string | null>(null);

  // Expanded evidence drawers keyed by message ID
  const [expandedEvidence, setExpandedEvidence] = useState<Record<string, boolean>>({});
  const [expandedClaims, setExpandedClaims] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Automatically select first conversation if none selected and conversations exist
  useEffect(() => {
    if (!selectedConvId && conversations.length > 0 && !isLoadingConvs) {
      setSearchParams({ id: conversations[0].id });
    }
  }, [selectedConvId, conversations, isLoadingConvs, setSearchParams]);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    if (activeConversation?.messages && activeConversation.messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [activeConversation?.messages, queryMutation.isPending]);

  const handleSelectConversation = (id: string) => {
    setSearchParams({ id });
    setEditingConvId(null);
  };

  const handleCreateNewThread = async () => {
    try {
      const newConv = await createMutation.mutateAsync('New Research Session');
      toast.success('New research thread initialized.', { title: 'Thread Created' });
      setSearchParams({ id: newConv.id });
      setEditingConvId(newConv.id);
      setEditTitleValue('New Research Session');
    } catch (err) {
      const errObj = formatError(err);
      toast.error(`Could not create thread: ${errObj.message}`, { title: 'Thread Error' });
      console.error('Failed to create thread:', err);
    }
  };

  const handleStartRename = (id: string, currentTitle: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setEditingConvId(id);
    setEditTitleValue(currentTitle);
  };

  const handleConfirmRename = async (id: string, e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!editTitleValue.trim()) return;

    try {
      await renameMutation.mutateAsync({ id, title: editTitleValue.trim() });
      toast.info(`Thread renamed to "${editTitleValue.trim()}".`, { title: 'Thread Renamed' });
      setEditingConvId(null);
    } catch (err) {
      const errObj = formatError(err);
      toast.error(`Rename failed: ${errObj.message}`, { title: 'Rename Error' });
      console.error('Failed to rename conversation:', err);
    }
  };

  const handleCancelRename = () => {
    setEditingConvId(null);
    setEditTitleValue('');
  };

  const handleDeleteConfirm = async () => {
    if (!convToDelete) return;
    try {
      await deleteMutation.mutateAsync(convToDelete);
      toast.success('Research thread and linked messages removed.', { title: 'Thread Deleted' });
      setConvToDelete(null);
      // Select another thread if available
      const remaining = conversations.filter((c) => c.id !== convToDelete);
      if (remaining.length > 0) {
        setSearchParams({ id: remaining[0].id });
      } else {
        setSearchParams({});
      }
    } catch (err) {
      const errObj = formatError(err);
      toast.error(`Failed to delete thread: ${errObj.message}`, { title: 'Delete Error' });
      console.error('Failed to delete conversation:', err);
    }
  };

  const handleSubmitQuestion = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!question.trim() || queryMutation.isPending || !selectedConvId) return;

    const currentQ = question.trim();
    setQuestion('');

    try {
      await queryMutation.mutateAsync({
        question: currentQ,
        conversation_id: selectedConvId,
      });
      // Refetch conversation details to get newly recorded message and citations
      refetchActive();
      refetchConvs();
    } catch (err) {
      const errObj = formatError(err);
      toast.error(`Query synthesis failed: ${errObj.message}`, { title: 'Synthesis Error' });
      console.error('Failed to execute conversational query:', err);
      // Restore question in case of failure
      setQuestion(currentQ);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmitQuestion();
    }
  };

  const toggleEvidence = (msgId: string) => {
    setExpandedEvidence((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const toggleClaims = (msgId: string) => {
    setExpandedClaims((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const handleOpenCitation = (cit: MessageCitationResponse | CitationItem) => {
    if (!cit.document_id) return;
    const url = `/documents/${cit.document_id}?page=${cit.page_number}&chunkId=${cit.chunk_id}&from=conversations&quote=${encodeURIComponent(
      cit.exact_quote.slice(0, 100)
    )}&verified=${'is_verified' in cit ? cit.is_verified : cit.verification_status === 'verified'}`;
    navigate(url);
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 h-full w-full">
      {/* Main Split Grid - Fills available viewport height without page scrolling */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 min-h-0 h-full">
        {/* --------------------------------------------------------------- */}
        {/* Left Sidebar: Threads List (Col 4)                              */}
        {/* --------------------------------------------------------------- */}
        <Card className="lg:col-span-4 flex flex-col h-full min-h-0 overflow-hidden p-0 bg-surface-secondary/20 border-border-subtle">
          {/* Thread List Header & Actions */}
          <div className="p-3.5 border-b border-border-subtle space-y-3 bg-surface-primary">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-brand" />
                <span className="text-xs font-bold uppercase tracking-wider text-content-primary">
                  Research Threads
                </span>
                <span className="text-xs font-mono text-content-muted">
                  ({conversations.length})
                </span>
              </div>

              <Button
                variant="primary"
                size="sm"
                onClick={handleCreateNewThread}
                isLoading={createMutation.isPending}
                icon={<Plus className="w-3.5 h-3.5" />}
                className="text-xs"
              >
                New Thread
              </Button>
            </div>

            {/* Thread Search Box */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-content-muted absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search research threads..."
                value={threadSearch}
                onChange={(e) => setThreadSearch(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-surface-secondary border border-border-subtle rounded-lg text-content-primary placeholder:text-content-muted focus:outline-none focus:border-brand"
              />
            </div>
          </div>

          {/* Threads Scrollable List */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {isLoadingConvs ? (
              <div className="p-3 space-y-2">
                <Skeleton className="h-14 w-full rounded-xl" />
                <Skeleton className="h-14 w-full rounded-xl" />
                <Skeleton className="h-14 w-full rounded-xl" />
              </div>
            ) : conversations.length === 0 ? (
              <div className="text-center py-12 px-4 space-y-2">
                <MessageSquare className="w-8 h-8 text-content-muted mx-auto opacity-50" />
                <p className="text-xs font-semibold text-content-secondary">
                  {threadSearch ? 'No matching threads found' : 'No research threads yet'}
                </p>
                <p className="text-[11px] text-content-muted max-w-[200px] mx-auto">
                  {threadSearch
                    ? 'No conversations match your current search query.'
                    : 'Create a new thread to start a persistent multi-turn research inquiry.'}
                </p>
                {threadSearch ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setThreadSearch('')}
                    className="mt-2 text-xs"
                  >
                    Clear Filter
                  </Button>
                ) : (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleCreateNewThread}
                    icon={<Plus className="w-3.5 h-3.5" />}
                    className="mt-2 text-xs"
                  >
                    Create First Thread
                  </Button>
                )}
              </div>
            ) : (
              conversations.map((thread) => {
                const isActive = thread.id === selectedConvId;
                const isEditing = editingConvId === thread.id;

                return (
                  <div
                    key={thread.id}
                    onClick={() => handleSelectConversation(thread.id)}
                    className={`group relative p-3 rounded-xl border text-left transition-all duration-120 ease-standard cursor-pointer select-none active:scale-[0.985] transform-gpu ${
                      isActive
                        ? 'bg-brand/10 border-brand shadow-sm'
                        : 'bg-surface-primary border-border-subtle hover:border-border-muted hover:bg-surface-secondary/60'
                    }`}
                  >
                    {isEditing ? (
                      <form
                        onSubmit={(e) => handleConfirmRename(thread.id, e)}
                        onClick={(e) => e.stopPropagation()}
                        className="flex items-center gap-1.5"
                      >
                        <input
                          type="text"
                          value={editTitleValue}
                          onChange={(e) => setEditTitleValue(e.target.value)}
                          autoFocus
                          className="w-full text-xs bg-surface-secondary border border-brand px-2 py-1 rounded text-content-primary focus:outline-none"
                        />
                        <button
                          type="submit"
                          className="p-1 rounded text-emerald-400 hover:bg-emerald-500/10"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={handleCancelRename}
                          className="p-1 rounded text-content-muted hover:bg-surface-secondary"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </form>
                    ) : (
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <p
                            className={`text-xs font-semibold truncate ${
                              isActive ? 'text-brand-light font-bold' : 'text-content-primary'
                            }`}
                          >
                            {thread.title}
                          </p>
                          <p className="text-[10px] text-content-muted flex items-center gap-1 mt-1 font-mono">
                            <Clock className="w-3 h-3" />
                            <span>{formatRelativeTime(thread.updated_at)}</span>
                          </p>
                        </div>

                        {/* Actions (Visible on hover or active) */}
                        <div className="flex items-center gap-0.5 opacity-80 group-hover:opacity-100 shrink-0">
                          <button
                            type="button"
                            title="Rename Thread"
                            onClick={(e) => handleStartRename(thread.id, thread.title, e)}
                            className="p-1 rounded text-content-muted hover:text-content-primary hover:bg-surface-secondary"
                          >
                            <Edit2 className="w-3 h-3" />
                          </button>
                          <button
                            type="button"
                            title="Delete Thread"
                            onClick={(e) => {
                              e.stopPropagation();
                              setConvToDelete(thread.id);
                            }}
                            className="p-1 rounded text-content-muted hover:text-rose-400 hover:bg-rose-500/10"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </Card>

        {/* --------------------------------------------------------------- */}
        {/* Right Pane: Active Thread Chat & Evidence Workspace (Col 8)    */}
        {/* --------------------------------------------------------------- */}
        <Card className="lg:col-span-8 flex flex-col h-full min-h-0 overflow-hidden p-0 bg-surface-primary border-border-subtle">
          {selectedConvId && isLoadingActive ? (
            <div className="flex flex-col h-full">
              <div className="p-4 border-b border-border-subtle flex items-center justify-between gap-4 bg-surface-primary">
                <Skeleton className="h-6 w-48 rounded-lg" />
                <Skeleton className="h-7 w-24 rounded-lg" />
              </div>
              <div className="flex-1 p-6 space-y-6">
                <div className="flex gap-3 justify-end">
                  <Skeleton className="h-16 w-2/3 rounded-2xl" />
                </div>
                <div className="flex gap-3">
                  <Skeleton className="h-28 w-3/4 rounded-2xl" />
                </div>
                <div className="flex gap-3 justify-end">
                  <Skeleton className="h-12 w-1/2 rounded-2xl" />
                </div>
              </div>
            </div>
          ) : selectedConvId && activeConversation ? (
            <>
              {/* Thread Header */}
              <div className="p-4 border-b border-border-subtle flex items-center justify-between gap-4 bg-surface-primary">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-content-primary truncate">
                      {activeConversation.title}
                    </h2>
                    <button
                      type="button"
                      onClick={() =>
                        handleStartRename(
                          activeConversation.id,
                          activeConversation.title
                        )
                      }
                      className="text-content-muted hover:text-content-primary p-1"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <p className="text-[11px] text-content-muted">
                    Session started {formatDate(activeConversation.created_at)} •{' '}
                    {activeConversation.messages.length} messages recorded
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => setConvToDelete(activeConversation.id)}
                    icon={<Trash2 className="w-3.5 h-3.5" />}
                  >
                    Delete Thread
                  </Button>
                </div>
              </div>

              {/* Messages Scroll Area - Independently scrollable */}
              <div className="flex-1 overflow-y-auto min-h-0 p-4 sm:p-5 space-y-5 bg-surface-secondary/20">
                {activeConversation.messages.length === 0 ? (
                  <div className="text-center py-12 px-4 space-y-2.5">
                    <div className="w-10 h-10 rounded-xl bg-brand/10 border border-brand/20 flex items-center justify-center text-brand mx-auto">
                      <Sparkles className="w-5 h-5" />
                    </div>
                    <h3 className="text-sm font-bold text-content-primary">
                      Begin Grounded Research Inquiry
                    </h3>
                    <p className="text-xs text-content-muted max-w-sm mx-auto leading-relaxed">
                      Ask your first question below. DocuMind will retrieve relevant chunks
                      from your documents, synthesize an answer, and link verifiable citations.
                    </p>
                  </div>
                ) : (
                  activeConversation.messages.map((msg: MessageResponse) => {
                    const isUser = msg.role === 'user';
                    const hasCitations = msg.citations && msg.citations.length > 0;
                    const isEvidenceOpen = !!expandedEvidence[msg.id];
                    const metadata = msg.message_metadata || {};
                    const supportingClaims = metadata.supporting_claims || [];
                    const isClaimsOpen = !!expandedClaims[msg.id];

                    if (isUser) {
                      return (
                        <div
                          key={msg.id}
                          className="flex justify-end gap-3 max-w-3xl ml-auto"
                        >
                          <div className="space-y-1 text-right">
                            <div className="inline-block p-4 rounded-2xl bg-surface-elevated text-content-primary border border-border-muted/60 text-sm shadow-xs font-sans leading-relaxed text-left">
                              {msg.content}
                            </div>
                            <span className="text-[10px] text-content-muted font-mono block px-1">
                              {formatRelativeTime(msg.created_at)}
                            </span>
                          </div>
                          <div className="w-8 h-8 rounded-full bg-brand/10 border border-brand/30 flex items-center justify-center text-brand shrink-0 mt-1">
                            <User className="w-4 h-4" />
                          </div>
                        </div>
                      );
                    }

                    // Assistant Message
                    return (
                      <div key={msg.id} className="flex gap-3 max-w-3xl mr-auto">
                        <div className="w-8 h-8 rounded-full bg-surface-secondary border border-brand/40 flex items-center justify-center text-brand shrink-0 mt-1">
                          <Bot className="w-4 h-4" />
                        </div>

                        <div className="space-y-3 flex-1 min-w-0">
                          <Card className="p-5 shadow-sm space-y-4 bg-surface-primary border-border-subtle">
                            {/* Message Header */}
                            <div className="flex items-center justify-between text-xs pb-3 border-b border-border-subtle">
                              <div className="flex items-center gap-2">
                                <Sparkles className="w-3.5 h-3.5 text-brand" />
                                <span className="font-bold text-content-primary">
                                  DocuMind Grounded Intelligence
                                </span>
                              </div>
                              <span className="text-[10px] text-content-muted font-mono">
                                {formatRelativeTime(msg.created_at)}
                              </span>
                            </div>

                            {/* Operational Execution Trace (Safe, no private chain-of-thought) */}
                            {msg.thinking_trace && (
                              <details className="text-xs rounded-lg bg-surface-secondary/50 border border-border-subtle p-3 text-content-muted">
                                <summary className="cursor-pointer font-mono font-semibold text-content-secondary select-none">
                                  Operational Execution Trace
                                </summary>
                                <p className="mt-2 font-mono text-[11px] leading-relaxed whitespace-pre-wrap text-content-primary">
                                  {msg.thinking_trace}
                                </p>
                              </details>
                            )}

                            {/* Markdown Content with In-Text Citations */}
                            <div className="text-sm">
                              <MarkdownView
                                content={msg.content}
                                citations={msg.citations}
                                onCitationClick={(cit) => handleOpenCitation(cit)}
                              />
                            </div>

                            {/* Claims & Citations Controls */}
                            {(hasCitations || supportingClaims.length > 0) && (
                              <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border-subtle">
                                {hasCitations && (
                                  <Button
                                    variant="secondary"
                                    size="sm"
                                    onClick={() => toggleEvidence(msg.id)}
                                    icon={
                                      isEvidenceOpen ? (
                                        <ChevronUp className="w-3.5 h-3.5" />
                                      ) : (
                                        <ChevronDown className="w-3.5 h-3.5" />
                                      )
                                    }
                                    className="text-xs"
                                  >
                                    {msg.citations.length}{' '}
                                    {msg.citations.length === 1
                                      ? 'Cited Source'
                                      : 'Cited Sources'}
                                  </Button>
                                )}

                                {supportingClaims.length > 0 && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => toggleClaims(msg.id)}
                                    icon={
                                      isClaimsOpen ? (
                                        <ChevronUp className="w-3.5 h-3.5" />
                                      ) : (
                                        <ChevronDown className="w-3.5 h-3.5" />
                                      )
                                    }
                                    className="text-xs text-content-secondary"
                                  >
                                    Claim Audit ({supportingClaims.length})
                                  </Button>
                                )}
                              </div>
                            )}

                            {/* Expanded Evidence Drawer */}
                            {isEvidenceOpen && hasCitations && (
                              <div className="space-y-2.5 pt-2">
                                <span className="text-[11px] font-bold uppercase tracking-wider text-content-muted block">
                                  Cited Evidence Passages:
                                </span>
                                {msg.citations.map((cit, citIdx) => (
                                  <div
                                    key={cit.id || citIdx}
                                    className="p-3 rounded-xl bg-surface-secondary/60 border border-border-subtle space-y-2"
                                  >
                                    <div className="flex items-center justify-between gap-2 text-xs">
                                      <div className="flex items-center gap-1.5 min-w-0">
                                        <span className="font-mono font-bold text-brand px-1.5 py-0.5 rounded bg-brand/10 text-[11px]">
                                          [P{citIdx + 1}]
                                        </span>
                                        <span className="font-semibold text-content-primary truncate">
                                          {cit.document_filename || 'Indexed Document'}
                                        </span>
                                      </div>
                                      <Badge variant="neutral" size="sm">
                                        Page {cit.page_number}
                                      </Badge>
                                    </div>

                                    <p className="text-xs text-content-secondary font-serif leading-relaxed italic bg-surface-primary/70 p-2.5 rounded border border-border-subtle">
                                      "{cit.exact_quote}"
                                    </p>

                                    <div className="flex items-center justify-between pt-1">
                                      <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                                        <ShieldCheck className="w-3 h-3" />
                                        <span>Verified Grounding</span>
                                      </span>

                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => handleOpenCitation(cit)}
                                        icon={<ExternalLink className="w-3 h-3 text-brand" />}
                                        className="text-xs text-brand hover:text-brand-light p-1"
                                      >
                                        Open in PDF
                                      </Button>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Expanded Claims Drawer */}
                            {isClaimsOpen && supportingClaims.length > 0 && (
                              <div className="space-y-2 pt-2">
                                <span className="text-[11px] font-bold uppercase tracking-wider text-content-muted block">
                                  Claim Audit Details:
                                </span>
                                {supportingClaims.map((claim: any, cIdx: number) => (
                                  <div
                                    key={cIdx}
                                    className="p-2.5 rounded-lg border border-border-subtle bg-surface-secondary/40 text-xs space-y-1.5"
                                  >
                                    <div className="flex items-center justify-between gap-2">
                                      <p className="font-semibold text-content-primary truncate">
                                        "{claim.claim_text}"
                                      </p>
                                      <EvidenceStatusBadge
                                        status={claim.support_state}
                                        size="sm"
                                      />
                                    </div>
                                    {claim.reasoning && (
                                      <p className="text-[11px] text-content-muted italic">
                                        {claim.reasoning}
                                      </p>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                          </Card>
                        </div>
                      </div>
                    );
                  })
                )}

                {/* Submitting Indicator */}
                {queryMutation.isPending && (
                  <div className="flex gap-3 max-w-3xl mr-auto">
                    <div className="w-8 h-8 rounded-full bg-surface-secondary border border-brand/40 flex items-center justify-center text-brand shrink-0 animate-pulse">
                      <Sparkles className="w-4 h-4 animate-spin" />
                    </div>
                    <Card className="p-4 bg-surface-primary border-brand/40 space-y-2">
                      <div className="flex items-center gap-2 text-xs font-semibold text-content-primary">
                        <span>DocuMind is synthesizing a grounded response...</span>
                      </div>
                      <p className="text-[11px] text-content-muted">
                        Executing hybrid search, verifying evidence claims, and extracting citations.
                      </p>
                    </Card>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Bottom Follow-up Input Bar - Fixed at bottom */}
              <div className="p-3 sm:p-3.5 border-t border-border-subtle bg-surface-primary shrink-0 space-y-2">
                <form onSubmit={handleSubmitQuestion} className="space-y-2">
                  <div className="relative">
                    <Textarea
                      ref={textareaRef}
                      rows={2}
                      placeholder="Ask a follow-up question grounded in this session... (Enter to send, Shift+Enter for newline)"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      onKeyDown={handleKeyDown}
                      disabled={queryMutation.isPending}
                      className="resize-none font-sans text-xs sm:text-sm pr-12 focus:border-brand"
                    />
                  </div>

                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[11px] text-content-muted font-mono">
                      Context preserved across turns in this session
                    </span>

                    <div className="flex items-center gap-2">
                      {question && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => setQuestion('')}
                          disabled={queryMutation.isPending}
                          className="text-xs"
                        >
                          Clear
                        </Button>
                      )}
                      <Button
                        type="submit"
                        variant="primary"
                        size="sm"
                        isLoading={queryMutation.isPending}
                        disabled={!question.trim() || queryMutation.isPending}
                        icon={<Send className="w-3.5 h-3.5" />}
                        className="text-xs"
                      >
                        Send
                      </Button>
                    </div>
                  </div>
                </form>
              </div>
            </>
          ) : (
            /* No Thread Selected State */
            <div className="h-full flex items-center justify-center p-8 text-center space-y-4">
              <div className="max-w-md space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-surface-secondary border border-border-subtle flex items-center justify-center text-content-muted mx-auto">
                  <MessageSquare className="w-6 h-6" />
                </div>
                <h3 className="text-base font-bold text-content-primary">
                  Select or Create a Research Thread
                </h3>
                <p className="text-xs text-content-muted leading-relaxed">
                  Multi-turn research threads allow iterative follow-up inquiries while
                  maintaining strict evidence verification and persistent citation audit trails.
                </p>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleCreateNewThread}
                  icon={<Plus className="w-3.5 h-3.5" />}
                >
                  Create New Thread
                </Button>
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Delete Confirmation Dialog                                        */}
      {/* ----------------------------------------------------------------- */}
      <ConfirmDialog
        isOpen={!!convToDelete}
        onClose={() => setConvToDelete(null)}
        onConfirm={handleDeleteConfirm}
        title="Delete Research Thread"
        message="Are you sure you want to delete this research thread? All recorded messages, thinking traces, and citation linkages will be permanently removed from SQLite."
        confirmLabel="Delete Thread"
        cancelLabel="Cancel"
        variant="danger"
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
};
