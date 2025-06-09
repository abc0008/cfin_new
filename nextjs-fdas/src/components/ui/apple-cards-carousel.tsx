"use client";
import React, {
  useEffect,
  useRef,
  useState,
} from "react";
import { IconArrowNarrowLeft, IconArrowNarrowRight } from "@tabler/icons-react";
import { cn } from "@/lib/utils";
import { motion } from "motion/react";

export const AppleCardsCarousel = ({ items, initialScroll = 0 }: { items: React.ReactNode[]; initialScroll?: number; }) => {
  const carouselRef = useRef<HTMLDivElement | null>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);
  const scrollIntervalRef = useRef<number | null>(null);

  useEffect(() => {
    if (carouselRef.current) {
      carouselRef.current.scrollLeft = initialScroll;
      checkScrollability();
    }
  }, [initialScroll]);

  const checkScrollability = () => {
    if (carouselRef.current) {
      const { scrollLeft, scrollWidth, clientWidth } = carouselRef.current;
      setCanScrollLeft(scrollLeft > 0);
      setCanScrollRight(scrollLeft < scrollWidth - clientWidth);
    }
  };

  const scrollLeftFn = () => {
    if (carouselRef.current) {
      carouselRef.current.scrollBy({ left: -300, behavior: "smooth" });
    }
  };

  const scrollRightFn = () => {
    if (carouselRef.current) {
      carouselRef.current.scrollBy({ left: 300, behavior: "smooth" });
    }
  };

  useEffect(() => {
    startAutoScroll();
    return () => {
      stopAutoScroll();
    };
  }, []);

  const startAutoScroll = () => {
    if (scrollIntervalRef.current) return;

    scrollIntervalRef.current = window.setInterval(() => {
      if (carouselRef.current) {
        const { scrollLeft, scrollWidth, clientWidth } = carouselRef.current;
        if (scrollLeft >= scrollWidth - clientWidth - 1) {
          carouselRef.current.scrollTo({ left: 0, behavior: "smooth" });
        } else {
          scrollRightFn();
        }
      }
    }, 4000);
  };

  const stopAutoScroll = () => {
    if (scrollIntervalRef.current) {
      clearInterval(scrollIntervalRef.current);
      scrollIntervalRef.current = null;
    }
  };

  const handleMouseEnter = () => {
    stopAutoScroll();
  };

  const handleMouseLeave = () => {
    startAutoScroll();
  };

  return (
    <div className="relative w-full">
      <button
        onClick={scrollLeftFn}
        disabled={!canScrollLeft}
        className={cn(
          "absolute left-2 top-1/2 z-20 transform -translate-y-1/2 bg-white rounded-full p-2 shadow-md hover:shadow-lg transition-shadow",
          !canScrollLeft && "opacity-30 cursor-not-allowed"
        )}
        aria-label="Scroll left"
      >
        <IconArrowNarrowLeft size={20} className="text-neutral-600" />
      </button>

      {/* Left Gradient Overlay */}
      {canScrollLeft && (
         <div className="absolute left-0 top-0 bottom-0 z-10 h-full w-[5%] md:w-[8%] bg-gradient-to-r from-white via-white/70 to-transparent pointer-events-none"></div>
      )}

      <div
        ref={carouselRef}
        onScroll={checkScrollability}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        className="flex w-full overflow-x-scroll overscroll-x-auto scroll-smooth py-3 [scrollbar-width:none] md:py-7"
      >
        <div className="flex flex-row justify-start gap-4 pl-4 mx-auto"> 
          {items.map((item, index) => (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0, transition: { duration: 0.5, delay: 0.2 * index, ease: "easeOut" } }}
              key={"card" + index}
              className="rounded-3xl shrink-0"
            >
              {item}
            </motion.div>
          ))}
        </div>
      </div>

      {/* Right Gradient Overlay */}
      {canScrollRight && (
        <div className="absolute right-0 top-0 bottom-0 z-10 h-full w-[5%] md:w-[8%] bg-gradient-to-l from-white via-white/70 to-transparent pointer-events-none"></div>
      )}

      <button
        onClick={scrollRightFn}
        disabled={!canScrollRight}
        className={cn(
          "absolute right-2 top-1/2 z-20 transform -translate-y-1/2 bg-white rounded-full p-2 shadow-md hover:shadow-lg transition-shadow",
          !canScrollRight && "opacity-30 cursor-not-allowed"
        )}
        aria-label="Scroll right"
      >
        <IconArrowNarrowRight size={20} className="text-neutral-600" />
      </button>
    </div>
  );
};
