"use client";
import React from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { StickyScroll } from "@/components/ui/sticky-scroll-reveal";
import { RM_PRO_FORMA_URL } from "@/lib/app-urls";

function AppCard({
  logo,
  href,
  label,
  gradientFrom,
  gradientTo,
}: {
  logo: string;
  href: string;
  label: string;
  gradientFrom: string;
  gradientTo: string;
}) {
  return (
    <div className="relative flex h-full w-full flex-col items-center justify-end rounded-2xl overflow-hidden border-2 border-white/10">
      <img
        src={logo}
        alt={label}
        className="absolute inset-0 h-full w-full object-cover"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent" />
      <Link
        href={href}
        className={`group relative z-10 mb-8 inline-flex items-center justify-center overflow-hidden rounded-xl bg-gradient-to-r ${gradientFrom} ${gradientTo} px-6 py-3 font-avenir-pro-demi text-white shadow-lg transition-all duration-300 hover:shadow-xl hover:-translate-y-0.5 hover:scale-105`}
      >
        {/* Base state */}
        <span className="relative z-10 flex items-center gap-2 transition-all duration-300 group-hover:opacity-0 group-hover:-translate-x-8">
          <span className="h-2 w-2 rounded-full bg-white/90 transition-transform duration-300 group-hover:scale-[85]" />
          <span>{label}</span>
        </span>

        {/* Hover state */}
        <span className="pointer-events-none absolute inset-0 z-20 flex items-center justify-center gap-2 opacity-0 translate-x-8 transition-all duration-300 group-hover:translate-x-0 group-hover:opacity-100">
          <span>{label}</span>
          <ArrowRight className="h-4 w-4" />
        </span>
      </Link>
    </div>
  );
}

const appScrollContent = [
  {
    title: "Agentic PDF Financial Analysis",
    description:
      "Upload financial PDFs and instantly chat with your documents. CFIN uses Claude AI to extract structured data, generate citation-linked insights, and produce interactive charts — taking you from source document to dashboard-ready analysis in minutes.",
    content: (
      <AppCard
        logo="/assets/finance-pdf-analysis-logo.png"
        href="/cfin"
        label="Open CFIN"
        gradientFrom="from-[#8f0f56]"
        gradientTo="to-[#8f0f56]/90"
      />
    ),
  },
  {
    title: "Text2SQL — Natural Language to Database",
    description:
      "Ask plain-English questions against banking datasets and get explainable SQL, data tables, and auto-generated visuals. Guided Mode walks you through schema selection, while Refine Mode lets power users iterate on queries with full transparency.",
    content: (
      <AppCard
        logo="/assets/text2sql-logo.png"
        href="/text2sql"
        label="Open Text2SQL"
        gradientFrom="from-[#6c757d]"
        gradientTo="to-[#6c757d]/90"
      />
    ),
  },
  {
    title: "Bank Analysis — RM Pro Forma & Pipeline",
    description:
      "Model new-hire relationship manager economics with RM Pro Forma: balance sheet build, fee revenue, direct expenses, and cumulative payback analysis. Pipeline Kanban tracks your loan pipeline with drag-and-drop stage management and real-time metrics.",
    content: (
      <AppCard
        logo="/assets/bank-analysis-logo.png"
        href={RM_PRO_FORMA_URL}
        label="Open Bank Analysis"
        gradientFrom="from-[#02a88e]"
        gradientTo="to-[#02a88e]/90"
      />
    ),
  },
  {
    title: "Social Ketchup — AI Signal Filtering",
    description:
      "Cut through social noise to surface the finance and analytics discussions that matter. Social Ketchup monitors your curated account list, filters posts through AI relevance scoring, and delivers a clean feed of high-signal content for your daily digest.",
    content: (
      <AppCard
        logo="/assets/social-ketchup-best.png"
        href="https://socialketchup.vercel.app"
        label="Open Social Ketchup"
        gradientFrom="from-[#e5241d]"
        gradientTo="to-[#8f0f56]/90"
      />
    ),
  },
];

export default function AppShowcaseScroll() {
  return (
    <section className="py-16">
      <div className="container mx-auto px-4">
        <div className="mb-10 text-center">
          <h2 className="text-3xl md:text-4xl font-avenir-pro-demi text-foreground mb-3">
            Explore the Platform
          </h2>
          <p className="text-lg font-avenir-pro text-brand-mt-rushmore max-w-2xl mx-auto">
            Scroll through each app to see what it does, then launch it directly.
          </p>
        </div>
        <div className="max-w-6xl mx-auto">
          <StickyScroll content={appScrollContent} />
        </div>
      </div>
    </section>
  );
}
