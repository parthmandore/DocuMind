/**
 * Privacy-Preserving Telemetry & Milestone Tracking
 *
 * Strict Privacy Contract:
 * 1. Opt-in only: Disabled by default. Zero data transmission unless explicitly enabled.
 * 2. High-level product milestones only (e.g., 'first_document_uploaded', 'first_query_executed').
 * 3. STRICTLY FORBIDS persisting or transmitting:
 *    - Document contents, excerpts, or full texts
 *    - Document filenames or storage paths
 *    - Research queries, prompts, or conversation history
 *    - Model reasoning traces or citations
 *    - User credentials, API keys, or tokens
 */

import { storage } from '@/utils/storage';

export type MilestoneEvent =
  | 'first_document_uploaded'
  | 'first_query_executed'
  | 'onboarding_completed'
  | 'theme_toggled'
  | 'support_submitted'
  | 'provider_switched';

export interface TelemetryRecord {
  event: MilestoneEvent;
  timestamp: number;
  metadata?: Record<string, string | number | boolean>;
}

// Prohibited keys that MUST NEVER appear in any telemetry payload
const FORBIDDEN_PAYLOAD_KEYS = new Set([
  'text',
  'content',
  'query',
  'prompt',
  'document',
  'filename',
  'path',
  'citation',
  'quote',
  'key',
  'token',
  'secret',
  'password',
  'email',
  'name',
]);

const TELEMETRY_STORAGE_KEY = 'documind_telemetry_enabled';

class TelemetryService {
  private inMemoryQueue: TelemetryRecord[] = [];

  /**
   * Checks whether telemetry collection is active.
   * Default: FALSE (privacy-first opt-in).
   */
  public isEnabled(): boolean {
    return storage.get<boolean>(TELEMETRY_STORAGE_KEY, false);
  }

  /**
   * Updates user consent for milestone telemetry.
   */
  public setEnabled(enabled: boolean): void {
    storage.set<boolean>(TELEMETRY_STORAGE_KEY, enabled);
    if (!enabled) {
      this.inMemoryQueue = [];
    }
  }

  /**
   * Records a product milestone event, sanitizing all metadata to ensure zero data leakage.
   */
  public trackMilestone(
    event: MilestoneEvent,
    metadata?: Record<string, string | number | boolean>
  ): boolean {
    if (!this.isEnabled()) {
      return false;
    }

    // Sanitize metadata: strip any fields that could carry confidential data
    const sanitizedMeta: Record<string, string | number | boolean> = {};
    if (metadata) {
      for (const [key, value] of Object.entries(metadata)) {
        const lowerKey = key.toLowerCase();
        const hasForbiddenSub = Array.from(FORBIDDEN_PAYLOAD_KEYS).some((f) =>
          lowerKey.includes(f)
        );

        if (hasForbiddenSub) {
          console.warn(
            `[DocuMind Privacy] Telemetry rejected confidential field: "${key}"`
          );
          continue;
        }

        // Only allow primitives
        if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
          sanitizedMeta[key] = value;
        }
      }
    }

    const record: TelemetryRecord = {
      event,
      timestamp: Date.now(),
      metadata: Object.keys(sanitizedMeta).length > 0 ? sanitizedMeta : undefined,
    };

    this.inMemoryQueue.push(record);
    // Keep max 50 milestone records in local session
    if (this.inMemoryQueue.length > 50) {
      this.inMemoryQueue.shift();
    }

    return true;
  }

  /**
   * Returns buffered milestone records for inspection / verification.
   */
  public getRecordedMilestones(): ReadonlyArray<TelemetryRecord> {
    return [...this.inMemoryQueue];
  }

  /**
   * Clears in-memory milestone records.
   */
  public clear(): void {
    this.inMemoryQueue = [];
  }
}

export const telemetry = new TelemetryService();
