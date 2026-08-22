const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '')
const isLocalhostUrl = (value: string) => /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?/i.test(value)

function resolvePublicUrl(rawUrl: string | undefined, fallbackUrl: string): string {
  const normalized = rawUrl?.trim()
  if (!normalized) return fallbackUrl
  if (isLocalhostUrl(normalized)) return fallbackUrl
  return normalized
}

const BANK_ANALYSIS_APP_URL =
  process.env.NEXT_PUBLIC_BANKANALYSIS_APP_URL ||
  (process.env.NODE_ENV === 'development'
    ? 'http://localhost:3002'
    : 'https://bankanalysis.aceanalytics.dev')

export const RM_PRO_FORMA_URL = `${trimTrailingSlash(BANK_ANALYSIS_APP_URL)}/rm-pro-forma`
export const CREDIT_SPREAD_URL = `${trimTrailingSlash(BANK_ANALYSIS_APP_URL)}/credit-spread`
export const REGIONAL_FORECASTING_URL = `${trimTrailingSlash(BANK_ANALYSIS_APP_URL)}/forecasting`
export const CLOSE_INTEL_URL = `${trimTrailingSlash(BANK_ANALYSIS_APP_URL)}/forecasting/close-intel`

const PEER_ANALYSIS_APP_URL =
  process.env.NEXT_PUBLIC_PEER_ANALYSIS_APP_URL ||
  (process.env.NODE_ENV === 'development'
    ? 'http://localhost:3000'
    : 'https://peeranalysis.aceanalytics.dev')
/** Peer Lens — bank peer-analysis app (its own subdomain). */
export const PEER_ANALYSIS_URL = trimTrailingSlash(PEER_ANALYSIS_APP_URL)

/** Annex — M&A target screener & deal lab (its own subdomain). */
export const ANNEX_URL = resolvePublicUrl(
  process.env.NEXT_PUBLIC_ANNEX_APP_URL,
  'https://annex.aceanalytics.dev',
)

const CFIN_WORKSPACE_DEFAULT_URL = 'https://aceanalytics.dev/workspace'
export const CFIN_WORKSPACE_URL = resolvePublicUrl(
  process.env.NEXT_PUBLIC_CFIN_WORKSPACE_URL,
  CFIN_WORKSPACE_DEFAULT_URL,
)

/** Public booking page (Google Calendar embed shell on cal.aceanalytics.dev). */
export const BOOK_DEMO_URL = resolvePublicUrl(
  process.env.NEXT_PUBLIC_BOOK_DEMO_URL,
  'https://cal.aceanalytics.dev/demo',
)
