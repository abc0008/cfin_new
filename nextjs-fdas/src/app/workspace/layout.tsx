import Header from '@/components/layout/Header'
import { WorkspaceThemeShell } from '@/components/layout/WorkspaceThemeShell'
import { CitationProvider } from '@/context/CitationContext'

export default function WorkspaceLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <CitationProvider>
      <WorkspaceThemeShell>
        <div className="min-h-screen flex flex-col">
          <Header />
          <main className="flex-1 flex flex-col">
            {children}
          </main>
        </div>
      </WorkspaceThemeShell>
    </CitationProvider>
  )
}