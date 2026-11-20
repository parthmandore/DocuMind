import React, { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Select } from '@/components/ui/Select';
import { Alert } from '@/components/ui/Alert';
import { useToast } from '@/context/ToastContext';
import { supportApi } from '@/services/api';
import { telemetry } from '@/services/telemetry';
import { Send, CheckCircle2 } from 'lucide-react';
import type { ContactRequest } from '@/types/api';

export interface SupportModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SupportModal: React.FC<SupportModalProps> = ({ isOpen, onClose }) => {
  const toast = useToast();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [category, setCategory] = useState<'bug' | 'feedback' | 'feature' | 'general'>('feedback');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [website, setWebsite] = useState(''); // Anti-spam honeypot
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submittedRef, setSubmittedRef] = useState<string | null>(null);

  const resetForm = () => {
    setName('');
    setEmail('');
    setCategory('feedback');
    setSubject('');
    setMessage('');
    setWebsite('');
    setErrorMessage(null);
    setSubmittedRef(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    // Basic frontend validation
    if (!name.trim()) {
      setErrorMessage('Please provide your name.');
      return;
    }
    if (!email.trim() || !email.includes('@') || !email.includes('.')) {
      setErrorMessage('Please provide a valid email address.');
      return;
    }
    if (!subject.trim() || subject.trim().length < 3) {
      setErrorMessage('Subject must be at least 3 characters.');
      return;
    }
    if (!message.trim() || message.trim().length < 10) {
      setErrorMessage('Message must be at least 10 characters.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: ContactRequest = {
        name: name.trim(),
        email: email.trim(),
        category,
        subject: subject.trim(),
        message: message.trim(),
        website: website.trim() || undefined,
      };

      const res = await supportApi.submitContact(payload);
      setSubmittedRef(res.reference_id);
      toast.success(`Your message was logged under ticket #${res.reference_id}.`, {
        title: 'Feedback Received',
      });

      // Record milestone telemetry if enabled (strictly without payloads)
      telemetry.trackMilestone('support_submitted');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit message. Please try again.';
      setErrorMessage(msg);
      toast.error(msg, {
        title: 'Submission Failed',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Contact & Engineering Support"
      description="Report an issue, request a capability, or share product feedback directly with the team."
      size="md"
    >
      {submittedRef ? (
        <div className="py-6 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-500 mx-auto flex items-center justify-center">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-content-primary">
              Submission Received
            </h3>
            <p className="text-xs text-content-secondary max-w-sm mx-auto">
              Your report has been securely registered with ticket reference:
            </p>
            <div className="inline-block mt-2 font-mono text-sm font-semibold bg-surface-secondary px-3 py-1 rounded-md border border-border-subtle text-brand">
              #{submittedRef}
            </div>
          </div>
          <p className="text-xs text-content-muted">
            All submitted details remain confidential and are processed according to our local data handling policies.
          </p>
          <div className="pt-2">
            <Button variant="outline" size="sm" onClick={handleClose}>
              Close Dialog
            </Button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {errorMessage && (
            <Alert variant="error" title="Submission Error">
              {errorMessage}
            </Alert>
          )}

          {/* Anti-spam honeypot - hidden from real users */}
          <div className="hidden" aria-hidden="true">
            <label htmlFor="support-website">Website</label>
            <input
              id="support-website"
              type="text"
              name="website"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              tabIndex={-1}
              autoComplete="off"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              id="support-name"
              label="Your Name"
              placeholder="e.g. Jane Doe"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              disabled={isSubmitting}
            />
            <Input
              id="support-email"
              type="email"
              label="Email Address"
              placeholder="jane@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={isSubmitting}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="sm:col-span-1">
              <Select
                id="support-category"
                label="Category"
                value={category}
                onChange={(e) =>
                  setCategory(e.target.value as 'bug' | 'feedback' | 'feature' | 'general')
                }
                options={[
                  { value: 'feedback', label: 'Feedback' },
                  { value: 'bug', label: 'Bug Report' },
                  { value: 'feature', label: 'Feature Request' },
                  { value: 'general', label: 'General Inquiry' },
                ]}
                disabled={isSubmitting}
              />
            </div>
            <div className="sm:col-span-2">
              <Input
                id="support-subject"
                label="Subject"
                placeholder="Brief summary of topic..."
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                required
                disabled={isSubmitting}
              />
            </div>
          </div>

          <Textarea
            id="support-message"
            label="Message Details"
            placeholder="Describe the issue, workflow context, or suggestion in detail..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={4}
            required
            disabled={isSubmitting}
          />

          <p className="text-[11px] text-content-muted leading-relaxed">
            Privacy Guarantee: We do not log full document extracts or private retrieval vectors with support submissions.
          </p>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border-subtle">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
              icon={<Send className="w-3.5 h-3.5" />}
            >
              Submit Feedback
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
};
