"use client";

import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import React, { forwardRef, useEffect, useId, useState } from "react";

export interface AnimatedBeamProps {
  className?: string;
  containerRef: React.RefObject<HTMLElement>; // Container ref
  fromRef: React.RefObject<HTMLElement>; // From element ref
  toRef: React.RefObject<HTMLElement>; // To element ref
  curvature?: number; // Beam curvature
  reverse?: boolean; // Reverse beam direction
  pathColor?: string; // Beam color
  pathWidth?: number; // Beam width
  pathOpacity?: number; // Beam opacity
  gradientStartColor?: string; // Gradient start color
  gradientStopColor?: string; // Gradient stop color
  delay?: number; // Animation delay
  duration?: number; // Animation duration
  startXOffset?: number; // Start x offset
  startYOffset?: number; // Start y offset
  endXOffset?: number; // End x offset
  endYOffset?: number; // End y offset
}

export const AnimatedBeam: React.FC<AnimatedBeamProps> = ({
  className,
  containerRef,
  fromRef,
  toRef,
  curvature = 0,
  reverse = false,
  duration = 5,
  delay = 0,
  pathColor = "gray",
  pathWidth = 2,
  pathOpacity = 0.2,
  gradientStartColor = "#00bed5", // Caribbean Blue
  gradientStopColor = "#8f0f56", // Mulberry
  startXOffset = 0,
  startYOffset = 0,
  endXOffset = 0,
  endYOffset = 0,
}) => {
  const id = useId();
  const [pathD, setPathD] = useState("");
  const [svgDimensions, setSvgDimensions] = useState({ width: 0, height: 0 });

  const gradientId = `gradient-${id}`;

  useEffect(() => {
    const updatePath = () => {
      if (containerRef.current && fromRef.current && toRef.current) {
        const containerRect = containerRef.current.getBoundingClientRect();
        const rectA = fromRef.current.getBoundingClientRect();
        const rectB = toRef.current.getBoundingClientRect();

        const svgWidth = containerRect.width;
        const svgHeight = containerRect.height;
        setSvgDimensions({
          width: svgWidth,
          height: svgHeight,
        });

        const startX =
          rectA.left - containerRect.left + rectA.width / 2 + startXOffset;
        const startY =
          rectA.top - containerRect.top + rectA.height / 2 + startYOffset;
        const endX =
          rectB.left - containerRect.left + rectB.width / 2 + endXOffset;
        const endY =
          rectB.top - containerRect.top + rectB.height / 2 + endYOffset;

        const controlPointX = startX + (endX - startX) / 2;
        const controlPointY = startY - curvature;

        const d = `M ${startX},${startY} Q ${controlPointX},${controlPointY} ${endX},${endY}`;
        setPathD(d);
      }
    };

    // Set up ResizeObserver
    const resizeObserver = new ResizeObserver(() => {
      updatePath();
    });

    // Observe the container
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    // Update path on mount and when refs change
    updatePath();

    // Cleanup
    return () => {
      resizeObserver.disconnect();
    };
  }, [
    containerRef,
    fromRef,
    toRef,
    curvature,
    startXOffset,
    startYOffset,
    endXOffset,
    endYOffset,
  ]);

  return (
    <svg
      fill="none"
      width={svgDimensions.width}
      height={svgDimensions.height}
      xmlns="http://www.w3.org/2000/svg"
      className={cn(
        "pointer-events-none absolute left-0 top-0 transform-gpu stroke-2",
        className
      )}
      viewBox={`0 0 ${svgDimensions.width} ${svgDimensions.height}`}
    >
      <defs>
        <linearGradient
          className={cn("transform-gpu")}
          id={gradientId}
          gradientUnits="userSpaceOnUse"
          x1="0%"
          x2="100%"
          y1="0%"
          y2="0%"
        >
          {reverse ? (
            <>
              <stop offset="0%" stopColor={gradientStopColor} stopOpacity="0" />
              <stop offset="100%" stopColor={gradientStartColor} stopOpacity="1" />
            </>
          ) : (
            <>
              <stop offset="0%" stopColor={gradientStartColor} stopOpacity="1" />
              <stop offset="100%" stopColor={gradientStopColor} stopOpacity="0" />
            </>
          )}
        </linearGradient>
      </defs>
      {pathD && (
        <>
          <motion.path
            d={pathD}
            stroke={pathColor}
            strokeWidth={pathWidth}
            strokeOpacity={pathOpacity}
            fill="none"
          />
          <motion.path
            d={pathD}
            stroke={`url(#${gradientId})`}
            strokeWidth={pathWidth}
            strokeOpacity="1"
            fill="none"
            strokeLinecap="round"
            initial={{
              strokeDasharray: "0 100%",
            }}
            animate={{
              strokeDasharray: ["0 100%", "100% 0"],
            }}
            transition={{
              duration,
              delay,
              repeat: Infinity,
              ease: "linear",
            }}
          />
        </>
      )}
    </svg>
  );
};

// Circle component for the nodes
export const Circle = forwardRef<
  HTMLDivElement,
  { className?: string; children?: React.ReactNode }
>(({ className, children }, ref) => {
  return (
    <div
      ref={ref}
      className={cn(
        "z-10 flex size-12 items-center justify-center rounded-full border-2 bg-white p-3 shadow-[0_0_20px_-12px_rgba(0,0,0,0.8)]",
        className
      )}
    >
      {children}
    </div>
  );
});

Circle.displayName = "Circle"; 