"use client";

import { forwardRef, useRef } from "react";
import { motion } from "framer-motion";
import { AnimatedBeam, Circle } from "@/components/ui/animated-beam";
import Image from "next/image";
import { cn } from "@/lib/utils";

const IconWrapper = forwardRef<
  HTMLDivElement,
  { children: React.ReactNode; className?: string }
>(({ children, className }, ref) => {
  return (
    <Circle ref={ref} className={cn("relative z-10", className)}>
      {children}
    </Circle>
  );
});

IconWrapper.displayName = "IconWrapper";

export default function AnimatedBeamSection() {
  const containerRef = useRef<HTMLDivElement>(null);
  const pdfRef = useRef<HTMLDivElement>(null);
  const excelRef = useRef<HTMLDivElement>(null);
  const wordRef = useRef<HTMLDivElement>(null);
  const claudeRef = useRef<HTMLDivElement>(null);
  const dashboardRef = useRef<HTMLDivElement>(null);
  const chatRef = useRef<HTMLDivElement>(null);

  return (
    <section className="py-24 bg-gradient-to-br from-white via-blue-50/30 to-purple-50/20">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl font-bold text-nero mb-6">
            Intelligent Document Processing Pipeline
          </h2>
          <p className="text-xl text-smokescreen max-w-3xl mx-auto">
            Watch how our AI transforms your financial documents into actionable insights through our seamless processing workflow.
          </p>
        </motion.div>

        {/* Animated Beam Container */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          viewport={{ once: true }}
          className="relative mx-auto max-w-6xl"
        >
          <div className="relative h-80 rounded-3xl bg-gradient-to-r from-white/80 via-white/60 to-white/80 backdrop-blur-sm border border-white/20 shadow-2xl overflow-hidden">
            {/* Background gradients */}
            <div className="absolute inset-0 bg-gradient-to-r from-mulberry/5 via-transparent to-caribbean-blue/5" />
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(143,15,86,0.1),transparent_50%)]" />
            
            <div ref={containerRef} className="relative w-full h-full p-8">
              {/* Input Documents - Left Side */}
              <IconWrapper 
                ref={pdfRef} 
                className="absolute left-8 top-12 w-16 h-16 bg-gradient-to-br from-lust/10 to-lust/20 border-2 border-lust/30 shadow-lg hover:scale-110 transition-transform duration-300"
              >
                <Image
                  src="/icons/pdf-svgrepo-com.svg"
                  alt="PDF"
                  width={32}
                  height={32}
                  className="filter brightness-0 saturate-100"
                  style={{ filter: 'invert(15%) sepia(95%) saturate(6765%) hue-rotate(347deg) brightness(92%) contrast(101%)' }} // Lust color filter
                />
              </IconWrapper>

              <IconWrapper 
                ref={excelRef} 
                className="absolute left-8 top-1/2 transform -translate-y-1/2 w-16 h-16 bg-gradient-to-br from-hobgoblin/10 to-hobgoblin/20 border-2 border-hobgoblin/30 shadow-lg hover:scale-110 transition-transform duration-300"
              >
                <Image
                  src="/icons/ms-excel-svgrepo-com.svg"
                  alt="Excel"
                  width={32}
                  height={32}
                />
              </IconWrapper>

              <IconWrapper 
                ref={wordRef} 
                className="absolute left-8 bottom-12 w-16 h-16 bg-gradient-to-br from-mt-rushmore/10 to-mt-rushmore/20 border-2 border-mt-rushmore/30 shadow-lg hover:scale-110 transition-transform duration-300"
              >
                <Image
                  src="/icons/ms-word-svgrepo-com.svg"
                  alt="Word"
                  width={32}
                  height={32}
                />
              </IconWrapper>

              {/* Central Processing - Claude AI */}
              <IconWrapper 
                ref={claudeRef} 
                className="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 w-20 h-20 bg-gradient-to-br from-mulberry/20 to-mulberry/30 border-3 border-mulberry/40 shadow-xl hover:scale-110 transition-transform duration-300"
              >
                <Image
                  src="/icons/claude-ai-icon.svg"
                  alt="Claude AI"
                  width={40}
                  height={40}
                />
              </IconWrapper>

              {/* Output Insights - Right Side */}
              <IconWrapper 
                ref={dashboardRef} 
                className="absolute right-8 top-1/4 transform -translate-y-1/2 w-16 h-16 bg-gradient-to-br from-caribbean-blue/10 to-caribbean-blue/20 border-2 border-caribbean-blue/30 shadow-lg hover:scale-110 transition-transform duration-300"
              >
                <Image
                  src="/icons/dashboard-svgrepo-com.svg"
                  alt="Dashboard"
                  width={32}
                  height={32}
                  className="filter brightness-0 saturate-100"
                  style={{ filter: 'invert(61%) sepia(39%) saturate(2834%) hue-rotate(162deg) brightness(101%) contrast(101%)' }} // Caribbean Blue color filter
                />
              </IconWrapper>

              <IconWrapper 
                ref={chatRef} 
                className="absolute right-8 bottom-1/4 transform translate-y-1/2 w-16 h-16 bg-gradient-to-br from-lust/10 to-lust/20 border-2 border-lust/30 shadow-lg hover:scale-110 transition-transform duration-300"
              >
                <Image
                  src="/icons/chat-round-unread-svgrepo-com.svg"
                  alt="Chat Analysis"
                  width={32}
                  height={32}
                  className="filter brightness-0 saturate-100"
                  style={{ filter: 'invert(15%) sepia(95%) saturate(6765%) hue-rotate(347deg) brightness(92%) contrast(101%)' }} // Lust color filter
                />
              </IconWrapper>

              {/* Animated Beams */}
              <AnimatedBeam
                containerRef={containerRef}
                fromRef={pdfRef}
                toRef={claudeRef}
                curvature={-20}
                duration={3}
                delay={0}
                gradientStartColor="#e5241d"
                gradientStopColor="#8f0f56"
              />
              <AnimatedBeam
                containerRef={containerRef}
                fromRef={excelRef}
                toRef={claudeRef}
                curvature={0}
                duration={3.5}
                delay={0.5}
                gradientStartColor="#02a88e"
                gradientStopColor="#8f0f56"
              />
              <AnimatedBeam
                containerRef={containerRef}
                fromRef={wordRef}
                toRef={claudeRef}
                curvature={20}
                duration={4}
                delay={1}
                gradientStartColor="#828282"
                gradientStopColor="#8f0f56"
              />
              <AnimatedBeam
                containerRef={containerRef}
                fromRef={claudeRef}
                toRef={dashboardRef}
                curvature={-15}
                duration={3.2}
                delay={1.5}
                gradientStartColor="#8f0f56"
                gradientStopColor="#00bed5"
              />
              <AnimatedBeam
                containerRef={containerRef}
                fromRef={claudeRef}
                toRef={chatRef}
                curvature={15}
                duration={3.8}
                delay={2}
                gradientStartColor="#8f0f56"
                gradientStopColor="#e5241d"
              />
            </div>
          </div>
        </motion.div>

        {/* Feature Cards */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          viewport={{ once: true }}
          className="grid md:grid-cols-3 gap-8 mt-16"
        >
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-gradient-to-r from-lust to-mulberry flex items-center justify-center">
              <span className="text-white font-bold text-lg">1</span>
            </div>
            <h3 className="text-xl font-semibold text-nero mb-2">Document Upload</h3>
            <p className="text-smokescreen">
              Upload PDF, Excel, or Word documents containing your financial data for analysis.
            </p>
          </div>
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-gradient-to-r from-mulberry to-hobgoblin flex items-center justify-center">
              <span className="text-white font-bold text-lg">2</span>
            </div>
            <h3 className="text-xl font-semibold text-nero mb-2">AI Processing</h3>
            <p className="text-smokescreen">
              Claude AI extracts, analyzes, and interprets financial data with unprecedented accuracy.
            </p>
          </div>
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-gradient-to-r from-hobgoblin to-caribbean-blue flex items-center justify-center">
              <span className="text-white font-bold text-lg">3</span>
            </div>
            <h3 className="text-xl font-semibold text-nero mb-2">Insights & Analysis</h3>
            <p className="text-smokescreen">
              Get interactive dashboards and conversational analysis of your financial data.
            </p>
          </div>
        </motion.div>
      </div>
    </section>
  );
} 