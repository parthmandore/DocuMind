/**
 * Document Upload Modal with Drag-and-Drop & Queue Management (Phase 5.5)
 *
 * Implements client-side validation (.pdf, .docx, .txt, .md, <=50MB),
 * multi-file queuing, duplicate SHA-256 feedback, and non-corrupting error handling.
 */

import React, { useState, useRef, useCallback } from 'react';
import {
  UploadCloud,
  FileText,
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Trash2,
} from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { Badge } from '@/components/ui/Badge';
import { useUploadDocument } from '@/hooks/useMutations';
import {
  isValidDocumentFile,
  formatFileSize,
  ALLOWED_EXTENSIONS,
} from '@/utils/file';
import { formatError } from '@/utils/errors';
import { useToast } from '@/hooks/useToast';

export interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

interface QueuedFile {
  id: string;
  file: File;
  status: 'queued' | 'uploading' | 'completed' | 'duplicate' | 'error';
  errorMessage?: string;
  duplicateMessage?: string;
}

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [queue, setQueue] = useState<QueuedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessingQueue, setIsProcessingQueue] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadMutation = useUploadDocument();
  const toast = useToast();

  const handleFilesAdded = useCallback((newFiles: FileList | File[]) => {
    const fileArray = Array.from(newFiles);
    const validEntries: QueuedFile[] = [];

    fileArray.forEach((file) => {
      const validation = isValidDocumentFile(file);
      const queueItem: QueuedFile = {
        id: `${file.name}-${file.size}-${Date.now()}-${Math.random()}`,
        file,
        status: validation.valid ? 'queued' : 'error',
        errorMessage: validation.error,
      };
      validEntries.push(queueItem);
    });

    setQueue((prev) => [...prev, ...validEntries]);
  }, []);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesAdded(e.dataTransfer.files);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFilesAdded(e.target.files);
    }
    // Reset file input so identical file can be selected again if removed
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleRemoveItem = (id: string) => {
    if (isProcessingQueue) return;
    setQueue((prev) => prev.filter((item) => item.id !== id));
  };

  const handleStartUpload = async () => {
    const itemsToUpload = queue.filter((item) => item.status === 'queued');
    if (itemsToUpload.length === 0 || isProcessingQueue) return;

    setIsProcessingQueue(true);

    let hasSuccess = false;

    for (const item of itemsToUpload) {
      // Mark current item uploading
      setQueue((prev) =>
        prev.map((q) => (q.id === item.id ? { ...q, status: 'uploading' } : q))
      );

      try {
        const response = await uploadMutation.mutateAsync(item.file);
        hasSuccess = true;

        if (response.is_duplicate) {
          toast.warning(
            response.message || `Document "${item.file.name}" is already indexed (duplicate hash).`,
            { title: 'Duplicate Document' }
          );
        } else {
          toast.success(
            `"${item.file.name}" uploaded successfully. Ingestion pipeline started.`,
            { title: 'Document Uploaded' }
          );
        }

        setQueue((prev) =>
          prev.map((q) => {
            if (q.id === item.id) {
              if (response.is_duplicate) {
                return {
                  ...q,
                  status: 'duplicate',
                  duplicateMessage:
                    response.message ||
                    'Matching SHA-256 hash already exists in repository.',
                };
              }
              return {
                ...q,
                status: 'completed',
              };
            }
            return q;
          })
        );
      } catch (err) {
        const errObj = formatError(err);
        toast.error(`Failed to upload "${item.file.name}": ${errObj.message}`, {
          title: 'Upload Failed',
        });
        setQueue((prev) =>
          prev.map((q) =>
            q.id === item.id
              ? {
                  ...q,
                  status: 'error',
                  errorMessage: errObj.message,
                }
              : q
          )
        );
      }
    }

    setIsProcessingQueue(false);
    if (hasSuccess && onSuccess) {
      onSuccess();
    }
  };

  const handleClose = () => {
    if (isProcessingQueue) return;
    setQueue([]);
    onClose();
  };

  const pendingCount = queue.filter((i) => i.status === 'queued').length;
  const completedCount = queue.filter(
    (i) => i.status === 'completed' || i.status === 'duplicate'
  ).length;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Upload Documents"
      description="Add documents to your local DocuMind repository for extraction and semantic indexing."
      size="lg"
      footer={
        <div className="flex items-center justify-between w-full">
          <div className="text-xs text-content-muted">
            {queue.length > 0 && (
              <span>
                {completedCount} of {queue.length} processed
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleClose}
              disabled={isProcessingQueue}
            >
              {completedCount > 0 && pendingCount === 0 ? 'Close' : 'Cancel'}
            </Button>
            {pendingCount > 0 && (
              <Button
                variant="primary"
                size="sm"
                onClick={handleStartUpload}
                isLoading={isProcessingQueue}
                icon={<UploadCloud className="w-4 h-4" />}
              >
                Upload {pendingCount} {pendingCount === 1 ? 'File' : 'Files'}
              </Button>
            )}
          </div>
        </div>
      }
    >
      <div className="space-y-5">
        {/* Drag and Drop Dropzone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-180 ease-standard select-none transform-gpu ${
            isDragging
              ? 'border-brand bg-brand/10 scale-[0.985] shadow-inner shadow-brand/10'
              : 'border-border-muted hover:border-brand/60 hover:bg-surface-secondary/50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={ALLOWED_EXTENSIONS.join(',')}
            onChange={handleFileInputChange}
            className="hidden"
          />

          <div className="flex flex-col items-center justify-center space-y-3 pointer-events-none">
            <div className="w-12 h-12 rounded-full bg-brand/10 border border-brand/20 flex items-center justify-center text-brand transition-transform duration-150">
              <UploadCloud className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-semibold text-content-primary">
                Drag and drop files here, or{' '}
                <span className="text-brand underline">browse</span>
              </p>
              <p className="text-xs text-content-muted">
                Supported: PDF, DOCX, TXT, MD • Maximum 50 MB per file
              </p>
            </div>
          </div>
        </div>

        {/* Upload Queue List */}
        {queue.length > 0 && (
          <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
            <div className="flex items-center justify-between text-xs font-semibold text-content-muted uppercase tracking-wider px-1">
              <span>File Queue ({queue.length})</span>
              {!isProcessingQueue && (
                <button
                  onClick={() => setQueue([])}
                  className="hover:text-status-error transition-colors px-2 py-1 min-h-[32px] rounded active:scale-95 text-xs font-semibold"
                >
                  Clear all
                </button>
              )}
            </div>

            <div className="space-y-2">
              {queue.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-3 rounded-lg border border-border-subtle bg-surface-secondary/50 text-xs transition-all duration-150 hover:bg-surface-secondary/80"
                >
                  <div className="flex items-center gap-3 min-w-0 flex-1 mr-3">
                    <FileText className="w-4 h-4 text-brand shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-content-primary truncate">
                        {item.file.name}
                      </p>
                      <p className="text-content-muted text-[11px]">
                        {formatFileSize(item.file.size)}
                      </p>
                    </div>
                  </div>

                  {/* Status Indicator with Settle Animation */}
                  <div className="flex items-center gap-2 shrink-0">
                    {item.status === 'queued' && (
                      <Badge variant="neutral">Ready</Badge>
                    )}
                    {item.status === 'uploading' && (
                      <Badge variant="processing">
                        <Loader2 className="w-3 h-3 animate-spin mr-1 inline" />
                        Uploading...
                      </Badge>
                    )}
                    {item.status === 'completed' && (
                      <Badge variant="success" className="animate-settle">
                        <CheckCircle2 className="w-3 h-3 mr-1 inline" />
                        Scheduled
                      </Badge>
                    )}
                    {item.status === 'duplicate' && (
                      <Badge variant="warning">
                        <AlertTriangle className="w-3 h-3 mr-1 inline" />
                        Duplicate
                      </Badge>
                    )}
                    {item.status === 'error' && (
                      <Badge variant="error" className="animate-shake-error">
                        <AlertCircle className="w-3 h-3 mr-1 inline" />
                        Rejected
                      </Badge>
                    )}

                    {!isProcessingQueue && item.status !== 'uploading' && (
                      <button
                        onClick={() => handleRemoveItem(item.id)}
                        className="min-w-[36px] min-h-[36px] p-2 flex items-center justify-center rounded-lg text-content-muted hover:text-status-error hover:bg-surface-elevated transition-colors active:scale-95"
                        title="Remove file"
                        aria-label={`Remove ${item.file.name}`}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Error / Warning Details */}
            {queue.some((i) => i.errorMessage || i.duplicateMessage) && (
              <div className="space-y-1.5 pt-2">
                {queue
                  .filter((i) => i.errorMessage)
                  .map((i) => (
                    <Alert
                      key={i.id}
                      variant="error"
                      title={i.file.name}
                      icon={<AlertCircle className="w-4 h-4" />}
                    >
                      {i.errorMessage}
                    </Alert>
                  ))}
                {queue
                  .filter((i) => i.duplicateMessage)
                  .map((i) => (
                    <Alert
                      key={i.id}
                      variant="warning"
                      title={i.file.name}
                      icon={<AlertTriangle className="w-4 h-4" />}
                    >
                      {i.duplicateMessage}
                    </Alert>
                  ))}
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
};
