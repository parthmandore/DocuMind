/**
 * Document File Handling Utilities
 *
 * Implements client-side file size formatting, extension extraction,
 * and backend allowlist validation.
 */

export const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024; // 50 MB

export const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.md'];

export function formatFileSize(bytes?: number | null): string {
  if (bytes === undefined || bytes === null || isNaN(bytes)) return '--';
  if (bytes === 0) return '0 B';

  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function getFileExtension(filename: string): string {
  const parts = filename.split('.');
  if (parts.length <= 1) return '';
  return `.${parts[parts.length - 1].toLowerCase()}`;
}

export function isValidDocumentFile(file: File): {
  valid: boolean;
  error?: string;
} {
  const ext = getFileExtension(file.name);

  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return {
      valid: false,
      error: `Unsupported file format "${ext || 'unknown'}". Allowed formats: ${ALLOWED_EXTENSIONS.join(', ')}`,
    };
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return {
      valid: false,
      error: `File size exceeds the 50 MB limit (${formatFileSize(file.size)}).`,
    };
  }

  if (file.size === 0) {
    return {
      valid: false,
      error: 'Empty files cannot be ingested into the repository.',
    };
  }

  return { valid: true };
}
