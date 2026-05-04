const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '')

const BANK_ANALYSIS_APP_URL =
  process.env.NEXT_PUBLIC_BANKANALYSIS_APP_URL ||
  (process.env.NODE_ENV === 'development'
    ? 'http://localhost:3002'
    : 'https://bankanalysis.aceanalytics.dev')

export const RM_PRO_FORMA_URL = `${trimTrailingSlash(BANK_ANALYSIS_APP_URL)}/rm-pro-forma`
