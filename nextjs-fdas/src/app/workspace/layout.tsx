import Header from '@/components/layout/Header'
import { CitationProvider } from '@/context/CitationContext'

export default function WorkspaceLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <CitationProvider>
      <div className="min-h-screen flex flex-col">
        <Header />
        <main className="flex-1 flex flex-col">
          {children}
        </main>
      </div>
    </CitationProvider>
  )
}