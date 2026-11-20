import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  FileQuestion,
  Home,
  FolderOpen,
  Sparkles,
  ArrowLeft,
  Compass,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { useRouteMetadata } from '@/hooks/useRouteMetadata';

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  useRouteMetadata({
    title: 'Page Not Found | DocuMind',
    description: 'The requested page or route does not exist in the DocuMind interface.',
    isPrivate: true,
  });

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center p-6 text-center animate-fade-in">
      <div className="max-w-lg w-full space-y-6">
        {/* Visual Identity / 404 Emblem */}
        <div className="relative mx-auto w-20 h-20 rounded-2xl bg-surface-primary border border-border-subtle shadow-md flex items-center justify-center text-brand">
          <FileQuestion className="w-10 h-10 stroke-[1.5]" />
          <span className="absolute -top-2 -right-2 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-brand text-white shadow-xs">
            404
          </span>
        </div>

        {/* Message */}
        <div className="space-y-2">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-content-primary">
            Page Not Found
          </h1>
          <p className="text-sm text-content-secondary max-w-md mx-auto leading-relaxed">
            The page, route, or document view you requested does not exist or may have been moved.
          </p>
        </div>

        {/* Primary Action Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
          <Button
            variant="secondary"
            size="md"
            onClick={() => navigate(-1)}
            icon={<ArrowLeft className="w-4 h-4" />}
          >
            Go Back
          </Button>

          <Link to="/">
            <Button
              variant="primary"
              size="md"
              icon={<Home className="w-4 h-4" />}
            >
              Back to Dashboard
            </Button>
          </Link>

          <Link to="/documents">
            <Button
              variant="secondary"
              size="md"
              icon={<FolderOpen className="w-4 h-4" />}
            >
              Document Library
            </Button>
          </Link>
        </div>

        {/* Helpful Quick Navigation Card */}
        <Card className="p-4 bg-surface-secondary/50 border-border-subtle text-left space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-content-muted">
            <Compass className="w-3.5 h-3.5 text-brand" />
            <span>Popular Destinations</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            <Link
              to="/documents"
              className="p-2.5 rounded-lg border border-border-subtle bg-surface-primary hover:border-brand/40 hover:bg-surface-secondary transition-colors flex items-center gap-2 text-content-primary font-medium"
            >
              <FolderOpen className="w-4 h-4 text-brand shrink-0" />
              <div>
                <p className="font-semibold">Document Library</p>
                <p className="text-[11px] text-content-muted font-normal">
                  View and upload documents
                </p>
              </div>
            </Link>

            <Link
              to="/research"
              className="p-2.5 rounded-lg border border-border-subtle bg-surface-primary hover:border-brand/40 hover:bg-surface-secondary transition-colors flex items-center gap-2 text-content-primary font-medium"
            >
              <Sparkles className="w-4 h-4 text-brand shrink-0" />
              <div>
                <p className="font-semibold">Research Workspace</p>
                <p className="text-[11px] text-content-muted font-normal">
                  Inquire with grounded citations
                </p>
              </div>
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
};
