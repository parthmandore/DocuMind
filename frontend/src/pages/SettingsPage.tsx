import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useHealth } from '@/hooks/useHealth';
import { useTheme } from '@/context/ThemeContext';
import { aiProviderApi } from '@/services/api';
import { queryKeys } from '@/services/queryKeys';
import type { AIProviderType } from '@/types/api';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Alert } from '@/components/ui/Alert';
import { Skeleton } from '@/components/ui/Skeleton';
import { useToast } from '@/hooks/useToast';
import { useRouteMetadata } from '@/hooks/useRouteMetadata';
import {
  Cpu,
  Database,
  ShieldCheck,
  RefreshCw,
  FolderLock,
  Sun,
  Moon,
  Laptop,
  Cloud,
  CheckCircle2,
  AlertTriangle,
  Server,
  Layers,
  KeyRound,
  Shield,
  HelpCircle,
  EyeOff
} from 'lucide-react';
import { cn } from '@/utils/cn';
import { telemetry } from '@/services/telemetry';
import { SupportModal } from '@/components/layout/SupportModal';

export const SettingsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const toast = useToast();

  useRouteMetadata({
    title: 'Settings & Diagnostics | DocuMind',
    description:
      'Configure dual AI generation engines (Groq Cloud & local Ollama), memory limits, and hardware concurrency.',
    isPrivate: true,
    canonicalPath: '/settings',
  });

  const { health, isLoading: isHealthLoading, isOnline, isOllamaConnected, refetch } = useHealth();
  const { theme, setTheme } = useTheme();
  const [switchError, setSwitchError] = useState<string | null>(null);
  const [isSupportOpen, setIsSupportOpen] = useState(false);
  const [telemetryEnabled, setTelemetryEnabled] = useState(() => telemetry.isEnabled());

  const handleToggleTelemetry = () => {
    const next = !telemetryEnabled;
    telemetry.setEnabled(next);
    setTelemetryEnabled(next);
    toast.success(
      next
        ? 'Anonymous product milestone events will be recorded locally.'
        : 'All milestone telemetry has been disabled and purged from memory.',
      {
        title: next ? 'Milestone Telemetry Enabled' : 'Milestone Telemetry Disabled',
      }
    );
  };

  // AI Provider settings query
  const {
    data: providerSettings,
    isLoading: isProviderLoading,
    refetch: refetchProvider
  } = useQuery({
    queryKey: queryKeys.aiProvider,
    queryFn: ({ signal }) => aiProviderApi.get(signal),
    staleTime: 5000,
  });

  // Switch AI Provider mutation
  const switchMutation = useMutation({
    mutationFn: (target: AIProviderType) => aiProviderApi.set(target),
    onSuccess: (data, target) => {
      setSwitchError(null);
      queryClient.setQueryData(queryKeys.aiProvider, data);
      queryClient.invalidateQueries({ queryKey: queryKeys.health });
      toast.success(
        target === 'groq'
          ? 'Switched to Groq Cloud API for ultra-fast generation.'
          : 'Switched to Ollama for 100% offline local generation.',
        { title: 'AI Provider Updated' }
      );
    },
    onError: (err: any) => {
      const msg = err?.message || 'Failed to switch AI provider.';
      setSwitchError(msg);
      toast.error(msg, { title: 'Provider Switch Failed' });
    },
  });

  const activeProvider = providerSettings?.active_provider || health?.active_provider || 'ollama';
  const isGroq = activeProvider === 'groq';

  const handleSwitch = (target: AIProviderType) => {
    if (target === activeProvider || switchMutation.isPending) return;
    setSwitchError(null);
    switchMutation.mutate(target);
  };

  const handleRefreshAll = () => {
    refetch();
    refetchProvider();
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-content-primary">System & AI Diagnostics</h2>
          <p className="text-xs text-content-secondary">
            Configure dual AI inference providers, workspace appearance, and inspect local hardware concurrency.
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={handleRefreshAll}
          isLoading={isHealthLoading || isProviderLoading}
          icon={<RefreshCw className="w-3.5 h-3.5" />}
        >
          Run Diagnostic Check
        </Button>
      </div>

      {switchError && (
        <Alert variant="error" title="Provider Switch Failed">
          {switchError}
        </Alert>
      )}

      {/* DUAL AI INFERENCE PROVIDER CARD */}
      <Card className="p-6 space-y-5 border-brand/20 bg-surface-primary">
        <div className="flex items-center justify-between border-b border-border-subtle pb-3">
          <div className="flex items-center gap-2.5">
            <Layers className="w-5 h-5 text-brand" />
            <div>
              <h3 className="text-sm font-semibold text-content-primary">Dual AI Inference Architecture</h3>
              <p className="text-xs text-content-secondary">
                Switch seamlessly between local Ollama inference and temporary remote Groq generation.
              </p>
            </div>
          </div>
          <StatusBadge
            status={providerSettings?.provider_health?.available ? 'healthy' : 'degraded'}
            label={activeProvider === 'groq' ? 'Groq Active' : 'Ollama Active'}
          />
        </div>

        {/* Cloud Inference Notice / Warning */}
        {isGroq ? (
          <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3">
            <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
            <div className="space-y-1 text-xs">
              <span className="font-semibold text-amber-600 dark:text-amber-400 block">
                Remote Cloud Inference Active (Groq API)
              </span>
              <p className="text-content-secondary leading-relaxed">
                Queries and selected document passages are transmitted to Groq over HTTPS for generation. Local document files, SQLite database storage, chunking, and 768-dim <code className="font-mono text-content-primary">nomic-embed-text</code> embeddings remain strictly on this machine. Citations continue to be verified by your local verifier.
              </p>
            </div>
          </div>
        ) : (
          <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-start gap-3">
            <ShieldCheck className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
            <div className="space-y-1 text-xs">
              <span className="font-semibold text-emerald-600 dark:text-emerald-400 block">
                Local AI Inference Mode Active
              </span>
              <p className="text-content-secondary leading-relaxed">
                Zero document data or queries leave this machine. Generation and embeddings are processed locally via Ollama with the hardware arbiter enforcing single-flight execution.
              </p>
            </div>
          </div>
        )}

        {/* Dual Provider Selection Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Local Ollama Card */}
          <div
            onClick={() => handleSwitch('ollama')}
            className={cn(
              'relative flex flex-col justify-between p-4 rounded-xl border transition-all cursor-pointer select-none space-y-4',
              !isGroq
                ? 'bg-brand/5 border-brand ring-1 ring-brand/30 shadow-xs'
                : 'bg-surface-secondary border-border-subtle hover:border-border-muted hover:bg-surface-secondary/80'
            )}
          >
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={cn(
                    'p-2 rounded-lg',
                    !isGroq ? 'bg-brand/15 text-brand' : 'bg-surface-tertiary text-content-secondary'
                  )}>
                    <Cpu className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-content-primary">Local — Ollama</h4>
                    <span className="text-[10px] text-content-muted">Permanent Local Engine</span>
                  </div>
                </div>
                {!isGroq && (
                  <span className="flex items-center gap-1 text-[11px] font-semibold text-brand">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Active
                  </span>
                )}
              </div>

              <div className="space-y-1 text-xs text-content-secondary pt-1">
                <div className="flex justify-between py-0.5 border-b border-border-subtle/50 text-[11px]">
                  <span className="text-content-muted">Generation:</span>
                  <span className="font-mono font-medium text-content-primary">qwen3:4b</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-border-subtle/50 text-[11px]">
                  <span className="text-content-muted">Embeddings:</span>
                  <span className="font-mono font-medium text-content-primary">nomic-embed-text (768d)</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-border-subtle/50 text-[11px]">
                  <span className="text-content-muted">Network:</span>
                  <span className="font-medium text-emerald-500">Local Host Only</span>
                </div>
                <div className="flex justify-between py-0.5 text-[11px]">
                  <span className="text-content-muted">Memory Footprint:</span>
                  <span className="font-medium text-content-secondary">Local RAM (~3.5 GB)</span>
                </div>
              </div>
            </div>

            <Button
              type="button"
              variant={!isGroq ? 'primary' : 'secondary'}
              size="sm"
              className="w-full text-xs font-medium"
              disabled={!isGroq || switchMutation.isPending}
              isLoading={switchMutation.isPending && switchMutation.variables === 'ollama'}
            >
              {!isGroq ? 'Active Provider' : 'Switch to Local Ollama'}
            </Button>
          </div>

          {/* Cloud Groq Card */}
          <div
            onClick={() => handleSwitch('groq')}
            className={cn(
              'relative flex flex-col justify-between p-4 rounded-xl border transition-all cursor-pointer select-none space-y-4',
              isGroq
                ? 'bg-sky-500/10 border-sky-500 ring-1 ring-sky-500/30 shadow-xs'
                : 'bg-surface-secondary border-border-subtle hover:border-border-muted hover:bg-surface-secondary/80'
            )}
          >
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={cn(
                    'p-2 rounded-lg',
                    isGroq ? 'bg-sky-500/20 text-sky-400' : 'bg-surface-tertiary text-content-secondary'
                  )}>
                    <Cloud className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-content-primary">Cloud — Groq</h4>
                    <span className="text-[10px] text-content-muted">Temporary Remote Inference</span>
                  </div>
                </div>
                {isGroq && (
                  <span className="flex items-center gap-1 text-[11px] font-semibold text-sky-400">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Active
                  </span>
                )}
              </div>

              <div className="space-y-1 text-xs text-content-secondary pt-1">
                <div className="flex justify-between py-0.5 border-b border-border-subtle/50 text-[11px]">
                  <span className="text-content-muted">Generation:</span>
                  <span className="font-mono font-medium text-sky-300">
                    {providerSettings?.generation_model || 'qwen/qwen3.8-27b'}
                  </span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-border-subtle/50 text-[11px]">
                  <span className="text-content-muted">Embeddings:</span>
                  <span className="font-mono font-medium text-content-primary">Local nomic-embed (768d)</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-border-subtle/50 text-[11px]">
                  <span className="text-content-muted">Network:</span>
                  <span className="font-medium text-sky-400">HTTPS API Required</span>
                </div>
                <div className="flex justify-between py-0.5 text-[11px]">
                  <span className="text-content-muted">RAM Relieved:</span>
                  <span className="font-medium text-emerald-500">Zero Generation RAM</span>
                </div>
              </div>
            </div>

            <Button
              type="button"
              variant={isGroq ? 'primary' : 'secondary'}
              size="sm"
              className={cn('w-full text-xs font-medium', isGroq && 'bg-sky-600 hover:bg-sky-500 text-white')}
              disabled={isGroq || switchMutation.isPending || !providerSettings?.groq_configured}
              isLoading={switchMutation.isPending && switchMutation.variables === 'groq'}
            >
              {isGroq
                ? 'Active Provider'
                : providerSettings?.groq_configured
                  ? 'Switch to Groq'
                  : 'API Key Missing'}
            </Button>
          </div>
        </div>

        {/* Backend .env Setup Instructions if Groq unconfigured */}
        {!providerSettings?.groq_configured && (
          <div className="p-3.5 rounded-xl bg-surface-secondary border border-border-subtle flex items-start gap-3 text-xs">
            <KeyRound className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-semibold text-content-primary block">
                How to configure Groq credentials safely
              </span>
              <p className="text-content-secondary leading-relaxed">
                Add <code className="font-mono text-content-primary">GROQ_API_KEY=your_key_here</code> to your local backend <code className="font-mono text-content-primary">.env</code> file. For security, API keys are never accepted or entered through the browser.
              </p>
            </div>
          </div>
        )}

        {/* Diagnostics & Capabilities Breakdown */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs font-mono">
          <div className="p-2.5 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
            <span className="text-content-muted block font-sans text-[11px]">Active Engine:</span>
            <span className="text-content-primary font-bold capitalize">{activeProvider}</span>
          </div>
          <div className="p-2.5 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
            <span className="text-content-muted block font-sans text-[11px]">Generation Status:</span>
            <span className={cn(
              'font-semibold',
              providerSettings?.provider_health?.available ? 'text-emerald-500' : 'text-amber-500'
            )}>
              {providerSettings?.provider_health?.status || 'Active'}
            </span>
          </div>
          <div className="p-2.5 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
            <span className="text-content-muted block font-sans text-[11px]">Local Embeddings:</span>
            <span className={cn(
              'font-semibold',
              providerSettings?.embedding_available ? 'text-emerald-500' : 'text-rose-500'
            )}>
              {providerSettings?.embedding_available ? 'Connected' : 'Offline'}
            </span>
          </div>
          <div className="p-2.5 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
            <span className="text-content-muted block font-sans text-[11px]">Vector Dimensions:</span>
            <span className="text-content-primary font-semibold">768 Float</span>
          </div>
        </div>
      </Card>

      {/* Visual Appearance & Theme Card */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-border-subtle pb-3">
          <div className="flex items-center gap-2.5">
            <Sun className="w-5 h-5 text-amber-500" />
            <div>
              <h3 className="text-sm font-semibold text-content-primary">Visual Appearance & Design System</h3>
              <p className="text-xs text-content-secondary">Configure workspace theme and contrast mode</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <button
            type="button"
            onClick={() => {
              setTheme('dark');
              toast.info('Dark appearance activated.', { title: 'Theme Updated' });
            }}
            className={cn(
              'flex flex-col items-center gap-2 p-3.5 rounded-xl border transition-all text-xs font-medium',
              theme === 'dark'
                ? 'bg-brand/10 border-brand text-brand-light shadow-xs'
                : 'bg-surface-secondary text-content-secondary border-border-subtle hover:text-content-primary hover:border-border-muted'
            )}
          >
            <Moon className="w-5 h-5" />
            <span>Dark Theme</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setTheme('light');
              toast.info('Light appearance activated.', { title: 'Theme Updated' });
            }}
            className={cn(
              'flex flex-col items-center gap-2 p-3.5 rounded-xl border transition-all text-xs font-medium',
              theme === 'light'
                ? 'bg-brand/10 border-brand text-brand-light shadow-xs'
                : 'bg-surface-secondary text-content-secondary border-border-subtle hover:text-content-primary hover:border-border-muted'
            )}
          >
            <Sun className="w-5 h-5 text-amber-500" />
            <span>Light Theme</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setTheme('system');
              toast.info('System theme synchronized.', { title: 'Theme Updated' });
            }}
            className={cn(
              'flex flex-col items-center gap-2 p-3.5 rounded-xl border transition-all text-xs font-medium',
              theme === 'system'
                ? 'bg-brand/10 border-brand text-brand-light shadow-xs'
                : 'bg-surface-secondary text-content-secondary border-border-subtle hover:text-content-primary hover:border-border-muted'
            )}
          >
            <Laptop className="w-5 h-5" />
            <span>System Default</span>
          </button>
        </div>
      </Card>

      {/* Backend & Database Card */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-border-subtle pb-3">
          <div className="flex items-center gap-2.5">
            <Database className="w-5 h-5 text-brand" />
            <div>
              <h3 className="text-sm font-semibold text-content-primary">Local Backend & Database</h3>
              <p className="text-xs text-content-secondary">FastAPI backend running locally on Windows</p>
            </div>
          </div>
          <StatusBadge
            status={isOnline ? 'healthy' : 'offline'}
            label={isOnline ? 'Active' : 'Unreachable'}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-3 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
            <span className="text-content-muted block font-sans">API Endpoint:</span>
            <span className="text-content-primary font-semibold">http://127.0.0.1:8000</span>
          </div>
          <div className="p-3 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
            <span className="text-content-muted block font-sans">Database Engine:</span>
            {isHealthLoading ? (
              <Skeleton className="h-4 w-32" />
            ) : (
              <span className="text-content-primary font-semibold">{health?.database || 'SQLite (WAL Mode)'}</span>
            )}
          </div>
          <div className="p-3 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
            <span className="text-content-muted block font-sans">Host System Memory (RAM):</span>
            {isHealthLoading ? (
              <Skeleton className="h-4 w-44" />
            ) : (
              <span className="text-content-primary font-semibold">
                {health?.ram_available_gb !== undefined
                  ? `${health.ram_available_gb.toFixed(1)} GB Available / ${health.ram_total_gb?.toFixed(1) || '--'} GB Total (${health.ram_used_percent ?? '--'}% in use)`
                  : '--'}
              </span>
            )}
          </div>
          <div className="p-3 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
            <span className="text-content-muted block font-sans">Host Processor (CPU):</span>
            <span className="text-content-primary font-semibold">
              {health?.cpu_count ? `${health.cpu_count} Logical Cores (Intel Core i7-12650H)` : '16 Logical Cores'}
            </span>
          </div>
          <div className="p-3 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
            <span className="text-content-muted block font-sans">Drive Storage (Disk Space):</span>
            <span className="text-content-primary font-semibold">{health ? `${health.free_disk_gb.toFixed(1)} GB Free on Project Drive` : '--'}</span>
          </div>
          <div className="p-3 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
            <span className="text-content-muted block font-sans">Application:</span>
            <span className="text-content-primary font-semibold">DocuMind v0.2.0 (Dual AI Architecture)</span>
          </div>
        </div>
      </Card>

      {/* Hardware Arbiter & Local Ingestion Protection */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-border-subtle pb-3">
          <div className="flex items-center gap-2.5">
            <Server className="w-5 h-5 text-indigo-500" />
            <div>
              <h3 className="text-sm font-semibold text-content-primary">Hardware Arbiter & Local Concurrency</h3>
              <p className="text-xs text-content-secondary">Local memory floor enforcement and mutual exclusion</p>
            </div>
          </div>
          <StatusBadge
            status={isOllamaConnected ? 'healthy' : 'degraded'}
            label={isOllamaConnected ? 'Arbiter Active' : 'Ollama Offline'}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-3 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
            <span className="text-content-muted block font-sans">Local Arbiter Lock:</span>
            <span className="text-emerald-500 font-semibold">{health?.arbiter_status || 'Idle'} (Single-flight)</span>
          </div>
          <div className="p-3 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
            <span className="text-content-muted block font-sans">Host Environment:</span>
            <span className="text-content-primary font-semibold">Intel Core i7-12650H • 16GB RAM</span>
          </div>
          <div className="p-3 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
            <span className="text-content-muted block font-sans">Embedding Daemon:</span>
            <span className="text-content-primary font-semibold">{isOllamaConnected ? '127.0.0.1:11434 (Ready)' : 'Unreachable'}</span>
          </div>
          <div className="p-3 rounded-lg bg-surface-secondary border border-border-subtle space-y-1">
            <span className="text-content-muted block font-sans">Safety Floor:</span>
            <span className="text-content-primary font-semibold">200 MB Free RAM Minimum</span>
          </div>
        </div>
      </Card>

      {/* Storage & Security Boundary Card */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-border-subtle pb-3">
          <div className="flex items-center gap-2.5">
            <FolderLock className="w-5 h-5 text-emerald-500" />
            <div>
              <h3 className="text-sm font-semibold text-content-primary">Storage & Security Boundary</h3>
              <p className="text-xs text-content-secondary">Path containment enforcement and air-gap integrity</p>
            </div>
          </div>
          <StatusBadge status="completed" label="Secured" />
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary/70 border border-border-subtle space-y-2 text-xs text-content-secondary">
          <div className="flex items-center gap-2 text-emerald-500 font-semibold">
            <ShieldCheck className="w-4 h-4 shrink-0" />
            <span>Path Containment Enforcement Active</span>
          </div>
          <p className="leading-relaxed text-content-muted">
            All document previews and downloads served via <code className="font-mono text-content-primary font-semibold">GET /api/documents/:id/file</code> are strictly verified against the configured upload directory using common-path containment checks. Arbitrary paths outside the uploads directory are rejected with HTTP 400.
          </p>
        </div>
      </Card>

      {/* Privacy, Telemetry & Support Card */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-border-subtle pb-3">
          <div className="flex items-center gap-2.5">
            <Shield className="w-5 h-5 text-brand" />
            <div>
              <h3 className="text-sm font-semibold text-content-primary">Privacy & Data Governance</h3>
              <p className="text-xs text-content-secondary">Zero-cookie guarantee, offline confidentiality, and support</p>
            </div>
          </div>
          <StatusBadge status="completed" label="Privacy Hardened" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-surface-secondary/70 border border-border-subtle space-y-2">
            <div className="flex items-center gap-2 text-content-primary font-semibold text-xs">
              <EyeOff className="w-4 h-4 text-emerald-500" />
              <span>100% Cookie-Free Architecture</span>
            </div>
            <p className="text-xs text-content-muted leading-relaxed">
              DocuMind sets zero HTTP tracking cookies or advertising pixels. Essential UI preferences (theme, collapsed sidebar) use strictly whitelisted local browser storage.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-surface-secondary/70 border border-border-subtle space-y-3">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="text-xs font-semibold text-content-primary block">
                  Anonymous Milestone Telemetry
                </span>
                <span className="text-[11px] text-content-muted block">
                  {telemetryEnabled ? 'Enabled (Opt-in active)' : 'Disabled by default'}
                </span>
              </div>
              <Button
                variant={telemetryEnabled ? 'outline' : 'secondary'}
                size="sm"
                onClick={handleToggleTelemetry}
              >
                {telemetryEnabled ? 'Disable' : 'Enable'}
              </Button>
            </div>
            <p className="text-[11px] text-content-muted leading-relaxed">
              Records high-level lifecycle events without payloads. Document contents, queries, citations, and filenames are permanently forbidden.
            </p>
          </div>
        </div>

        {/* Support & Feedback Action */}
        <div className="pt-2 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-t border-border-subtle">
          <div className="text-xs text-content-secondary">
            Need assistance, discovered a bug, or have a suggestion?
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsSupportOpen(true)}
            icon={<HelpCircle className="w-3.5 h-3.5" />}
          >
            Contact Engineering Support
          </Button>
        </div>
      </Card>

      <SupportModal isOpen={isSupportOpen} onClose={() => setIsSupportOpen(false)} />
    </div>
  );
};
