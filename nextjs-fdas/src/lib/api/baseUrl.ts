const DEFAULT_DEVELOPMENT_API_URL = 'http://localhost:8000';
const DEFAULT_PRODUCTION_API_URL = 'https://cfin-backend.vercel.app';

const stripTrailingSlashes = (value: string) => value.replace(/\/+$/, '');

const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();

export const API_BASE_URL = stripTrailingSlashes(
  configuredApiUrl ||
    (process.env.NODE_ENV === 'production'
      ? DEFAULT_PRODUCTION_API_URL
      : DEFAULT_DEVELOPMENT_API_URL)
);

export const API_ORIGIN_URL = API_BASE_URL.endsWith('/api')
  ? API_BASE_URL.slice(0, -4)
  : API_BASE_URL;

export const ENABLE_WEBSOCKET_STREAMING =
  process.env.NEXT_PUBLIC_ENABLE_WEBSOCKETS === 'true' ||
  (
    process.env.NEXT_PUBLIC_ENABLE_WEBSOCKETS !== 'false' &&
    !API_ORIGIN_URL.includes('.vercel.app')
  );

export function apiUrl(endpoint: string): string {
  const normalized = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;

  if (normalized === '/api') {
    return `${API_ORIGIN_URL}/api`;
  }

  if (normalized.startsWith('/api/')) {
    return `${API_ORIGIN_URL}${normalized}`;
  }

  return `${API_ORIGIN_URL}/api${normalized}`;
}

export function websocketUrl(endpoint: string): string {
  const normalized = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = new URL(normalized, `${API_ORIGIN_URL}/`);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return url.toString();
}
