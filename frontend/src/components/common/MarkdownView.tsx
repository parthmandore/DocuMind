import React from 'react';
import { CitationBadge } from '@/components/document/CitationBadge';
import type { CitationItem, MessageCitationResponse } from '@/types/api';

export interface MarkdownViewProps {
  content: string;
  citations?: (CitationItem | MessageCitationResponse)[];
  onCitationClick?: (citation: any, index: number) => void;
  className?: string;
}

export const MarkdownView: React.FC<MarkdownViewProps> = ({
  content,
  citations = [],
  onCitationClick,
  className = '',
}) => {
  if (!content) return null;

  // Split content into blocks (paragraphs, lists, headers, code blocks)
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBlockBuffer: string[] = [];
  let listBuffer: { type: 'ul' | 'ol'; items: string[] } | null = null;

  const flushList = () => {
    if (!listBuffer) return;
    const ListTag = listBuffer.type;
    elements.push(
      <ListTag
        key={`list-${elements.length}`}
        className={`space-y-1.5 my-2.5 pl-5 ${
          listBuffer.type === 'ul' ? 'list-disc' : 'list-decimal'
        } text-content-primary`}
      >
        {listBuffer.items.map((item, idx) => (
          <li key={idx} className="leading-relaxed">
            {renderInline(item)}
          </li>
        ))}
      </ListTag>
    );
    listBuffer = null;
  };

  const renderInline = (text: string): React.ReactNode => {
    // Regex for inline code, bold, italic, and citation tokens like [P1], [1], [Cit 1]
    const tokenRegex =
      /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[P\d+\]|\[\d+\]|\[Cit\s*\d+\])/g;

    const parts = text.split(tokenRegex);

    return parts.map((part, index) => {
      if (!part) return null;

      // Citation match [P1], [1], [Cit 1]
      const citMatch = part.match(/^\[(?:P|Cit\s*)?(\d+)\]$/i);
      if (citMatch) {
        const citIdx = parseInt(citMatch[1], 10);
        const citation = citations[citIdx - 1];
        return (
          <span key={index} className="inline-block mx-0.5 align-middle">
            <CitationBadge
              index={citIdx}
              documentTitle={
                (citation
                  ? 'document_filename' in citation
                    ? citation.document_filename
                    : citation.document_id
                  : undefined) || undefined
              }
              pageNumber={citation?.page_number}
              isVerified={
                citation
                  ? 'is_verified' in citation
                    ? citation.is_verified
                    : citation.verification_status === 'verified'
                  : true
              }
              onClick={() => onCitationClick?.(citation, citIdx)}
            />
          </span>
        );
      }

      // Bold **text**
      if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
        return (
          <strong key={index} className="font-semibold text-content-primary">
            {part.slice(2, -2)}
          </strong>
        );
      }

      // Italic *text*
      if (part.startsWith('*') && part.endsWith('*') && part.length >= 2) {
        return (
          <em key={index} className="italic text-content-secondary">
            {part.slice(1, -1)}
          </em>
        );
      }

      // Inline code `code`
      if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
        return (
          <code
            key={index}
            className="px-1.5 py-0.5 rounded bg-surface-secondary text-brand-light font-mono text-[12px] border border-border-subtle"
          >
            {part.slice(1, -1)}
          </code>
        );
      }

      return <span key={index}>{part}</span>;
    });
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code block toggle
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <div
            key={`code-${elements.length}`}
            className="my-3 rounded-xl bg-surface-secondary/80 border border-border-subtle p-3.5 overflow-x-auto font-mono text-xs text-content-primary"
          >
            <pre>
              <code>{codeBlockBuffer.join('\n')}</code>
            </pre>
          </div>
        );
        codeBlockBuffer = [];
        inCodeBlock = false;
      } else {
        flushList();
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockBuffer.push(line);
      continue;
    }

    const trimmed = line.trim();

    if (!trimmed) {
      flushList();
      continue;
    }

    // Headers
    if (trimmed.startsWith('# ')) {
      flushList();
      elements.push(
        <h1
          key={`h1-${elements.length}`}
          className="text-xl font-bold text-content-primary mt-4 mb-2 tracking-tight"
        >
          {renderInline(trimmed.slice(2))}
        </h1>
      );
      continue;
    }
    if (trimmed.startsWith('## ')) {
      flushList();
      elements.push(
        <h2
          key={`h2-${elements.length}`}
          className="text-lg font-bold text-content-primary mt-3.5 mb-1.5 tracking-tight"
        >
          {renderInline(trimmed.slice(3))}
        </h2>
      );
      continue;
    }
    if (trimmed.startsWith('### ')) {
      flushList();
      elements.push(
        <h3
          key={`h3-${elements.length}`}
          className="text-base font-semibold text-content-primary mt-3 mb-1 tracking-tight"
        >
          {renderInline(trimmed.slice(4))}
        </h3>
      );
      continue;
    }

    // Unordered lists
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      if (!listBuffer || listBuffer.type !== 'ul') {
        flushList();
        listBuffer = { type: 'ul', items: [] };
      }
      listBuffer.items.push(trimmed.slice(2));
      continue;
    }

    // Ordered lists (e.g. 1. )
    const olMatch = trimmed.match(/^\d+\.\s+(.*)$/);
    if (olMatch) {
      if (!listBuffer || listBuffer.type !== 'ol') {
        flushList();
        listBuffer = { type: 'ol', items: [] };
      }
      listBuffer.items.push(olMatch[1]);
      continue;
    }

    // Normal Paragraph
    flushList();
    elements.push(
      <p
        key={`p-${elements.length}`}
        className="leading-relaxed my-2 text-content-primary text-sm"
      >
        {renderInline(line)}
      </p>
    );
  }

  flushList();

  return <div className={`text-sm ${className}`}>{elements}</div>;
};
