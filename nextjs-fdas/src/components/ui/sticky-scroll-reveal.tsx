"use client";
import React, { useEffect, useRef, useState } from "react";
import { useMotionValueEvent, useScroll } from "motion/react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

export const StickyScroll = ({
  content,
  contentClassName,
}: {
  content: {
    title: string;
    description: string;
    content?: React.ReactNode | any;
  }[];
  contentClassName?: string;
}) => {
  const [activeCard, setActiveCard] = React.useState(0);
  const ref = useRef<any>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });
  const cardLength = content.length;

  useMotionValueEvent(scrollYProgress, "change", (latest) => {
    const cardsBreakpoints = content.map((_, index) => index / cardLength);
    const closestBreakpointIndex = cardsBreakpoints.reduce(
      (acc, breakpoint, index) => {
        const distance = Math.abs(latest - breakpoint);
        if (distance < Math.abs(latest - cardsBreakpoints[acc])) {
          return index;
        }
        return acc;
      },
      0,
    );
    setActiveCard(closestBreakpointIndex);
  });

  const backgroundColors = [
    "#0c1222",
    "#0a1628",
    "#0e1520",
    "#10141c",
  ];

  return (
    <motion.div
      ref={ref}
      animate={{
        backgroundColor: backgroundColors[activeCard % backgroundColors.length],
      }}
      className="relative flex justify-between gap-10 rounded-2xl p-10"
    >
      <div className="relative flex items-start px-4">
        <div className="max-w-xl">
          {content.map((item, index) => (
            <div key={item.title + index} className="min-h-[24rem] flex flex-col justify-center py-10">
              <motion.h2
                initial={{ opacity: 0 }}
                animate={{ opacity: activeCard === index ? 1 : 0.3 }}
                className="text-2xl md:text-3xl font-avenir-pro-demi text-white"
              >
                {item.title}
              </motion.h2>
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: activeCard === index ? 1 : 0.3 }}
                className="text-base md:text-lg mt-6 max-w-md font-avenir-pro text-white/70 leading-relaxed"
              >
                {item.description}
              </motion.p>
            </div>
          ))}
        </div>
      </div>
      <div
        className={cn(
          "sticky top-24 hidden h-[24rem] w-[24rem] shrink-0 self-start overflow-hidden rounded-2xl md:block",
          contentClassName,
        )}
      >
        {content[activeCard].content ?? null}
      </div>
    </motion.div>
  );
};
