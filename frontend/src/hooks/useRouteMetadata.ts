import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

export interface BreadcrumbMetaItem {
  label: string;
  to?: string;
}

export interface RouteMetadataOptions {
  /** Page title displayed in the browser tab. Suffix "| DocuMind" added if not present. */
  title: string;
  /** Natural language meta description for public pages. */
  description?: string;
  /**
   * Whether this route is private application space.
   * If true, applies "noindex, nofollow" to prevent search engine indexing of private corpus data.
   * @default true
   */
  isPrivate?: boolean;
  /** Custom canonical path if different from current pathname. */
  canonicalPath?: string;
  /** Dynamic entity title (e.g. document filename) for local tab display without leaking into public tags. */
  dynamicEntityTitle?: string;
  /** Optional breadcrumbs list for generating BreadcrumbList Schema.org structured data. */
  breadcrumbs?: BreadcrumbMetaItem[];
}

const DEFAULT_DESCRIPTION =
  'DocuMind is a local-first AI document intelligence platform for verifiable research, hybrid vector retrieval, and automated citation verification.';

export function getAppBaseUrl(): string {
  if (typeof window !== 'undefined') {
    const envUrl = (import.meta as any).env?.VITE_APP_URL;
    if (envUrl && typeof envUrl === 'string' && envUrl.trim()) {
      return envUrl.trim().replace(/\/$/, '');
    }
    return window.location.origin.replace(/\/$/, '');
  }
  return '';
}

function updateOrCreateMetaTag(
  selector: string,
  attributeName: string,
  attributeValue: string,
  content: string
): void {
  let element = document.querySelector<HTMLMetaElement>(selector);
  if (!element) {
    element = document.createElement('meta');
    element.setAttribute(attributeName, attributeValue);
    document.head.appendChild(element);
  }
  element.setAttribute('content', content);
}

function updateOrCreateLinkTag(rel: string, href: string): void {
  let link = document.querySelector<HTMLLinkElement>(`link[rel="${rel}"]`);
  if (!link) {
    link = document.createElement('link');
    link.setAttribute('rel', rel);
    document.head.appendChild(link);
  }
  link.setAttribute('href', href);
}

function updateOrCreateJsonLd(schemaId: string, schemaData: object): void {
  let script = document.getElementById(schemaId) as HTMLScriptElement | null;
  if (!script) {
    script = document.createElement('script');
    script.id = schemaId;
    script.type = 'application/ld+json';
    document.head.appendChild(script);
  }
  script.textContent = JSON.stringify(schemaData, null, 2);
}

/**
 * Hook to manage document.title, meta tags, Open Graph, Twitter cards, indexing privacy,
 * and Schema.org JSON-LD structured data per route.
 */
export function useRouteMetadata(options: RouteMetadataOptions): void {
  const location = useLocation();

  useEffect(() => {
    // 1. Resolve Document Title for Local Browser Tab
    const baseTitle = options.dynamicEntityTitle
      ? `${options.dynamicEntityTitle} | DocuMind`
      : options.title.includes('DocuMind')
      ? options.title
      : `${options.title} | DocuMind`;

    document.title = baseTitle;

    // 2. Canonical URL Resolution (Clean, no query parameters, consistent slash policy)
    const baseUrl = getAppBaseUrl();
    const rawPathname = options.canonicalPath || location.pathname;
    // Normalized pathname: root is '/', sub-routes have leading slash and no trailing slash
    const normalizedPathname =
      rawPathname === '/' ? '/' : `/${rawPathname.replace(/^\/+|\/+$/g, '')}`;
    const fullCanonicalUrl = `${baseUrl}${normalizedPathname}`;

    // 3. Privacy Boundary: Robots Directive
    // Private application routes MUST NOT be indexed by search engines.
    const isPrivate = options.isPrivate ?? true;
    const robotsDirective = isPrivate ? 'noindex, nofollow' : 'index, follow';
    updateOrCreateMetaTag('meta[name="robots"]', 'name', 'robots', robotsDirective);

    // 4. Meta Description
    // On private routes, never leak sensitive document text. Use safe platform description.
    const description = options.description || DEFAULT_DESCRIPTION;
    updateOrCreateMetaTag('meta[name="description"]', 'name', 'description', description);

    // 5. Canonical Link
    updateOrCreateLinkTag('canonical', fullCanonicalUrl);

    // 6. Open Graph Protocol (Standardized platform identity)
    const ogTitle = options.isPrivate
      ? 'DocuMind — Grounded Document Intelligence'
      : baseTitle;
    const ogDescription = options.isPrivate
      ? DEFAULT_DESCRIPTION
      : description;
    const ogImageUrl = `${baseUrl}/og-image.png`;

    updateOrCreateMetaTag('meta[property="og:title"]', 'property', 'og:title', ogTitle);
    updateOrCreateMetaTag('meta[property="og:description"]', 'property', 'og:description', ogDescription);
    updateOrCreateMetaTag('meta[property="og:type"]', 'property', 'og:type', 'website');
    updateOrCreateMetaTag('meta[property="og:url"]', 'property', 'og:url', fullCanonicalUrl);
    updateOrCreateMetaTag('meta[property="og:image"]', 'property', 'og:image', ogImageUrl);
    updateOrCreateMetaTag('meta[property="og:site_name"]', 'property', 'og:site_name', 'DocuMind');

    // 7. Twitter / X Card Protocol
    updateOrCreateMetaTag('meta[name="twitter:card"]', 'name', 'twitter:card', 'summary_large_image');
    updateOrCreateMetaTag('meta[name="twitter:title"]', 'name', 'twitter:title', ogTitle);
    updateOrCreateMetaTag('meta[name="twitter:description"]', 'name', 'twitter:description', ogDescription);
    updateOrCreateMetaTag('meta[name="twitter:image"]', 'name', 'twitter:image', ogImageUrl);

    // 8. Schema.org Structured Data (JSON-LD)
    const schemaGraph: any[] = [];

    // Core Platform & SoftwareApplication Schema
    if (!options.isPrivate && normalizedPathname === '/') {
      schemaGraph.push({
        '@type': 'WebSite',
        '@id': `${baseUrl}/#website`,
        url: `${baseUrl}/`,
        name: 'DocuMind',
        description: 'Local-first AI document intelligence, research workspace, and citation verification engine.',
      });

      schemaGraph.push({
        '@type': 'SoftwareApplication',
        '@id': `${baseUrl}/#software`,
        name: 'DocuMind',
        applicationCategory: 'BusinessApplication',
        operatingSystem: 'Windows, macOS, Linux',
        softwareVersion: '0.2.0',
        description:
          'Local-first AI document intelligence platform for verifiable research, hybrid vector retrieval, and automated citation verification.',
        offers: {
          '@type': 'Offer',
          price: '0',
          priceCurrency: 'USD',
        },
        featureList: [
          'Hybrid dense and lexical retrieval (BM25 + 768-dim vector search)',
          'Two-stage claim verification and quote grounding',
          'PDF coordinate bounding box citation mapping',
          'Dual AI provider routing (Groq Cloud API & local Ollama)',
          '100% offline air-gap capable execution',
        ],
      });
    }

    // BreadcrumbList Schema (if breadcrumbs provided)
    if (options.breadcrumbs && options.breadcrumbs.length > 0) {
      schemaGraph.push({
        '@type': 'BreadcrumbList',
        itemListElement: options.breadcrumbs.map((crumb, idx) => ({
          '@type': 'ListItem',
          position: idx + 1,
          name: crumb.label,
          item: crumb.to ? `${baseUrl}${crumb.to}` : undefined,
        })),
      });
    }

    if (schemaGraph.length > 0) {
      updateOrCreateJsonLd('documind-schema-ld', {
        '@context': 'https://schema.org',
        '@graph': schemaGraph,
      });
    } else {
      const existing = document.getElementById('documind-schema-ld');
      if (existing) existing.remove();
    }
  }, [
    options.title,
    options.description,
    options.isPrivate,
    options.canonicalPath,
    options.dynamicEntityTitle,
    options.breadcrumbs,
    location.pathname,
  ]);
}
