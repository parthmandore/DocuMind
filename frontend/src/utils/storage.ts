/**
 * Local UI Preference Storage Utilities
 *
 * Persists ONLY non-sensitive layout and UI preferences in browser storage.
 * Prohibits persisting raw document text, chunks, embeddings, or private research answers.
 */

export interface UiPreferences {
  sidebarCollapsed: boolean;
  theme: 'dark' | 'light' | 'system';
  splitRatio: number; // For side-by-side evidence viewer (e.g., 0.5)
  lastActiveConversationId: string | null;
}

const STORAGE_KEYS = {
  SIDEBAR_COLLAPSED: 'documind_sidebar_collapsed',
  THEME: 'documind_theme_mode',
  SPLIT_RATIO: 'documind_split_ratio',
  LAST_CONV_ID: 'documind_last_conv_id',
  TELEMETRY_ENABLED: 'documind_telemetry_enabled',
} as const;

// Strict whitelist of permitted storage keys
const ALLOWED_KEYS = new Set<string>(Object.values(STORAGE_KEYS));

// In-memory fallback if localStorage is unavailable (e.g. Node / SSR / private mode)
const memoryStore = new Map<string, string>();

const getStorageItem = (key: string): string | null => {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage.getItem(key);
    }
    if (typeof localStorage !== 'undefined') {
      return localStorage.getItem(key);
    }
  } catch {
    // Ignore and fallback
  }
  return memoryStore.get(key) ?? null;
};

const setStorageItem = (key: string, value: string): void => {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(key, value);
      return;
    }
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(key, value);
      return;
    }
  } catch {
    // Ignore and fallback
  }
  memoryStore.set(key, value);
};

const removeStorageItem = (key: string): void => {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.removeItem(key);
      return;
    }
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(key);
      return;
    }
  } catch {
    // Ignore and fallback
  }
  memoryStore.delete(key);
};

export const storage = {
  /**
   * Retrieves a typed UI preference value from storage.
   */
  get<T>(key: string, defaultValue: T): T {
    if (!ALLOWED_KEYS.has(key)) {
      console.warn(`[DocuMind Storage] Blocked attempt to read non-whitelisted key: "${key}"`);
      return defaultValue;
    }

    try {
      const raw = getStorageItem(key);
      if (raw === null) return defaultValue;
      return JSON.parse(raw) as T;
    } catch {
      return defaultValue;
    }
  },

  /**
   * Saves a typed UI preference value to storage.
   */
  set<T>(key: string, value: T): void {
    if (!ALLOWED_KEYS.has(key)) {
      console.warn(`[DocuMind Storage] Blocked attempt to persist non-whitelisted key: "${key}"`);
      return;
    }

    try {
      setStorageItem(key, JSON.stringify(value));
    } catch (e) {
      console.warn('[DocuMind Storage] Failed to write to storage', e);
    }
  },

  /**
   * Removes a UI preference key.
   */
  remove(key: string): void {
    removeStorageItem(key);
  },

  /**
   * Clears internal memory store (useful for testing).
   */
  clearMemory(): void {
    memoryStore.clear();
  },

  // --- Strongly-typed convenience accessors ---

  getSidebarCollapsed(): boolean {
    return this.get<boolean>(STORAGE_KEYS.SIDEBAR_COLLAPSED, false);
  },

  setSidebarCollapsed(collapsed: boolean): void {
    this.set<boolean>(STORAGE_KEYS.SIDEBAR_COLLAPSED, collapsed);
  },

  getTheme(): 'dark' | 'light' | 'system' {
    return this.get<'dark' | 'light' | 'system'>(STORAGE_KEYS.THEME, 'dark');
  },

  setTheme(theme: 'dark' | 'light' | 'system'): void {
    this.set<'dark' | 'light' | 'system'>(STORAGE_KEYS.THEME, theme);
  },

  getSplitRatio(): number {
    return this.get<number>(STORAGE_KEYS.SPLIT_RATIO, 0.5);
  },

  setSplitRatio(ratio: number): void {
    const clamped = Math.min(Math.max(ratio, 0.2), 0.8);
    this.set<number>(STORAGE_KEYS.SPLIT_RATIO, clamped);
  },

  getLastConversationId(): string | null {
    return this.get<string | null>(STORAGE_KEYS.LAST_CONV_ID, null);
  },

  setLastConversationId(id: string | null): void {
    this.set<string | null>(STORAGE_KEYS.LAST_CONV_ID, id);
  },
};
