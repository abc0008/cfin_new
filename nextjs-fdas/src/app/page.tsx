import Link from 'next/link'
import { BarChart3, FileUp, FileSearch, Zap, TrendingUp, Shield, Users, ArrowRight, CheckCircle, Star, Play, HelpCircle, Mail, ChevronDown, AlertTriangle, Award, Clock } from 'lucide-react'
import { Modal, ModalBody, ModalContent, ModalTrigger } from '@/components/ui/animated-modal';
import { AppleCardsCarousel } from '@/components/ui/apple-cards-carousel';
import TestimonialCard from '@/components/testimonials/TestimonialCard';
import { Skeleton } from '@/components/ui/skeleton'
import AnimatedBeamSection from '@/components/sections/AnimatedBeamSection'

export default function Home() {
  const testimonialsData = [
    {
      id: 1,
      quote: "FDAS transformed our quarterly reporting process. What used to take days now takes hours.",
      name: "Michael Rodriguez",
      title: "CFO, TechCorp",
      avatarImage: "/assets/TestimonialPortraits/man-7450033_1920.jpg",
    },
    {
      id: 2,
      quote: "The citation tracking feature is incredible. Every insight is instantly verifiable.",
      name: "Sarah Brannon",
      title: "Senior Analyst, TechCorp",
      avatarImage: "/assets/TestimonialPortraits/woman-7450034_1920.jpg",
    },
    {
      id: 3,
      quote: "Finally, a tool that understands financial context. The AI responses are remarkably accurate.",
      name: "David Lee",
      title: "Investment Manager, Meridian Capital",
      avatarImage: "/assets/TestimonialPortraits/engineer-4922428_1920.jpg",
    },
    {
      id: 4, 
      quote: "The intuitive interface and powerful AI have saved us countless hours.",
      name: "Emily Zhang",
      title: "Financial Controller, BlueHarbor Group",
      avatarImage: "/assets/TestimonialPortraits/engineer-4940833_1920.jpg", 
    },
    {
      id: 5, 
      quote: "A game-changer for our financial reporting and analysis workflows.",
      name: "Jace Miller",
      title: "Head of Finance, Axiom Partners",
      avatarImage: "/assets/TestimonialPortraits/fashion-4951644_1920.jpg", 
    },
  ];

  return (
    <main className="min-h-screen bg-gradient-to-b from-background via-background to-brand-white-smoke">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        {/* Background Elements */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-secondary/5 to-accent/5"></div>
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-bl from-primary/10 to-transparent rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 left-0 w-80 h-80 bg-gradient-to-tr from-secondary/10 to-transparent rounded-full blur-3xl"></div>
        
        <div className="relative container mx-auto px-4 py-20">
          <div className="max-w-4xl mx-auto text-center">
            {/* Badge with Lust accent */}
            <div className="inline-flex items-center px-4 py-2 rounded-full bg-gradient-to-r from-primary/10 to-secondary/10 border-2 border-brand-lust/20 mb-8">
              <span className="text-sm font-avenir-pro-demi text-brand-lust">✨ Powered by Claude AI</span>
            </div>
            
            {/* Main Headline */}
            <h1 className="text-5xl md:text-7xl font-avenir-pro-demi text-foreground mb-6 tracking-tight">
              Financial Document
              <span className="bg-gradient-to-r from-primary via-brand-lust to-secondary bg-clip-text text-transparent"> 
                {" "}Analysis{" "}
              </span>
              Revolutionized
          </h1>
            
            {/* Subheadline */}
            <p className="text-xl md:text-2xl font-avenir-pro text-brand-mt-rushmore max-w-3xl mx-auto mb-12 leading-relaxed">
              Transform financial PDFs into actionable insights with AI-powered analysis, 
              interactive visualizations, and citation-linked conversations.
            </p>
            
            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
              <Link 
                href="/workspace" 
                className="group relative inline-flex items-center px-8 py-4 rounded-xl bg-gradient-to-r from-primary to-primary/90 text-white font-avenir-pro-demi text-lg shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1"
              >
                <span className="absolute inset-0 rounded-xl bg-gradient-to-r from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></span>
                <span className="relative">Get Started Free</span>
                <ArrowRight className="relative ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" />
              </Link>
              
              <Modal>
                <ModalTrigger className="group film-roll-container relative inline-flex items-center px-8 py-4 rounded-xl border-2 border-brand-pigeon bg-card/50 backdrop-blur-sm text-foreground font-avenir-pro-demi text-lg hover:bg-card transition-all duration-300 transform hover:-translate-y-1">
                  <span className="absolute inset-0 rounded-xl bg-gradient-to-r from-white/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></span>
                  <Play className="relative mr-2 h-5 w-5 text-secondary film-roll" />
                  <span className="relative">Watch Demo</span>
                </ModalTrigger>
                
                <ModalBody>
                  <ModalContent>
                    <div className="text-center">
                      <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-secondary/10 to-secondary/5 border border-brand-pigeon flex items-center justify-center mx-auto mb-6">
                        <Play className="h-10 w-10 text-secondary" />
                      </div>
                      
                      <h2 className="text-3xl font-avenir-pro-demi text-foreground mb-4">
                        Financial Document Analysis Demo
                      </h2>
                      
                      <p className="text-lg text-brand-mt-rushmore mb-8 max-w-2xl mx-auto">
                        See how FDAS transforms complex financial documents into actionable insights with AI-powered analysis.
          </p>
                      
                      {/* Demo Video Placeholder */}
                      <div className="aspect-video bg-gradient-to-br from-primary/10 via-secondary/10 to-accent/10 rounded-xl border-2 border-brand-pigeon mb-6 flex items-center justify-center relative overflow-hidden">
                        <div className="absolute inset-0 bg-gradient-to-br from-brand-white-smoke/50 to-transparent"></div>
                        <div className="relative text-center">
                          <Play className="h-16 w-16 text-secondary mx-auto mb-4" />
                          <p className="text-brand-mt-rushmore font-avenir-pro">
                            Demo video will be embedded here
                          </p>
                        </div>
                      </div>
                      
                      {/* Feature highlights */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                        <div className="p-4 rounded-lg bg-brand-white-smoke border border-brand-pigeon">
                          <FileUp className="h-6 w-6 text-primary mx-auto mb-2" />
                          <p className="text-sm font-avenir-pro-demi text-foreground">Upload PDFs</p>
                        </div>
                        <div className="p-4 rounded-lg bg-brand-white-smoke border border-brand-pigeon">
                          <FileSearch className="h-6 w-6 text-secondary mx-auto mb-2" />
                          <p className="text-sm font-avenir-pro-demi text-foreground">AI Analysis</p>
                        </div>
                        <div className="p-4 rounded-lg bg-brand-white-smoke border border-brand-pigeon">
                          <BarChart3 className="h-6 w-6 text-accent mx-auto mb-2" />
                          <p className="text-sm font-avenir-pro-demi text-foreground">Interactive Charts</p>
                        </div>
                      </div>
                      
                      <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <Link 
                          href="/workspace" 
                          className="group relative inline-flex items-center px-6 py-3 rounded-xl bg-gradient-to-r from-primary to-primary/90 text-white font-avenir-pro-demi shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1"
                        >
                          <span className="absolute inset-0 rounded-xl bg-gradient-to-r from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></span>
                          <span className="relative">Try It Now</span>
                          <ArrowRight className="relative ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                        </Link>
                        
                        <Link 
                          href="/dashboard" 
                          className="inline-flex items-center text-secondary hover:text-secondary/80 font-avenir-pro-demi transition-colors group"
                        >
                          View Dashboard
                          <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                        </Link>
                      </div>
                    </div>
                  </ModalContent>
                </ModalBody>
              </Modal>
              
              <Link 
                href="/dashboard" 
                className="group relative inline-flex items-center px-8 py-4 rounded-xl bg-gradient-to-r from-accent to-accent/90 text-white font-avenir-pro-demi text-lg shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1"
              >
                <span className="absolute inset-0 rounded-xl bg-gradient-to-r from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></span>
                <span className="relative">Explore Dashboard</span>
                <ArrowRight className="relative ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" />
              </Link>
            </div>
            
            {/* Trust Indicators with brand colors */}
            <div className="flex flex-wrap justify-center items-center gap-8 text-sm text-brand-mt-rushmore font-avenir-pro">
              <div className="flex items-center">
                <Shield className="h-4 w-4 mr-2 text-secondary" />
                Enterprise Security
              </div>
              <div className="flex items-center">
                <Zap className="h-4 w-4 mr-2 text-accent" />
                99.9% Uptime
              </div>
              <div className="flex items-center">
                <Users className="h-4 w-4 mr-2 text-brand-lust" />
                500+ Companies
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Value Proposition Section */}
      <section className="py-20 bg-gradient-to-b from-brand-white-smoke to-background">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-avenir-pro-demi text-foreground mb-4">
              The Complete Financial Analysis Platform
            </h2>
            <p className="text-lg font-avenir-pro text-brand-mt-rushmore max-w-2xl mx-auto">
              From document upload to actionable insights in minutes, not hours.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {/* Step 1 */}
            <div className="group relative p-8 rounded-2xl bg-gradient-to-br from-card to-card/50 border-2 border-brand-pigeon shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-2 hover:border-primary/30">
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
              <div className="relative">
                <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center mb-6 shadow-lg">
                  <FileUp className="h-8 w-8 text-primary-foreground" />
                </div>
                <h3 className="text-xl font-avenir-pro-demi text-foreground mb-3">1. Upload & Process</h3>
                <p className="text-brand-mt-rushmore font-avenir-pro">
                  Drag and drop financial documents. Our AI extracts structured data, tables, and citations instantly.
                </p>
              </div>
            </div>
            
            {/* Step 2 */}
            <div className="group relative p-8 rounded-2xl bg-gradient-to-br from-card to-card/50 border-2 border-brand-pigeon shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-2 hover:border-secondary/30">
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-secondary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
              <div className="relative">
                <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-secondary to-secondary/80 flex items-center justify-center mb-6 shadow-lg">
                  <FileSearch className="h-8 w-8 text-secondary-foreground" />
                </div>
                <h3 className="text-xl font-avenir-pro-demi text-foreground mb-3">2. Ask & Analyze</h3>
                <p className="text-brand-mt-rushmore font-avenir-pro">
                  Chat with your documents. Ask complex financial questions and get contextual, citation-linked answers.
                </p>
              </div>
            </div>
            
            {/* Step 3 */}
            <div className="group relative p-8 rounded-2xl bg-gradient-to-br from-card to-card/50 border-2 border-brand-pigeon shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-2 hover:border-accent/30">
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-accent/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
              <div className="relative">
                <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-accent to-accent/80 flex items-center justify-center mb-6 shadow-lg">
                  <BarChart3 className="h-8 w-8 text-accent-foreground" />
                </div>
                <h3 className="text-xl font-avenir-pro-demi text-foreground mb-3">3. Visualize & Act</h3>
                <p className="text-brand-mt-rushmore font-avenir-pro">
                  Transform data into interactive charts, track trends, and make informed financial decisions.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Animated Beam Processing Pipeline */}
      <AnimatedBeamSection />

      {/* Features Showcase */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            {/* Left Content */}
            <div>
              <h2 className="text-3xl md:text-4xl font-avenir-pro-demi text-foreground mb-6">
                Advanced Document Intelligence
              </h2>
              <p className="text-lg font-avenir-pro text-brand-mt-rushmore mb-8">
                Our Claude AI-powered engine understands financial documents like a seasoned analyst, 
                extracting not just data but context and relationships.
              </p>
              
              <div className="space-y-6">
                <div className="flex items-start">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-lust to-brand-lust/80 flex items-center justify-center mr-4 flex-shrink-0">
                    <CheckCircle className="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <h3 className="font-avenir-pro-demi text-foreground mb-1">Multi-format Support</h3>
                    <p className="text-brand-mt-rushmore font-avenir-pro">PDFs, spreadsheets, and financial statements</p>
                  </div>
                </div>
                
                <div className="flex items-start">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-secondary to-secondary/80 flex items-center justify-center mr-4 flex-shrink-0">
                    <CheckCircle className="h-5 w-5 text-secondary-foreground" />
                  </div>
                  <div>
                    <h3 className="font-avenir-pro-demi text-foreground mb-1">Citation Tracking</h3>
                    <p className="text-brand-mt-rushmore font-avenir-pro">Every insight linked back to source documents</p>
                  </div>
                </div>
                
                <div className="flex items-start">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent to-accent/80 flex items-center justify-center mr-4 flex-shrink-0">
                    <CheckCircle className="h-5 w-5 text-accent-foreground" />
                  </div>
                  <div>
                    <h3 className="font-avenir-pro-demi text-foreground mb-1">Real-time Analysis</h3>
                    <p className="text-brand-mt-rushmore font-avenir-pro">Instant financial ratios and trend analysis</p>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Right Visual with brand colors and wave animation */}
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-brand-lust/10 to-accent/10 rounded-3xl blur-xl"></div>
              <div className="relative bg-gradient-to-br from-card to-card/50 rounded-3xl border-2 border-brand-pigeon p-8 shadow-2xl">
                <div className="space-y-4">
                  <Skeleton className="h-4 bg-gradient-to-r from-brand-lust/20 to-brand-lust/10" />
                  <Skeleton className="h-4 bg-gradient-to-r from-secondary/20 to-secondary/10 w-3/4" />
                  <Skeleton className="h-4 bg-gradient-to-r from-accent/20 to-accent/10 w-1/2" />
                  <div className="grid grid-cols-2 gap-4 mt-8">
                    <div className="aspect-square bg-gradient-to-br from-primary/10 to-primary/5 rounded-xl flex items-center justify-center border border-brand-pigeon">
                      <TrendingUp className="h-8 w-8 text-primary" />
                    </div>
                    <div className="aspect-square bg-gradient-to-br from-brand-lust/10 to-brand-lust/5 rounded-xl flex items-center justify-center border border-brand-pigeon">
                      <BarChart3 className="h-8 w-8 text-brand-lust" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Product Categories */}
      <section className="py-20 bg-gradient-to-b from-brand-white-smoke to-background">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-avenir-pro-demi text-foreground mb-4">
              Specialized Analysis Types
            </h2>
            <p className="text-lg font-avenir-pro text-brand-mt-rushmore max-w-2xl mx-auto">
              Choose from our specialized analysis modules designed for different financial document types.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {/* Category 1 */}
            <Link href="/workspace" className="group relative p-6 rounded-2xl bg-gradient-to-br from-card to-card/50 border-2 border-brand-pigeon shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 hover:border-primary/30">
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
              <div className="relative text-center">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5 border border-brand-pigeon flex items-center justify-center mx-auto mb-4">
                  <BarChart3 className="h-10 w-10 text-primary" />
                </div>
                <h3 className="text-xl font-avenir-pro-demi text-foreground mb-3">Financial Statements</h3>
                <p className="text-brand-mt-rushmore font-avenir-pro mb-4">
                  Income statements, balance sheets, and cash flow analysis with automated ratio calculations.
            </p>
                <div className="flex items-center justify-center text-primary group-hover:text-primary/80 transition-colors">
                  <span className="font-avenir-pro-demi text-sm">Explore</span>
                  <ArrowRight className="ml-1 h-4 w-4 transition-transform group-hover:translate-x-1" />
                </div>
              </div>
            </Link>
            
            {/* Category 2 */}
            <Link href="/workspace" className="group relative p-6 rounded-2xl bg-gradient-to-br from-card to-card/50 border-2 border-brand-pigeon shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 hover:border-brand-lust/30">
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-brand-lust/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
              <div className="relative text-center">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-brand-lust/10 to-brand-lust/5 border border-brand-pigeon flex items-center justify-center mx-auto mb-4">
                  <AlertTriangle className="h-10 w-10 text-brand-lust" />
                </div>
                <h3 className="text-xl font-avenir-pro-demi text-foreground mb-3">Risk Assessment</h3>
                <p className="text-brand-mt-rushmore font-avenir-pro mb-4">
                  Identify financial risks, stress test scenarios, and evaluate potential threats to business stability.
                </p>
                <div className="flex items-center justify-center text-brand-lust group-hover:text-brand-lust/80 transition-colors">
                  <span className="font-avenir-pro-demi text-sm">Explore</span>
                  <ArrowRight className="ml-1 h-4 w-4 transition-transform group-hover:translate-x-1" />
                </div>
              </div>
            </Link>
            
            {/* Category 3 */}
            <Link href="/workspace" className="group relative p-6 rounded-2xl bg-gradient-to-br from-card to-card/50 border-2 border-brand-pigeon shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 hover:border-accent/30">
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-accent/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
              <div className="relative text-center">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-accent/10 to-accent/5 border border-brand-pigeon flex items-center justify-center mx-auto mb-4">
                  <FileSearch className="h-10 w-10 text-accent" />
                </div>
                <h3 className="text-xl font-avenir-pro-demi text-foreground mb-3">Due Diligence</h3>
                <p className="text-brand-mt-rushmore font-avenir-pro mb-4">
                  Comprehensive document review, risk identification, and compliance checking for M&A.
                </p>
                <div className="flex items-center justify-center text-accent group-hover:text-accent/80 transition-colors">
                  <span className="font-avenir-pro-demi text-sm">Explore</span>
                  <ArrowRight className="ml-1 h-4 w-4 transition-transform group-hover:translate-x-1" />
                </div>
              </div>
            </Link>
          </div>
        </div>
      </section>

      {/* Social Proof / Testimonials Section */}
      <section className="py-20 bg-background">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-avenir-pro-demi text-foreground mb-4">
              Trusted by Financial Professionals
            </h2>
          </div>
          <AppleCardsCarousel 
            items={testimonialsData.map(testimonial => (
              <TestimonialCard
                key={testimonial.id}
                quote={testimonial.quote}
                name={testimonial.name}
                title={testimonial.title}
                avatarImage={testimonial.avatarImage}
              />
            ))}
          />
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-20 bg-gradient-to-b from-brand-white-smoke to-background">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-avenir-pro-demi text-foreground mb-4">
              Frequently Asked Questions
            </h2>
            <p className="text-lg font-avenir-pro text-brand-mt-rushmore max-w-2xl mx-auto">
              Everything you need to know about our financial document analysis platform.
            </p>
          </div>
          
          <div className="max-w-3xl mx-auto space-y-4">
            {/* FAQ 1 */}
            <details className="group bg-gradient-to-br from-card to-card/50 border-2 border-brand-pigeon rounded-xl p-6 shadow-lg">
              <summary className="flex items-center justify-between cursor-pointer font-avenir-pro-demi text-foreground text-lg">
                How secure is my financial data?
                <ChevronDown className="h-5 w-5 text-brand-mt-rushmore transition-transform group-open:rotate-180" />
              </summary>
              <p className="mt-4 text-brand-mt-rushmore font-avenir-pro">
                We use enterprise-grade encryption and comply with SOC 2 Type II standards. Your documents are processed securely and never stored permanently on our servers.
            </p>
            </details>
            
            {/* FAQ 2 */}
            <details className="group bg-gradient-to-br from-card to-card/50 border-2 border-brand-pigeon rounded-xl p-6 shadow-lg">
              <summary className="flex items-center justify-between cursor-pointer font-avenir-pro-demi text-foreground text-lg">
                What file formats do you support?
                <ChevronDown className="h-5 w-5 text-brand-mt-rushmore transition-transform group-open:rotate-180" />
              </summary>
              <p className="mt-4 text-brand-mt-rushmore font-avenir-pro">
                We support PDF, Excel, Word documents, and most common financial statement formats. Our AI can extract data from both native and scanned documents.
              </p>
            </details>
            
            {/* FAQ 3 */}
            <details className="group bg-gradient-to-br from-card to-card/50 border-2 border-brand-pigeon rounded-xl p-6 shadow-lg">
              <summary className="flex items-center justify-between cursor-pointer font-avenir-pro-demi text-foreground text-lg">
                How accurate is the AI analysis?
                <ChevronDown className="h-5 w-5 text-brand-mt-rushmore transition-transform group-open:rotate-180" />
              </summary>
              <p className="mt-4 text-brand-mt-rushmore font-avenir-pro">
                Our Claude AI achieves 95%+ accuracy on financial data extraction and provides confidence scores for each insight, with full citation tracking for verification.
              </p>
            </details>
            
            {/* FAQ 4 */}
            <details className="group bg-gradient-to-br from-card to-card/50 border-2 border-brand-pigeon rounded-xl p-6 shadow-lg">
              <summary className="flex items-center justify-between cursor-pointer font-avenir-pro-demi text-foreground text-lg">
                Can I integrate with existing workflows?
                <ChevronDown className="h-5 w-5 text-brand-mt-rushmore transition-transform group-open:rotate-180" />
              </summary>
              <p className="mt-4 text-brand-mt-rushmore font-avenir-pro">
                Yes, we offer API access and integrations with popular platforms like Excel, PowerBI, and major accounting software systems.
              </p>
            </details>
          </div>
        </div>
      </section>

      {/* Newsletter Signup */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto text-center">
            <div className="bg-gradient-to-br from-card to-card/50 border-2 border-brand-pigeon rounded-3xl p-12 shadow-2xl relative overflow-hidden">
              {/* Background Elements */}
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-brand-lust/10 to-transparent rounded-full blur-2xl"></div>
              <div className="absolute bottom-0 left-0 w-32 h-32 bg-gradient-to-tr from-secondary/10 to-transparent rounded-full blur-2xl"></div>
              
              <div className="relative">
                <Mail className="h-16 w-16 text-accent mx-auto mb-6" />
                <h2 className="text-3xl md:text-4xl font-avenir-pro-demi text-foreground mb-4">
                  Stay Updated on Financial AI
                </h2>
                <p className="text-lg font-avenir-pro text-brand-mt-rushmore mb-8 max-w-2xl mx-auto">
                  Get the latest insights on AI-powered financial analysis, new features, and industry trends delivered to your inbox.
                </p>
                
                <div className="flex flex-col sm:flex-row gap-4 max-w-md mx-auto">
                  <input
                    type="email"
                    placeholder="Enter your email"
                    className="flex-1 px-4 py-3 rounded-xl border-2 border-brand-pigeon bg-background/50 backdrop-blur-sm text-foreground font-avenir-pro focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                  <button className="group relative px-6 py-3 rounded-xl bg-gradient-to-r from-primary to-primary/90 text-white font-avenir-pro-demi shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
                    <span className="absolute inset-0 rounded-xl bg-gradient-to-r from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></span>
                    <span className="relative">Subscribe</span>
                  </button>
                </div>
                
                <p className="text-sm text-brand-mt-rushmore font-avenir-pro mt-4">
                  No spam. Unsubscribe at any time.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-20 relative overflow-hidden">
        {/* Background Elements */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-brand-lust/5 to-accent/5"></div>
        <div className="absolute top-0 left-0 w-72 h-72 bg-gradient-to-br from-primary/10 to-transparent rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 right-0 w-72 h-72 bg-gradient-to-tl from-brand-lust/10 to-transparent rounded-full blur-3xl"></div>
        
        <div className="relative container mx-auto px-4 text-center">
          <h2 className="text-3xl md:text-5xl font-avenir-pro-demi text-foreground mb-6">
            Ready to Transform Your 
            <span className="bg-gradient-to-r from-primary via-brand-lust to-secondary bg-clip-text text-transparent">
              {" "}Financial Analysis?
            </span>
          </h2>
          <p className="text-lg font-avenir-pro text-brand-mt-rushmore max-w-2xl mx-auto mb-12">
            Join hundreds of financial professionals who are already saving hours with AI-powered document analysis.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <Link 
            href="/workspace" 
              className="group relative inline-flex items-center px-10 py-5 rounded-xl bg-gradient-to-r from-primary to-primary/90 text-white font-avenir-pro-demi text-xl shadow-xl hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-1"
            >
              <span className="absolute inset-0 rounded-xl bg-gradient-to-r from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></span>
              <span className="relative">Start Free Trial</span>
              <ArrowRight className="relative ml-3 h-6 w-6 transition-transform group-hover:translate-x-1" />
            </Link>
            
            <Link 
              href="/dashboard" 
              className="inline-flex items-center text-primary hover:text-primary/80 font-avenir-pro-demi text-lg transition-colors group"
            >
              Explore Dashboard
              <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" />
          </Link>
          </div>
        </div>
      </section>
    </main>
  )
}