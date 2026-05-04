import Header from '@/components/layout/Header'
import { WorkspaceThemeShell } from '@/components/layout/WorkspaceThemeShell'

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <WorkspaceThemeShell>
      <div className="min-h-screen flex flex-col">
        <Header />
        <main className="flex-1 flex flex-col">
          {children}
        </main>
      </div>
    </WorkspaceThemeShell>
  )
}