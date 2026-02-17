"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface RainbowButtonProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  /** The solid fill color(s) for the button face, e.g. "#0A66C2" */
  fillColor: string;
  /** Optional second color for gradient fill */
  fillColorTo?: string;
  /** Speed of the rainbow animation */
  speed?: string;
  children: React.ReactNode;
}

/**
 * A link-button with animated rainbow border & glow that preserves
 * the original fill color. Uses brand CSS variables --color-1 … --color-5.
 */
export const RainbowButton = React.forwardRef<HTMLAnchorElement, RainbowButtonProps>(
  ({ fillColor, fillColorTo, speed = "50s", className, children, style, ...props }, ref) => {
    const fill = fillColorTo
      ? `linear-gradient(135deg, ${fillColor}, ${fillColorTo})`
      : fillColor;

    return (
      <a
        ref={ref}
        className={cn(
          "group relative cursor-pointer animate-rainbow",
          "inline-flex items-center justify-center",
          "rounded-xl font-avenir-pro-demi text-white",
          "transition-all duration-300 hover:-translate-y-0.5",
          "overflow-visible",
          className
        )}
        style={
          {
            "--speed": speed,
            /* Three-layer background:
               1) solid fill (visible face)
               2) fill→transparent fade (soft edge)
               3) animated rainbow gradient (border bleed-through) */
            background: [
              fill,
              `linear-gradient(${fillColor} 60%, transparent 100%)`,
              `linear-gradient(90deg, hsl(var(--color-1)), hsl(var(--color-5)), hsl(var(--color-3)), hsl(var(--color-4)), hsl(var(--color-2)))`,
            ].join(", "),
            backgroundSize: "200%",
            backgroundClip: "padding-box, border-box, border-box",
            backgroundOrigin: "border-box",
            border: "2px solid transparent",
            ...style,
          } as React.CSSProperties
        }
        {...props}
      >
        {/* Rainbow glow beneath the button */}
        <span
          className="pointer-events-none absolute -bottom-[20%] left-1/2 z-0 h-1/4 w-3/5 -translate-x-1/2 animate-rainbow opacity-70 blur-lg"
          style={{
            background:
              "linear-gradient(90deg, hsl(var(--color-1)), hsl(var(--color-5)), hsl(var(--color-3)), hsl(var(--color-4)), hsl(var(--color-2)))",
            backgroundSize: "200%",
          }}
          aria-hidden
        />
        {/* Content */}
        <span className="relative z-10 flex items-center">{children}</span>
      </a>
    );
  }
);

RainbowButton.displayName = "RainbowButton";
