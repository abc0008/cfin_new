import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'nodejs'

export function GET(request: NextRequest) {
  const iconUrl = new URL('/ace-card-favicon-v2.ico', request.url)
  return NextResponse.redirect(iconUrl, 308)
}
