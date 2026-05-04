"use client";

import { useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import { motion, useScroll, useTransform } from "motion/react";
import {
  ArrowRight,
  Briefcase,
  GraduationCap,
  Linkedin,
  Sparkles,
  TrendingUp,
  Building2,
  BarChart3,
  Database,
  Users,
  LineChart,
} from "lucide-react";
import { CometCard } from "@/components/ui/comet-card";
import { RainbowButton } from "@/components/ui/rainbow-button";
import { RM_PRO_FORMA_URL } from "@/lib/app-urls";

interface TimelineRole {
  date: string;
  title: string;
  company: string;
  companyDetail?: string;
  description: string;
  highlights?: string[];
  skills?: string[];
  isCurrent?: boolean;
  isEducation?: boolean;
  icon: React.ReactNode;
  accentColor: string;
  logo?: string;
  headerImage?: string;
}

const roles: TimelineRole[] = [
  {
    date: "2025 – Present",
    title: "Director, Enterprise Analytics & Finance Transformation",
    company: "Synovus",
    companyDetail: "Synovus + Pinnacle Merger",
    description:
      "Leading a brand new team — Finance Enterprise Analytics — for the combined bank. The mission: end analytics litigation once and for all. One source. One team. One truth. Building enterprise financial data models that connect finance and business data at the instrument level and turning that foundation into executive scorecards, advisor-level insights, and an analytics platform that scales from CEO to financial advisor.",
    highlights: [
      "Team of 9 A+ analysts & developers consolidated from Community/Commercial Banking, Wholesale Banking, Treasury Payment Services, and BASIS",
      "Enterprise financial data models at the instrument level",
      "Executive scorecards driving producer behavior",
      "Deep connective tissue with data and people leaders across the organization",
    ],
    skills: [
      "Finance Transformation",
      "Enterprise Analytics",
      "Power BI",
      "Team Leadership",
      "Merger Integration",
      "Data Modeling",
    ],
    isCurrent: true,
    icon: <Sparkles className="h-5 w-5" />,
    accentColor: "from-brand-lust to-primary",
    logo: "/assets/logos/synovus.jpeg",
    headerImage: "/assets/logos/synovus-pinnacle.jpeg",
  },
  {
    date: "2023 – 2025",
    title: "Director, Strategic Finance",
    company: "Synovus",
    description:
      "Led Strategic Finance support for Wholesale Banking, Commercial & Investment Banking, and Treasury Payment Solutions segments. Maintained indirect support over the Performance Reporting Power BI-based financial analytics platform that the team built and deployed in the prior role.",
    skills: [
      "Strategic Finance",
      "Wholesale Banking",
      "C&IB",
      "Treasury",
      "Power BI",
      "Financial Analytics",
    ],
    icon: <TrendingUp className="h-5 w-5" />,
    accentColor: "from-primary to-primary/80",
    logo: "/assets/logos/synovus.jpeg",
  },
  {
    date: "2022 – 2023",
    title: "Senior FP&A Manager, Performance Reporting",
    company: "Synovus",
    description:
      "Led a team within Finance specializing in analytical platforms for finance leadership and sales executives. Within 6 months, built and deployed a Power BI, SQL, and SAS financial analytics platform that dramatically increased insight generation by reducing time-to-insight and increasing data discoverability — connecting ERP financial ledger and GL transactional data across the enterprise.",
    skills: [
      "FP&A",
      "Power BI",
      "SQL",
      "SAS",
      "Platform Development",
      "ERP Integration",
    ],
    icon: <BarChart3 className="h-5 w-5" />,
    accentColor: "from-secondary to-secondary/80",
    logo: "/assets/logos/synovus.jpeg",
  },
  {
    date: "2014 – 2022",
    title: "VP, Manager of Financial Analytics",
    company: "First Horizon Bank",
    companyDetail: "Formerly IBERIABANK",
    description:
      "Led a high-performing analyst team delivering financial reporting, forecasting, and consultative support for the $40B+ Regional Banking segment. Trusted liaison to executive leadership in a heavily matrixed organization (C-Suite, LOB leads, sales executives). Consistently recognized as a thought leader driving efficiency and impact across departments through technology. Transformed the team from a traditional reporting group into one focused on proactive profitability analytics.",
    skills: [
      "Financial Reporting",
      "Forecasting",
      "Team Leadership",
      "Profitability Analytics",
      "Executive Liaison",
      "Regional Banking",
    ],
    icon: <Building2 className="h-5 w-5" />,
    accentColor: "from-accent to-accent/80",
    logo: "/assets/logos/first-horizon.jpeg",
  },
  {
    date: "2013 – 2014",
    title: "Asset Liability Analyst",
    company: "Regions Financial Corporation",
    description:
      "Joined the Forecasting & Reporting team within Asset Liability Management (ALM). Responsible for consolidated NII and balance sheet forecast development, risk simulation analyses, and coordinating balance sheet intelligence across business partners. Key focus areas included balance sheet modeling, CCAR stress testing, and interest rate risk analysis.",
    skills: [
      "ALM",
      "NII Forecasting",
      "Balance Sheet Modeling",
      "CCAR",
      "Risk Simulation",
    ],
    icon: <LineChart className="h-5 w-5" />,
    accentColor: "from-primary/70 to-secondary/70",
    logo: "/assets/logos/regions.jpeg",
  },
  {
    date: "2011 – 2013",
    title: "Management Associate — Finance Development Program",
    company: "Regions Financial Corporation",
    description:
      "Two-year rotational program developing cross-functional leadership across Finance, Accounting, and Treasury. Rotations included Investment Portfolio (market monitoring, due diligence, risk collaboration), Investor Relations (earnings materials, rating agency decks, investor targeting), and Corporate Treasury.",
    skills: [
      "Investment Portfolio",
      "Investor Relations",
      "Corporate Treasury",
      "Financial Modeling",
    ],
    icon: <Briefcase className="h-5 w-5" />,
    accentColor: "from-brand-mt-rushmore/60 to-brand-mt-rushmore/40",
    logo: "/assets/logos/regions.jpeg",
  },
  {
    date: "2008 – 2011",
    title: "B.B.A. Finance, Honors Scholar",
    company: "Auburn University",
    companyDetail: "Cum Laude · 3.6 GPA · Graduated in 3 Years",
    description:
      "Graduated cum laude through the Auburn University Honors College in three years with a BBA in Finance. President of the Mu Omega chapter of Alpha Kappa Psi Business Fraternity. Recipient of the Mark Bertus Memorial Scholarship. Founded and coached Lee County Special Olympics Basketball.",
    skills: [
      "Finance",
      "Honors Scholar",
      "Leadership",
      "Security Analysis",
      "Financial Strategy",
    ],
    isEducation: true,
    icon: <GraduationCap className="h-5 w-5" />,
    accentColor: "from-[#03244d] to-[#e87511]",
    logo: "/assets/logos/auburn.png",
  },
];

function TimelineEntry({
  role,
  index,
}: {
  role: TimelineRole;
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 40 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.5, delay: 0.1 }}
      className="relative pl-10 md:pl-16 pb-16 last:pb-0 group"
    >
      {/* Timeline dot */}
      <div
        className={`absolute left-0 top-1 z-10 flex h-8 w-8 md:h-10 md:w-10 items-center justify-center rounded-full border-2 ${
          role.isCurrent
            ? "border-brand-lust bg-gradient-to-br from-brand-lust to-primary text-white shadow-lg shadow-brand-lust/30"
            : role.isEducation
            ? "border-[#03244d] bg-gradient-to-br from-[#03244d] to-[#e87511] text-white"
            : "border-brand-pigeon bg-card text-brand-mt-rushmore group-hover:border-primary group-hover:text-primary transition-colors"
        }`}
      >
        {role.icon}
      </div>

      {/* Connector line (except last) */}
      {index < roles.length - 1 && (
        <div className="absolute left-[15px] md:left-[19px] top-10 md:top-12 bottom-0 w-[2px] bg-gradient-to-b from-brand-pigeon to-brand-pigeon/30" />
      )}

      {/* Content card */}
      <div
        className={`rounded-2xl border-2 overflow-hidden transition-all duration-300 ${
          role.isCurrent
            ? "border-brand-lust/30 bg-gradient-to-br from-card to-brand-lust/5 shadow-xl"
            : "border-brand-pigeon bg-gradient-to-br from-card to-card/50 shadow-lg hover:shadow-xl hover:border-primary/20"
        }`}
      >
        {/* Header image for current role (merger banner) */}
        {role.headerImage && (
          <div className="relative w-full h-28 md:h-36">
            <Image
              src={role.headerImage}
              alt={`${role.company} banner`}
              fill
              className="object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-card" />
          </div>
        )}

        <div className="p-6 md:p-8">
          {/* Date badge + Company logo row */}
          <div className="flex items-start justify-between gap-4 mb-3">
            <div className="flex flex-wrap items-center gap-3">
              <span
                className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-avenir-pro-demi ${
                  role.isCurrent
                    ? "bg-brand-lust/10 text-brand-lust border border-brand-lust/20"
                    : role.isEducation
                    ? "bg-[#03244d]/10 text-[#03244d] border border-[#03244d]/20"
                    : "bg-primary/10 text-primary border border-primary/20"
                }`}
              >
                {role.date}
              </span>
              {role.isCurrent && (
                <span className="inline-flex items-center rounded-full bg-brand-lust/15 px-3 py-1 text-xs font-avenir-pro-demi text-brand-lust border border-brand-lust/25">
                  <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-brand-lust animate-pulse" />
                  Current Role
                </span>
              )}
            </div>

            {/* Company logo */}
            {role.logo && (
              <div className="shrink-0 h-10 w-10 md:h-12 md:w-12 rounded-lg overflow-hidden border border-brand-pigeon/40 bg-white shadow-sm">
                <Image
                  src={role.logo}
                  alt={`${role.company} logo`}
                  width={48}
                  height={48}
                  className="h-full w-full object-contain p-1"
                />
              </div>
            )}
          </div>

          {/* Title */}
          <h3 className="text-xl md:text-2xl font-avenir-pro-demi text-foreground mb-1">
            {role.title}
          </h3>

          {/* Company */}
          <p className="font-avenir-pro-demi text-brand-mt-rushmore mb-1">
            {role.company}
            {role.companyDetail && (
              <span className="font-avenir-pro text-brand-mt-rushmore/70">
                {" "}
                · {role.companyDetail}
              </span>
            )}
          </p>

        {/* Description */}
        <p className="mt-3 font-avenir-pro text-brand-mt-rushmore leading-relaxed">
          {role.description}
        </p>

        {/* Highlights (for current role) */}
        {role.highlights && (
          <ul className="mt-4 space-y-2">
            {role.highlights.map((h) => (
              <li key={h} className="flex items-start text-sm font-avenir-pro text-brand-mt-rushmore">
                <span className="mr-2 mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-lust" />
                {h}
              </li>
            ))}
          </ul>
        )}

        {/* Skills */}
        {role.skills && (
          <div className="mt-4 flex flex-wrap gap-2">
            {role.skills.map((skill) => (
              <span
                key={skill}
                className="rounded-lg bg-background/80 border border-brand-pigeon/60 px-2.5 py-1 text-xs font-avenir-pro text-brand-mt-rushmore"
              >
                {skill}
              </span>
            ))}
          </div>
        )}
        </div>
      </div>
    </motion.div>
  );
}

export default function AboutAlexTimeline() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start end", "end start"],
  });

  const lineHeight = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);

  return (
    <section
      ref={sectionRef}
      id="about-alex"
      className="py-20 bg-gradient-to-b from-brand-white-smoke to-background"
    >
      <div className="container mx-auto px-4">
        <div className="max-w-5xl mx-auto">
          {/* Section Header */}
          <div className="text-center mb-16">
            <div className="inline-flex items-center rounded-full border border-brand-pigeon bg-background/80 px-4 py-2 mb-6">
              <span className="text-sm font-avenir-pro-demi text-brand-lust">
                About Alex
              </span>
            </div>
            <h2 className="text-3xl md:text-5xl font-avenir-pro-demi text-foreground mb-4">
              14+ Years in Finance,{" "}
              <span className="bg-gradient-to-r from-primary via-brand-lust to-secondary bg-clip-text text-transparent">
                Analytics & Leadership
              </span>
            </h2>
            <p className="text-lg font-avenir-pro text-brand-mt-rushmore max-w-3xl mx-auto leading-relaxed">
              From rotational analyst to building a centralized enterprise analytics
              function for a $117B combined bank. Here&apos;s the journey.
            </p>
          </div>

          {/* Profile Header */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="mb-16 flex flex-col md:flex-row items-center gap-8 rounded-3xl border-2 border-brand-pigeon bg-gradient-to-br from-card to-card/50 p-8 shadow-xl"
          >
            {/* Headshot — CometCard 3D tilt */}
            <CometCard className="shrink-0" rotateDepth={16} translateDepth={18}>
              <div className="relative h-40 w-40 md:h-48 md:w-48 overflow-hidden rounded-2xl border-2 border-brand-pigeon shadow-2xl">
                <Image
                  src="/assets/alex-headshot.png"
                  alt="Alex Cardell"
                  width={696}
                  height={1114}
                  className="h-full w-full object-cover object-top"
                  priority
                />
              </div>
            </CometCard>

            {/* Intro text */}
            <div className="text-center md:text-left">
              <h3 className="text-2xl md:text-3xl font-avenir-pro-demi text-foreground mb-2">
                Alex Cardell
              </h3>
              <p className="text-lg font-avenir-pro-demi text-brand-lust mb-3">
                Director, Enterprise Analytics & Finance Transformation
              </p>
              <p className="font-avenir-pro text-brand-mt-rushmore leading-relaxed mb-5 max-w-xl">
                One-part Finance Manager, two-parts AI-enabled analytics product leader. Currently building a centralized enterprise analytics function for a $117B super-regional bank. Here&apos;s the journey.
              </p>
              <div className="flex flex-wrap gap-3 justify-center md:justify-start">
                <RainbowButton
                  href="https://www.linkedin.com/in/alexcardell/"
                  target="_blank"
                  rel="noopener noreferrer"
                  fillColor="#0A66C2"
                  fillColorTo="#0A66C2e6"
                  speed="1.5s"
                  className="px-5 py-2.5 shadow-md hover:shadow-lg"
                >
                  <Linkedin className="mr-2 h-4 w-4" />
                  Connect on LinkedIn
                </RainbowButton>
                <Link
                  href={RM_PRO_FORMA_URL}
                  className="inline-flex items-center rounded-xl border-2 border-brand-pigeon bg-card px-5 py-2.5 text-foreground font-avenir-pro-demi transition-colors hover:bg-brand-white-smoke"
                >
                  View Bank Analysis
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </div>
            </div>
          </motion.div>

          {/* Timeline */}
          <div className="relative">
            {/* Animated progress line overlay */}
            <motion.div
              className="absolute left-[15px] md:left-[19px] top-0 w-[2px] bg-gradient-to-b from-brand-lust via-primary to-secondary origin-top z-[5]"
              style={{ height: lineHeight }}
            />

            {/* Roles */}
            {roles.map((role, i) => (
              <TimelineEntry key={role.date + role.title} role={role} index={i} />
            ))}
          </div>

          {/* Bottom CTA */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="mt-16 text-center"
          >
            <p className="font-avenir-pro text-brand-mt-rushmore mb-4">
              Want to build something together?
            </p>
            <RainbowButton
              href="https://www.linkedin.com/in/alexcardell/"
              target="_blank"
              rel="noopener noreferrer"
              fillColor="#00bed5"
              fillColorTo="#00bed5e6"
              speed="1.5s"
              className="px-6 py-3 shadow-lg hover:shadow-xl"
            >
              <Linkedin className="mr-2 h-4 w-4" />
              Let&apos;s Connect
              <ArrowRight className="ml-2 h-4 w-4" />
            </RainbowButton>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
