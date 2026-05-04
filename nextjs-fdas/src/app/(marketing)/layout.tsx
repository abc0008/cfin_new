import './marketing.css'
import { MarketingChrome } from '@/components/marketing/shared'

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return <MarketingChrome>{children}</MarketingChrome>
}
