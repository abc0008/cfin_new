"use client";

import React, { useRef, useState, useCallback } from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

interface CometCardProps {
  rotateDepth?: number;
  translateDepth?: number;
  className?: string;
  children: React.ReactNode;
}

export function CometCard({
  rotateDepth = 14,
  translateDepth = 16,
  className,
  children,
}: CometCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [rotate, setRotate] = useState({ x: 0, y: 0 });
  const [translate, setTranslate] = useState({ x: 0, y: 0 });
  const [isHovering, setIsHovering] = useState(false);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!cardRef.current) return;
      const rect = cardRef.current.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const px = (e.clientX - cx) / (rect.width / 2);
      const py = (e.clientY - cy) / (rect.height / 2);

      setRotate({ x: -py * rotateDepth, y: px * rotateDepth });
      setTranslate({ x: px * translateDepth, y: py * translateDepth });
    },
    [rotateDepth, translateDepth]
  );

  const handleMouseEnter = useCallback(() => setIsHovering(true), []);
  const handleMouseLeave = useCallback(() => {
    setIsHovering(false);
    setRotate({ x: 0, y: 0 });
    setTranslate({ x: 0, y: 0 });
  }, []);

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      style={{ perspective: "900px" }}
      className={cn("relative", className)}
    >
      <motion.div
        animate={{
          rotateX: rotate.x,
          rotateY: rotate.y,
          translateX: translate.x,
          translateY: translate.y,
        }}
        transition={{ type: "spring", stiffness: 260, damping: 20, mass: 0.6 }}
        className="relative"
        style={{ transformStyle: "preserve-3d" }}
      >
        {/* Comet glow trail — visible on hover */}
        <motion.div
          animate={{
            opacity: isHovering ? 0.6 : 0,
            scale: isHovering ? 1.12 : 0.95,
          }}
          transition={{ duration: 0.35 }}
          className="absolute -inset-3 rounded-3xl bg-gradient-to-br from-brand-lust/30 via-primary/25 to-secondary/30 blur-2xl pointer-events-none"
          style={{ transform: "translateZ(-30px)" }}
        />

        {/* Subtle shine sweep */}
        <motion.div
          animate={{
            opacity: isHovering ? 0.15 : 0,
            backgroundPosition: isHovering ? "200% 0" : "0% 0",
          }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="absolute inset-0 rounded-2xl pointer-events-none overflow-hidden z-10"
          style={{
            background:
              "linear-gradient(105deg, transparent 40%, rgba(255,255,255,0.5) 50%, transparent 60%)",
            backgroundSize: "200% 100%",
          }}
        />

        {/* Card content */}
        <div className="relative" style={{ transform: "translateZ(20px)" }}>
          {children}
        </div>
      </motion.div>
    </div>
  );
}
