"use client";

import React, { useEffect, useRef, useState } from "react";
import { useInView } from "motion/react";
import { cn } from "@/lib/utils";

type EncryptedTextProps = {
  text: string;
  className?: string;
  revealDelayMs?: number;
  startDelayMs?: number;
  charset?: string;
  flipDelayMs?: number;
  encryptedClassName?: string;
  revealedClassName?: string;
  trigger?: boolean;
};

const DEFAULT_CHARSET =
  "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-={}[];:,.<>/?";

function generateRandomCharacter(charset: string): string {
  const index = Math.floor(Math.random() * charset.length);
  return charset.charAt(index);
}

function generateGibberishPreservingSpaces(
  original: string,
  charset: string
): string {
  if (!original) return "";

  let result = "";
  for (let index = 0; index < original.length; index += 1) {
    const char = original[index];
    result += char === " " ? " " : generateRandomCharacter(charset);
  }
  return result;
}

export function EncryptedText({
  text,
  className,
  revealDelayMs = 50,
  startDelayMs = 0,
  charset = DEFAULT_CHARSET,
  flipDelayMs = 50,
  encryptedClassName,
  revealedClassName,
  trigger = true,
}: EncryptedTextProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true, amount: 0.6 });

  const [revealCount, setRevealCount] = useState(text.length);
  const [hasStarted, setHasStarted] = useState(false);
  const [, setRenderTick] = useState(0);
  const animationFrameRef = useRef<number | null>(null);
  const startTimeRef = useRef<number>(0);
  const lastFlipTimeRef = useRef<number>(0);
  const scrambleCharsRef = useRef<string[]>(text.split(""));

  useEffect(() => {
    scrambleCharsRef.current = text.split("");
    setRevealCount(text.length);
    setRenderTick((value) => value + 1);
  }, [text]);

  useEffect(() => {
    if (!trigger || !isInView || !text) return;

    let isCancelled = false;
    let timeoutId: number | null = null;
    setHasStarted(false);

    const update = (now: number) => {
      if (isCancelled) return;

      const elapsedMs = now - startTimeRef.current;
      const totalLength = text.length;
      const currentRevealCount = Math.min(
        totalLength,
        Math.floor(elapsedMs / Math.max(1, revealDelayMs))
      );

      setRevealCount(currentRevealCount);

      if (currentRevealCount >= totalLength) {
        return;
      }

      if (now - lastFlipTimeRef.current >= Math.max(0, flipDelayMs)) {
        for (let index = currentRevealCount; index < totalLength; index += 1) {
          scrambleCharsRef.current[index] =
            text[index] === " " ? " " : generateRandomCharacter(charset);
        }
        lastFlipTimeRef.current = now;
        setRenderTick((value) => value + 1);
      }

      animationFrameRef.current = requestAnimationFrame(update);
    };

    const begin = () => {
      if (isCancelled) return;
      setHasStarted(true);
      scrambleCharsRef.current = generateGibberishPreservingSpaces(
        text,
        charset
      ).split("");
      setRevealCount(0);
      setRenderTick((value) => value + 1);
      startTimeRef.current = performance.now();
      lastFlipTimeRef.current = startTimeRef.current;
      animationFrameRef.current = requestAnimationFrame(update);
    };

    if (startDelayMs > 0) {
      timeoutId = window.setTimeout(begin, startDelayMs);
    } else {
      begin();
    }

    return () => {
      isCancelled = true;
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
      }
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [trigger, isInView, text, revealDelayMs, startDelayMs, charset, flipDelayMs]);

  if (!text) return null;

  return (
    <span
      ref={ref}
      className={cn(className)}
      aria-label={text}
      role="text"
      style={
        trigger && isInView && !hasStarted ? { opacity: 0 } : undefined
      }
    >
      {text.split("").map((char, index) => {
        const isRevealed = index < revealCount;
        const displayChar = isRevealed
          ? char
          : char === " "
            ? " "
            : (scrambleCharsRef.current[index] ??
              generateRandomCharacter(charset));

        return (
          <span
            key={`${char}-${index}`}
            className={cn(isRevealed ? revealedClassName : encryptedClassName)}
          >
            {displayChar}
          </span>
        );
      })}
    </span>
  );
}
