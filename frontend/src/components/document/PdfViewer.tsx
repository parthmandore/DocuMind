/**
 * Mozilla PDF.js Document Viewer (Phase 5.5)
 *
 * Professional PDF inspection featuring:
 * - Canvas rendering with HiDPI device-pixel-ratio scaling
 * - Selectable, aligned HTML text layer
 * - Citation-based coordinate highlighting with PyMuPDF top-left mapping
 * - Verified vs partial support visual distinction
 * - Page navigation, thumbnail drawer, zoom & fit controls
 * - Resource cleanup and render cancellation
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCw,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  CheckCircle2,
  AlertTriangle,
  X,
  FileText,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { pdfjsLib } from '@/utils/pdfWorker';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Alert } from '@/components/ui/Alert';
import { documentsApi } from '@/services/api';
import 'pdfjs-dist/web/pdf_viewer.css';

export interface CitationHighlightInfo {
  pageNumber: number;
  bbox?: {
    x0?: number;
    y0?: number;
    x1?: number;
    y1?: number;
    page?: number;
  } | null;
  quote?: string;
  isVerified?: boolean;
  groundingScore?: number;
  claimText?: string;
}

export interface PdfViewerProps {
  documentId: string;
  documentTitle?: string;
  initialPage?: number;
  activeCitation?: CitationHighlightInfo | null;
  onDismissCitation?: () => void;
  className?: string;
}

export const PdfViewer: React.FC<PdfViewerProps> = ({
  documentId,
  documentTitle,
  initialPage = 1,
  activeCitation,
  onDismissCitation,
  className = '',
}) => {
  // PDF Document State
  const [pdfDoc, setPdfDoc] = useState<any>(null);
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(initialPage);
  const [scale, setScale] = useState<number>(1.25);
  const [rotation, setRotation] = useState<number>(0);
  const [isLoadingPdf, setIsLoadingPdf] = useState<boolean>(true);
  const [isRenderingPage, setIsRenderingPage] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Page dimensions (for coordinate transformation)
  const [pageSize, setPageSize] = useState<{ width: number; height: number }>({
    width: 612,
    height: 792,
  });

  // Sidebar Layout State
  const [showThumbnails, setShowThumbnails] = useState<boolean>(false);
  const [showCitationDetails, setShowCitationDetails] = useState<boolean>(true);

  // DOM Refs
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const textLayerRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const renderTaskRef = useRef<any>(null);

  // ---------------------------------------------------------------------------
  // 1. Load PDF Document from Local Backend
  // ---------------------------------------------------------------------------
  const loadPdf = useCallback(async () => {
    setIsLoadingPdf(true);
    setLoadError(null);

    try {
      const fileUrl = documentsApi.getFileUrl(documentId);
      const loadingTask = pdfjsLib.getDocument({
        url: fileUrl,
        withCredentials: false,
      });

      const loadedDoc = await loadingTask.promise;
      setPdfDoc(loadedDoc);
      setNumPages(loadedDoc.numPages);
      setIsLoadingPdf(false);
    } catch (err: any) {
      console.error('Failed to load PDF:', err);
      setLoadError(
        err?.message || 'Unable to load PDF document from the local repository.'
      );
      setIsLoadingPdf(false);
    }
  }, [documentId]);

  useEffect(() => {
    loadPdf();
    return () => {
      if (renderTaskRef.current) {
        try {
          renderTaskRef.current.cancel();
        } catch {}
      }
    };
  }, [loadPdf]);

  // Handle citation navigation
  useEffect(() => {
    if (activeCitation?.pageNumber && activeCitation.pageNumber > 0) {
      setCurrentPage(activeCitation.pageNumber);
    }
  }, [activeCitation]);

  // ---------------------------------------------------------------------------
  // 2. Render Target Page (Canvas + TextLayer)
  // ---------------------------------------------------------------------------
  const renderPage = useCallback(
    async (pageNum: number) => {
      if (!pdfDoc || !canvasRef.current || pageNum < 1 || pageNum > numPages) {
        return;
      }

      // Cancel any ongoing rendering task to prevent canvas collision
      if (renderTaskRef.current) {
        try {
          renderTaskRef.current.cancel();
        } catch {}
      }

      setIsRenderingPage(true);

      try {
        const page = await pdfDoc.getPage(pageNum);
        const canvas = canvasRef.current;
        if (!canvas) return;

        const context = canvas.getContext('2d');
        if (!context) return;

        // Unscaled viewport gives canonical PDF points dimensions
        const baseViewport = page.getViewport({ scale: 1.0, rotation });
        setPageSize({ width: baseViewport.width, height: baseViewport.height });

        // Device Pixel Ratio scaling for Retina / HiDPI sharp rendering
        const dpr = window.devicePixelRatio || 1;
        const viewport = page.getViewport({ scale, rotation });

        canvas.width = Math.floor(viewport.width * dpr);
        canvas.height = Math.floor(viewport.height * dpr);
        canvas.style.width = `${Math.floor(viewport.width)}px`;
        canvas.style.height = `${Math.floor(viewport.height)}px`;

        context.setTransform(dpr, 0, 0, dpr, 0, 0);

        // Render Canvas
        const renderContext = {
          canvasContext: context,
          viewport: viewport,
        };

        const renderTask = page.render(renderContext);
        renderTaskRef.current = renderTask;
        await renderTask.promise;

        // Render Text Layer
        if (textLayerRef.current) {
          textLayerRef.current.innerHTML = '';
          textLayerRef.current.style.width = `${Math.floor(viewport.width)}px`;
          textLayerRef.current.style.height = `${Math.floor(viewport.height)}px`;

          try {
            // PDF.js v4 TextLayer constructor
            const TextLayerClass = (pdfjsLib as any).TextLayer;
            if (TextLayerClass) {
              const textLayer = new TextLayerClass({
                textContentSource: page.streamTextContent
                  ? page.streamTextContent()
                  : await page.getTextContent(),
                container: textLayerRef.current,
                viewport: viewport,
              });
              await textLayer.render();
            }
          } catch (textErr) {
            // Text layer failure is non-fatal; canvas remains readable
            console.debug('TextLayer render warning:', textErr);
          }
        }

        setIsRenderingPage(false);
      } catch (err: any) {
        if (err?.name !== 'RenderingCancelledException') {
          console.error('Page render error:', err);
        }
        setIsRenderingPage(false);
      }
    },
    [pdfDoc, numPages, scale, rotation]
  );

  useEffect(() => {
    if (pdfDoc && currentPage >= 1 && currentPage <= numPages) {
      renderPage(currentPage);
    }
  }, [pdfDoc, currentPage, scale, rotation, renderPage]);

  // ---------------------------------------------------------------------------
  // 3. Zoom & Fit Controls
  // ---------------------------------------------------------------------------
  const handleZoomIn = () => setScale((s) => Math.min(3.0, s + 0.2));
  const handleZoomOut = () => setScale((s) => Math.max(0.5, s - 0.2));
  const handleResetZoom = () => setScale(1.0);

  const handleFitToWidth = () => {
    if (!containerRef.current || !pageSize.width) return;
    const availableWidth = containerRef.current.clientWidth - 48; // padding
    const calculatedScale = Math.max(0.5, availableWidth / pageSize.width);
    setScale(parseFloat(calculatedScale.toFixed(2)));
  };

  const handleRotate = () => {
    setRotation((r) => (r + 90) % 360);
  };

  const handlePageChange = (delta: number) => {
    const next = currentPage + delta;
    if (next >= 1 && next <= numPages) {
      setCurrentPage(next);
    }
  };

  const handlePageInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(e.target.value, 10);
    if (!isNaN(val) && val >= 1 && val <= numPages) {
      setCurrentPage(val);
    }
  };

  // ---------------------------------------------------------------------------
  // 4. Citation Coordinate Mapping (Rotation-Aware 0°, 90°, 180°, 270°)
  // ---------------------------------------------------------------------------
  const isCitationActiveOnCurrentPage =
    activeCitation &&
    activeCitation.pageNumber === currentPage &&
    activeCitation.bbox &&
    activeCitation.bbox.x0 !== undefined &&
    activeCitation.bbox.y0 !== undefined &&
    activeCitation.bbox.x1 !== undefined &&
    activeCitation.bbox.y1 !== undefined;

  let highlightStyle: React.CSSProperties | undefined = undefined;

  if (isCitationActiveOnCurrentPage && pageSize.width && pageSize.height) {
    const x0 = activeCitation!.bbox!.x0!;
    const y0 = activeCitation!.bbox!.y0!;
    const x1 = activeCitation!.bbox!.x1!;
    const y1 = activeCitation!.bbox!.y1!;

    // Derive canonical unrotated page dimensions (W, H)
    const isSideways = rotation === 90 || rotation === 270;
    const origW = isSideways ? pageSize.height : pageSize.width;
    const origH = isSideways ? pageSize.width : pageSize.height;

    let leftPct = 0;
    let topPct = 0;
    let widthPct = 0;
    let heightPct = 0;

    switch (rotation) {
      case 90:
        // 90° Clockwise: (x, y) -> (H - y, x). Rotated canvas size: H x W
        leftPct = ((origH - y1) / origH) * 100;
        topPct = (x0 / origW) * 100;
        widthPct = ((y1 - y0) / origH) * 100;
        heightPct = ((x1 - x0) / origW) * 100;
        break;
      case 180:
        // 180°: (x, y) -> (W - x, H - y). Rotated canvas size: W x H
        leftPct = ((origW - x1) / origW) * 100;
        topPct = ((origH - y1) / origH) * 100;
        widthPct = ((x1 - x0) / origW) * 100;
        heightPct = ((y1 - y0) / origH) * 100;
        break;
      case 270:
        // 270° Clockwise: (x, y) -> (y, W - x). Rotated canvas size: H x W
        leftPct = (y0 / origH) * 100;
        topPct = ((origW - x1) / origW) * 100;
        widthPct = ((y1 - y0) / origH) * 100;
        heightPct = ((x1 - x0) / origW) * 100;
        break;
      case 0:
      default:
        // Canonical unrotated 0°
        leftPct = (x0 / origW) * 100;
        topPct = (y0 / origH) * 100;
        widthPct = ((x1 - x0) / origW) * 100;
        heightPct = ((y1 - y0) / origH) * 100;
        break;
    }

    highlightStyle = {
      position: 'absolute',
      left: `${leftPct}%`,
      top: `${topPct}%`,
      width: `${widthPct}%`,
      height: `${heightPct}%`,
      pointerEvents: 'none',
    };
  }

  return (
    <div
      className={`flex flex-col h-full bg-surface-secondary/40 border border-border-subtle rounded-xl overflow-hidden ${className}`}
    >
      {/* ----------------------------------------------------------------- */}
      {/* Top Toolbar                                                       */}
      {/* ----------------------------------------------------------------- */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-surface-primary border-b border-border-subtle text-xs gap-3 flex-wrap">
        {/* Left: Sidebar Toggle & Page Navigation */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowThumbnails((v) => !v)}
            title={showThumbnails ? 'Hide page list' : 'Show page list'}
            icon={
              showThumbnails ? (
                <PanelLeftClose className="w-4 h-4" />
              ) : (
                <PanelLeftOpen className="w-4 h-4" />
              )
            }
          />

          <div className="h-4 w-px bg-border-subtle mx-1" />

          <Button
            variant="ghost"
            size="sm"
            onClick={() => handlePageChange(-1)}
            disabled={currentPage <= 1 || isLoadingPdf}
            icon={<ChevronLeft className="w-4 h-4" />}
            title="Previous page"
          />

          <div className="flex items-center gap-1.5 font-medium">
            <input
              type="number"
              min={1}
              max={numPages || 1}
              value={currentPage}
              onChange={handlePageInput}
              disabled={isLoadingPdf}
              className="w-12 text-center py-1 px-1 rounded border border-border-subtle bg-surface-secondary text-content-primary focus:outline-none focus:border-brand font-mono text-xs"
            />
            <span className="text-content-muted">/ {numPages || '--'}</span>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => handlePageChange(1)}
            disabled={currentPage >= numPages || isLoadingPdf}
            icon={<ChevronRight className="w-4 h-4" />}
            title="Next page"
          />
        </div>

        {/* Center: Title / Current Status */}
        <div className="hidden md:flex items-center gap-2 text-content-secondary truncate max-w-xs lg:max-w-md">
          <FileText className="w-3.5 h-3.5 text-brand shrink-0" />
          <span className="truncate font-medium">
            {documentTitle || 'Document Preview'}
          </span>
          {isRenderingPage && (
            <Loader2 className="w-3 h-3 text-brand animate-spin shrink-0" />
          )}
        </div>

        {/* Right: Zoom & Layout Controls */}
        <div className="flex items-center gap-1.5">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleZoomOut}
            disabled={scale <= 0.5 || isLoadingPdf}
            icon={<ZoomOut className="w-4 h-4" />}
            title="Zoom out"
          />

          <button
            onClick={handleResetZoom}
            className="px-2 py-1 rounded text-content-secondary hover:text-content-primary hover:bg-surface-hover font-mono text-xs"
            title="Reset to 100%"
          >
            {Math.round(scale * 100)}%
          </button>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleZoomIn}
            disabled={scale >= 3.0 || isLoadingPdf}
            icon={<ZoomIn className="w-4 h-4" />}
            title="Zoom in"
          />

          <Button
            variant="ghost"
            size="sm"
            onClick={handleFitToWidth}
            disabled={isLoadingPdf}
            icon={<Maximize2 className="w-3.5 h-3.5" />}
            title="Fit to width"
          />

          <Button
            variant="ghost"
            size="sm"
            onClick={handleRotate}
            disabled={isLoadingPdf}
            icon={<RotateCw className="w-3.5 h-3.5" />}
            title="Rotate 90 degrees"
          />

          {activeCitation && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowCitationDetails((v) => !v)}
              className={showCitationDetails ? 'text-brand' : ''}
              icon={
                showCitationDetails ? (
                  <PanelRightClose className="w-4 h-4" />
                ) : (
                  <PanelRightOpen className="w-4 h-4" />
                )
              }
              title="Toggle citation sidebar"
            />
          )}
        </div>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Active Citation Notification Banner                              */}
      {/* ----------------------------------------------------------------- */}
      {activeCitation && (
        <div className="bg-surface-elevated border-b border-border-subtle px-4 py-2 flex items-center justify-between text-xs gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            {activeCitation.isVerified ? (
              <Badge variant="success">
                <CheckCircle2 className="w-3 h-3 mr-1 inline" />
                Verified Citation
              </Badge>
            ) : (
              <Badge variant="warning">
                <AlertTriangle className="w-3 h-3 mr-1 inline" />
                Partial Support
              </Badge>
            )}
            <span className="font-medium text-content-primary truncate">
              Cited on Page {activeCitation.pageNumber}
            </span>
            {activeCitation.quote && (
              <span className="text-content-secondary italic truncate max-w-md hidden sm:inline">
                "{activeCitation.quote}"
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {activeCitation.pageNumber !== currentPage && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(activeCitation.pageNumber)}
              >
                Go to Cited Page
              </Button>
            )}
            {onDismissCitation && (
              <button
                onClick={onDismissCitation}
                className="min-w-[36px] min-h-[36px] p-2 flex items-center justify-center rounded-lg text-content-muted hover:text-content-primary hover:bg-surface-secondary transition-colors active:scale-95"
                title="Dismiss citation highlight"
                aria-label="Dismiss citation highlight"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Main Reading Workspace                                            */}
      {/* ----------------------------------------------------------------- */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Left: Page Thumbnail / Jump Drawer */}
        {showThumbnails && (
          <div className="w-48 bg-surface-primary border-r border-border-subtle flex flex-col shrink-0">
            <div className="p-3 border-b border-border-subtle flex items-center justify-between text-xs font-semibold uppercase text-content-muted">
              <span>Pages ({numPages})</span>
              <button
                onClick={() => setShowThumbnails(false)}
                className="hover:text-content-primary"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
              {Array.from({ length: numPages }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  onClick={() => setCurrentPage(p)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors flex items-center justify-between ${
                    p === currentPage
                      ? 'bg-brand/10 text-brand border border-brand/30'
                      : 'text-content-secondary hover:bg-surface-secondary'
                  }`}
                >
                  <span>Page {p}</span>
                  {activeCitation?.pageNumber === p && (
                    <span className="w-1.5 h-1.5 rounded-full bg-brand" />
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Center: PDF Canvas & Text Layer Container */}
        <div
          ref={containerRef}
          className="flex-1 overflow-auto p-6 flex justify-center items-start bg-app"
        >
          {isLoadingPdf ? (
            <div className="w-[612px] h-[792px] max-w-full rounded-xl border border-border-subtle bg-surface-primary shadow-xl p-10 flex flex-col justify-between animate-pulse">
              <div className="space-y-6">
                <div className="flex items-center justify-between pb-6 border-b border-border-subtle">
                  <div className="space-y-2">
                    <div className="h-6 w-48 bg-surface-secondary rounded" />
                    <div className="h-3.5 w-32 bg-surface-secondary/70 rounded" />
                  </div>
                  <div className="w-10 h-10 rounded-lg bg-surface-secondary" />
                </div>
                <div className="space-y-3 pt-4">
                  <div className="h-4 w-full bg-surface-secondary/80 rounded" />
                  <div className="h-4 w-11/12 bg-surface-secondary/80 rounded" />
                  <div className="h-4 w-5/6 bg-surface-secondary/80 rounded" />
                  <div className="h-4 w-full bg-surface-secondary/80 rounded" />
                </div>
                <div className="space-y-3 pt-6">
                  <div className="h-4 w-10/12 bg-surface-secondary/80 rounded" />
                  <div className="h-4 w-full bg-surface-secondary/80 rounded" />
                  <div className="h-4 w-4/5 bg-surface-secondary/80 rounded" />
                </div>
              </div>
              <div className="pt-6 border-t border-border-subtle flex items-center justify-between text-xs text-content-muted">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-3.5 h-3.5 text-brand animate-spin" />
                  <span>Loading PDF page structure...</span>
                </div>
                <div className="h-3 w-16 bg-surface-secondary rounded" />
              </div>
            </div>
          ) : loadError ? (
            <div className="max-w-md my-8">
              <Alert
                variant="error"
                title="Failed to Load PDF"
                icon={<AlertTriangle className="w-5 h-5" />}
              >
                <div className="space-y-3">
                  <p className="text-xs leading-relaxed">{loadError}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={loadPdf}
                    icon={<RefreshCw className="w-3.5 h-3.5" />}
                  >
                    Retry Loading
                  </Button>
                </div>
              </Alert>
            </div>
          ) : (
            <div
              className="relative shadow-2xl rounded-sm border border-border-subtle bg-[#F5F3EF]"
              style={{
                width: `${Math.floor(pageSize.width * scale)}px`,
                height: `${Math.floor(pageSize.height * scale)}px`,
              }}
            >
              {/* PDF Canvas */}
              <canvas
                ref={canvasRef}
                className="absolute top-0 left-0 block rounded-sm"
              />

              {/* PDF.js Text Layer for text selection */}
              <div
                ref={textLayerRef}
                className="textLayer absolute top-0 left-0"
              />

              {/* Citation Bounding Box Highlight Overlay */}
              {isCitationActiveOnCurrentPage && highlightStyle && (
                <div
                  style={highlightStyle}
                  className={`rounded-sm transition-all duration-200 ease-enter z-20 animate-in fade-in zoom-in-95 transform-gpu ${
                    activeCitation?.isVerified
                      ? 'border-2 border-brand bg-brand/25 shadow-[0_0_15px_rgba(205,242,43,0.35)]'
                      : 'border-2 border-dashed border-brand/80 bg-brand/15 shadow-[0_0_15px_rgba(205,242,43,0.20)]'
                  }`}
                />
              )}
            </div>
          )}
        </div>

        {/* Right: Citation & Metadata Drawer */}
        {activeCitation && showCitationDetails && (
          <div className="w-72 bg-surface-primary border-l border-border-subtle flex flex-col shrink-0">
            <div className="p-3 border-b border-border-subtle flex items-center justify-between text-xs font-semibold uppercase text-content-muted">
              <span>Citation Evidence</span>
              <button
                onClick={() => setShowCitationDetails(false)}
                className="hover:text-content-primary"
              >
                <X className="w-3 h-3" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
              <div>
                <span className="text-[11px] font-semibold text-content-muted uppercase block mb-1">
                  Verification Status
                </span>
                {activeCitation.isVerified ? (
                  <Badge variant="success">
                    <CheckCircle2 className="w-3 h-3 mr-1 inline" />
                    Verified Support
                  </Badge>
                ) : (
                  <Badge variant="warning">
                    <AlertTriangle className="w-3 h-3 mr-1 inline" />
                    Partial / Unverified Support
                  </Badge>
                )}
              </div>

              {activeCitation.claimText && (
                <div>
                  <span className="text-[11px] font-semibold text-content-muted uppercase block mb-1">
                    Asserted Claim
                  </span>
                  <p className="text-content-primary font-medium leading-relaxed bg-surface-secondary/60 p-2.5 rounded-lg border border-border-subtle">
                    {activeCitation.claimText}
                  </p>
                </div>
              )}

              {activeCitation.quote && (
                <div>
                  <span className="text-[11px] font-semibold text-content-muted uppercase block mb-1">
                    Exact Ground-Truth Quote
                  </span>
                  <blockquote className="text-content-secondary italic border-l-2 border-brand pl-2.5 py-1 leading-relaxed">
                    "{activeCitation.quote}"
                  </blockquote>
                </div>
              )}

              <div className="space-y-1.5 pt-2 border-t border-border-subtle text-[11px] text-content-muted">
                <div className="flex justify-between">
                  <span>Cited Page:</span>
                  <span className="font-mono text-content-primary">
                    Page {activeCitation.pageNumber}
                  </span>
                </div>
                {activeCitation.bbox && (
                  <div className="flex justify-between">
                    <span>Coordinates:</span>
                    <span className="font-mono text-content-primary">
                      {Math.round(activeCitation.bbox.x0 || 0)},{' '}
                      {Math.round(activeCitation.bbox.y0 || 0)} -{' '}
                      {Math.round(activeCitation.bbox.x1 || 0)},{' '}
                      {Math.round(activeCitation.bbox.y1 || 0)}
                    </span>
                  </div>
                )}
                {activeCitation.groundingScore !== undefined && (
                  <div className="flex justify-between">
                    <span>Grounding Score:</span>
                    <span className="font-mono text-content-primary">
                      {Math.round(activeCitation.groundingScore * 100)}%
                    </span>
                  </div>
                )}
              </div>

              {onDismissCitation && (
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full mt-2"
                  onClick={onDismissCitation}
                >
                  Clear Highlight
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
