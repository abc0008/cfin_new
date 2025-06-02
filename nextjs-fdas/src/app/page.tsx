import Link from 'next/link'
import { BarChart3, FileUp, FileSearch, Zap } from 'lucide-react'

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <header className="text-center mb-16">
          <h1 className="text-4xl font-avenir-pro-demi text-primary mb-4 tracking-tight">
            Financial Document Analysis System
          </h1>
          <p className="text-xl font-avenir-pro-light text-muted-foreground max-w-3xl mx-auto">
            AI-powered application that analyzes financial PDFs using an interactive chatbot 
            and advanced data visualization.
          </p>
        </header>

        {/* Main Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
          <div className="bg-card p-8 rounded-xl shadow-sm hover:shadow-md transition-all duration-200 border border-border hover:border-primary/20">
            <div className="flex items-center mb-4">
              <div className="bg-primary/10 p-3 rounded-full mr-4">
                <FileUp className="h-6 w-6 text-primary" />
              </div>
              <h2 className="text-xl font-avenir-pro-demi text-foreground">Document Processing</h2>
            </div>
            <p className="font-avenir-pro text-muted-foreground mb-4">
              Upload financial documents to extract structured data, tables, and citations using Claude API technology.
            </p>
            <ul className="space-y-2 font-avenir-pro-light text-foreground">
              <li className="flex items-center">
                <Zap className="h-4 w-4 text-primary mr-2" />
                Intelligent PDF processing
              </li>
              <li className="flex items-center">
                <Zap className="h-4 w-4 text-primary mr-2" />
                Citation extraction and linking
              </li>
              <li className="flex items-center">
                <Zap className="h-4 w-4 text-primary mr-2" />
                Multi-document analysis
              </li>
            </ul>
          </div>

          <div className="bg-card p-8 rounded-xl shadow-sm hover:shadow-md transition-all duration-200 border border-border hover:border-primary/20">
            <div className="flex items-center mb-4">
              <div className="bg-secondary/10 p-3 rounded-full mr-4">
                <FileSearch className="h-6 w-6 text-secondary" />
              </div>
              <h2 className="text-xl font-avenir-pro-demi text-foreground">Interactive Analysis</h2>
            </div>
            <p className="font-avenir-pro text-muted-foreground mb-4">
              Engage with your financial data through a conversational interface with contextual understanding.
            </p>
            <ul className="space-y-2 font-avenir-pro-light text-foreground">
              <li className="flex items-center">
                <Zap className="h-4 w-4 text-secondary mr-2" />
                Multi-turn conversation
              </li>
              <li className="flex items-center">
                <Zap className="h-4 w-4 text-secondary mr-2" />
                Contextual references to documents
              </li>
              <li className="flex items-center">
                <Zap className="h-4 w-4 text-secondary mr-2" />
                Guided analysis prompts
              </li>
            </ul>
          </div>

          <div className="bg-card p-8 rounded-xl shadow-sm hover:shadow-md transition-all duration-200 border border-border hover:border-primary/20">
            <div className="flex items-center mb-4">
              <div className="bg-accent/10 p-3 rounded-full mr-4">
                <BarChart3 className="h-6 w-6 text-accent" />
              </div>
              <h2 className="text-xl font-avenir-pro-demi text-foreground">Visual Insights</h2>
            </div>
            <p className="font-avenir-pro text-muted-foreground mb-4">
              Transform financial data into interactive visualizations with citation linking.
            </p>
            <ul className="space-y-2 font-avenir-pro-light text-foreground">
              <li className="flex items-center">
                <Zap className="h-4 w-4 text-accent mr-2" />
                Dynamic charts and graphs
              </li>
              <li className="flex items-center">
                <Zap className="h-4 w-4 text-accent mr-2" />
                Time series analysis
              </li>
              <li className="flex items-center">
                <Zap className="h-4 w-4 text-accent mr-2" />
                Comparative financial metrics
              </li>
            </ul>
          </div>
        </div>

        {/* Call to Action */}
        <div className="text-center">
          <Link 
            href="/workspace" 
            className="btn-primary inline-flex items-center px-8 py-3 rounded-lg transition-colors"
          >
            <span className="font-avenir-pro-demi">Get Started</span>
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 ml-2" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10.293 5.293a1 1 0 011.414 0l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414-1.414L12.586 11H5a1 1 0 110-2h7.586l-2.293-2.293a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </Link>
          <p className="mt-4 font-avenir-pro text-muted-foreground">
            Or explore the <Link href="/dashboard" className="text-primary hover:text-primary/80 font-avenir-pro-demi">dashboard</Link>
          </p>
        </div>
      </div>
    </main>
  )
}