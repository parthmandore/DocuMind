import React from 'react';
import { ShieldCheck } from 'lucide-react';
import { cn } from '@/utils/cn';

export interface CitationBadgeProps {
  index?: number | string;
  label?: string;
  pageNumber?: number;
  documentTitle?: string;
  isVerified?: boolean;
  score?: number;
  onClick?: () => void;
  className?: string;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({
  index,
  label,
  pageNumber,
  documentTitle,
  isVerified = true,
  score,
  onClick,
  className,
}) => {
  const displayText =
    label || (index !== undefined ? `[P${index}]` : pageNumber ? `p.${pageNumber}` : '[Cit]');

  const titleTooltip = [
    documentTitle ? `Doc: ${documentTitle}` : '',
    pageNumber ? `Page ${pageNumber}` : '',
    score !== undefined ? `Relevance: ${Math.round(score * 100)}%` : '',
    isVerified ? 'Verified Grounding Claim' : '',
  ]
    .filter(Boolean)
    .join(' • ');

  return (
    <button
      type="button"
      onClick={onClick}
      title={titleTooltip}
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 min-h-[28px] rounded-md text-[11px] font-mono font-medium border transition-all duration-120 ease-standard cursor-pointer select-none active:scale-[0.93] transform-gpu',
        'bg-brand/10 text-brand border-brand/30 hover:bg-brand/20 hover:border-brand/60 hover:-translate-y-0.5 hover:shadow-sm hover:shadow-brand/15',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-1 focus-visible:ring-offset-app',
        className
      )}
    >
      <span>{displayText}</span>
      {isVerified && (
        <ShieldCheck className="w-3 h-3 text-brand shrink-0" aria-label="Verified citation" />
      )}
    </button>
  );
};
