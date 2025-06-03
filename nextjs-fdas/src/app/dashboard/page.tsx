/**
 * Dashboard Page Component
 * 
 * This is the main dashboard page that provides an overview of the financial analysis system.
 * It includes:
 * - Document management (upload, view, delete)
 * - Analysis tracking and access
 * - Key metrics display
 * - Recent analyses overview
 * 
 * The page is organized into several sections:
 * 1. Header with quick access to new analysis
 * 2. Stats overview showing document count, analysis count, and last activity
 * 3. Main content area with document list and upload functionality
 * 4. Recent analyses section showing past analysis results
 */

"use client"

import { useEffect, useState } from 'react'
import { BarChart2, Calendar, FileText, Plus, TrendingUp, Users, Activity } from 'lucide-react'
import Link from 'next/link'
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { DocumentList } from '@/components/DocumentList'
import { UploadForm } from '@/components/document/UploadForm'
import { DocumentDetails } from '@/components/document/DocumentDetails'
import { AnalysisControls } from '@/components/analysis/AnalysisControls'
import { fetchAnalysesForDocument, fetchDocument, fetchDocuments, uploadFile } from '@/lib/api/documentApi'
import { AnalysisResult, DocumentPlus, ProcessedDocument } from '@/types'

export default function Dashboard() {
  // State to trigger document list refresh when uploading a new document
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [lastUploadedDocument, setLastUploadedDocument] = useState<ProcessedDocument | null>(null);

  // Mock data for recent analyses (would come from API in production)
  const [analyses, setAnalyses] = useState([
    { id: '1', name: 'Revenue Trend Analysis', date: '2023-12-30', metrics: ['Revenue', 'COGS', 'Gross Margin'] },
    { id: '2', name: 'Liquidity Ratio Analysis', date: '2023-12-20', metrics: ['Current Ratio', 'Quick Ratio', 'Cash Ratio'] },
  ]);

  // Handle successful document upload
  const handleUploadSuccess = (document: ProcessedDocument) => {
    // Update the last uploaded document state
    setLastUploadedDocument(document);
    
    // Trigger a refresh of the document list
    setRefreshTrigger(prev => prev + 1);
  };

  // Handle selection of a document
  const handleSelectDocument = (documentId: string) => {
    // Navigate to the document viewer or workspace page
    window.location.href = `/workspace?document=${documentId}`;
  };

  // Handle analyze action for a document
  const handleAnalyzeDocument = (documentId: string) => {
    window.location.href = `/workspace?document=${documentId}&analyze=true`;
  };

  // Handle document deletion
  const handleDocumentDelete = (documentId: string) => {
    // The DocumentList component handles the deletion API call
    // Here we can add any additional logic if needed
    console.log(`Document ${documentId} has been deleted`);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b border-border bg-card">
        <div className="container mx-auto px-6 py-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="font-avenir-pro-demi text-4xl text-foreground tracking-tighter">
                Financial Dashboard
              </h1>
              <p className="font-avenir-pro-light text-lg text-muted-foreground mt-2">
                AI-powered document analysis and insights
              </p>
            </div>
            <Link 
              href="/workspace"
              className="btn-primary flex items-center"
            >
              <Plus className="h-5 w-5 mr-2" />
              New Analysis
            </Link>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-6 py-12">
        {/* Stats Overview - Professional metric cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
          <div className="metric-card">
            <div className="flex items-center justify-between">
              <h3 className="metric-card-title">Total Documents</h3>
              <div className="p-2 bg-primary/10 rounded-lg">
                <FileText className="h-6 w-6 text-primary" />
              </div>
            </div>
            <div className="mt-4">
              <div className="metric-card-value" id="document-count">-</div>
              <p className="font-avenir-pro-light text-sm text-muted-foreground mt-2">
                Uploaded financial documents
              </p>
            </div>
          </div>

          <div className="metric-card">
            <div className="flex items-center justify-between">
              <h3 className="metric-card-title">Completed Analyses</h3>
              <div className="p-2 bg-secondary/10 rounded-lg">
                <BarChart2 className="h-6 w-6 text-secondary" />
              </div>
            </div>
            <div className="mt-4">
              <div className="metric-card-value">{analyses.length}</div>
              <div className="flex items-center mt-2">
                <TrendingUp className="h-4 w-4 text-secondary mr-1" />
                <span className="font-avenir-pro text-sm text-secondary">Active</span>
              </div>
            </div>
          </div>

          <div className="metric-card">
            <div className="flex items-center justify-between">
              <h3 className="metric-card-title">Last Activity</h3>
              <div className="p-2 bg-accent/10 rounded-lg">
                <Activity className="h-6 w-6 text-accent" />
              </div>
            </div>
            <div className="mt-4">
              <div className="font-avenir-pro-demi text-2xl text-foreground tracking-tighter">Today</div>
              <p className="font-avenir-pro-light text-sm text-muted-foreground mt-2">
                Recent document processing
              </p>
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
          {/* Documents List */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle className="font-avenir-pro-demi text-xl tracking-tighter">Document Library</CardTitle>
                <CardDescription className="font-avenir-pro-light">
                  Manage and analyze your financial documents
                </CardDescription>
              </CardHeader>
              <CardContent>
                <DocumentList 
                  refreshTrigger={refreshTrigger}
                  onSelectDocument={handleSelectDocument}
                  onDelete={handleDocumentDelete}
                  onAnalyze={handleAnalyzeDocument}
                />
              </CardContent>
            </Card>
          </div>
          
          {/* Upload Section */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="font-avenir-pro-demi text-xl tracking-tighter">Upload Document</CardTitle>
                <CardDescription className="font-avenir-pro-light">
                  Add financial documents for AI analysis
                </CardDescription>
              </CardHeader>
              <CardContent>
                <UploadForm onUploadSuccess={handleUploadSuccess} />
                
                {lastUploadedDocument && (
                  <div className="mt-6 p-4 bg-secondary/10 border border-secondary/20 rounded-lg">
                    <p className="font-avenir-pro-demi text-sm text-secondary">
                      Successfully uploaded: {lastUploadedDocument.metadata.filename}
                    </p>
                    <p className="font-avenir-pro-light text-xs text-muted-foreground mt-1">
                      {lastUploadedDocument.citations?.length || 0} citations extracted
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="font-avenir-pro-demi text-lg tracking-tighter">Supported Formats</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-avenir-pro text-sm text-muted-foreground mb-4">
                  PDF documents containing financial statements:
                </p>
                <ul className="space-y-2 font-avenir-pro-light text-sm text-muted-foreground">
                  <li className="flex items-center">
                    <div className="h-1.5 w-1.5 bg-primary rounded-full mr-3"></div>
                    Balance Sheets
                  </li>
                  <li className="flex items-center">
                    <div className="h-1.5 w-1.5 bg-primary rounded-full mr-3"></div>
                    Income Statements
                  </li>
                  <li className="flex items-center">
                    <div className="h-1.5 w-1.5 bg-primary rounded-full mr-3"></div>
                    Cash Flow Statements
                  </li>
                  <li className="flex items-center">
                    <div className="h-1.5 w-1.5 bg-primary rounded-full mr-3"></div>
                    Annual Reports
                  </li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Recent Analyses Section */}
        <div>
          <div className="flex justify-between items-center mb-8">
            <div>
              <h2 className="font-avenir-pro-demi text-2xl text-foreground tracking-tighter">Recent Analyses</h2>
              <p className="font-avenir-pro-light text-muted-foreground mt-1">
                View and continue your financial analysis work
              </p>
            </div>
            <Link
              href="/workspace"
              className="font-avenir-pro text-primary hover:text-primary/80 font-medium flex items-center transition-colors"
            >
              View All
              <svg className="ml-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path>
              </svg>
            </Link>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {analyses.map((analysis) => (
              <Card key={analysis.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <CardTitle className="font-avenir-pro-demi text-lg tracking-tighter">
                        {analysis.name}
                      </CardTitle>
                      <CardDescription className="font-avenir-pro-light mt-1">
                        {new Date(analysis.date).toLocaleDateString('en-US', { 
                          year: 'numeric', 
                          month: 'long', 
                          day: 'numeric' 
                        })}
                      </CardDescription>
                    </div>
                    <div className="p-2 bg-primary/10 rounded-lg">
                      <BarChart2 className="h-5 w-5 text-primary" />
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2 mb-4">
                    {analysis.metrics.map((metric, index) => (
                      <span 
                        key={index} 
                        className="px-3 py-1 text-xs font-avenir-pro rounded-full bg-muted text-muted-foreground"
                      >
                        {metric}
                      </span>
                    ))}
                  </div>
                </CardContent>
                <CardFooter>
                  <Link 
                    href={`/workspace?analysis=${analysis.id}`}
                    className="btn-outline w-full justify-center text-sm"
                  >
                    Open Analysis
                  </Link>
                </CardFooter>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}