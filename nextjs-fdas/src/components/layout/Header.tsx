'use client'

import Link from 'next/link'
import Image from 'next/image'
import { usePathname } from 'next/navigation'
import { BarChart, FileText, Home, Settings, User } from 'lucide-react'

export default function Header() {
  const pathname = usePathname()

  return (
    <header className="border-b border-border bg-card shadow-sm">
      <div className="container mx-auto px-6 py-4">
        <div className="flex justify-between items-center">
          {/* Logo and branding */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center group">
              <div className="bg-primary text-primary-foreground p-2 rounded-lg mr-3 group-hover:bg-primary/90 transition-colors">
                <BarChart className="h-6 w-6" />
              </div>
              <div className="flex flex-col">
                <span className="font-avenir-pro-demi text-2xl text-foreground tracking-tighter">FDAS</span>
                <span className="font-avenir-pro-light text-xs text-muted-foreground uppercase tracking-wide">
                  Financial Document Analysis
                </span>
              </div>
            </Link>
          </div>

          {/* Main navigation */}
          <nav className="hidden md:flex space-x-2">
            <Link 
              href="/" 
              className={`px-4 py-2.5 rounded-lg text-sm font-avenir-pro transition-all duration-200 ${
                pathname === '/' 
                  ? 'bg-primary text-primary-foreground shadow-sm' 
                  : 'text-foreground hover:bg-muted hover:text-foreground'
              }`}
            >
              <div className="flex items-center">
                <Home className="h-4 w-4 mr-2" />
                <span className="font-avenir-pro">Home</span>
              </div>
            </Link>
            <Link 
              href="/dashboard" 
              className={`px-4 py-2.5 rounded-lg text-sm font-avenir-pro transition-all duration-200 ${
                pathname === '/dashboard' 
                  ? 'bg-primary text-primary-foreground shadow-sm' 
                  : 'text-foreground hover:bg-muted hover:text-foreground'
              }`}
            >
              <div className="flex items-center">
                <BarChart className="h-4 w-4 mr-2" />
                <span className="font-avenir-pro">Dashboard</span>
              </div>
            </Link>
            <Link 
              href="/workspace" 
              className={`px-4 py-2.5 rounded-lg text-sm font-avenir-pro transition-all duration-200 ${
                pathname === '/workspace' 
                  ? 'bg-primary text-primary-foreground shadow-sm' 
                  : 'text-foreground hover:bg-muted hover:text-foreground'
              }`}
            >
              <div className="flex items-center">
                <FileText className="h-4 w-4 mr-2" />
                <span className="font-avenir-pro">Workspace</span>
              </div>
            </Link>
          </nav>

          {/* User menu */}
          <div className="flex items-center space-x-3">
            <button className="p-2 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors">
              <Settings className="h-5 w-5" />
            </button>
            <button className="p-2 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors">
              <User className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}