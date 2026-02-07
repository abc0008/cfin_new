'use client';

import { useEffect, useRef, useCallback } from 'react';

interface PerformanceMetrics {
  citationLoadTime: number[];
  pdfLoadTime: number[];
  searchTime: number[];
  navigationTime: number[];
  memoryUsage: number[];
  cacheHitRate: number;
}

interface PerformanceEvent {
  type: 'citation_load' | 'pdf_load' | 'search' | 'navigation';
  duration: number;
  metadata?: Record<string, any>;
}

export function usePerformanceMonitor() {
  const metrics = useRef<PerformanceMetrics>({
    citationLoadTime: [],
    pdfLoadTime: [],
    searchTime: [],
    navigationTime: [],
    memoryUsage: [],
    cacheHitRate: 0
  });

  const timers = useRef<Map<string, number>>(new Map());

  const startTimer = useCallback((id: string) => {
    timers.current.set(id, performance.now());
  }, []);

  const endTimer = useCallback((id: string): number => {
    const startTime = timers.current.get(id);
    if (!startTime) {
      console.warn(`No start time found for timer: ${id}`);
      return 0;
    }
    
    const duration = performance.now() - startTime;
    timers.current.delete(id);
    return duration;
  }, []);

  const recordEvent = useCallback((event: PerformanceEvent) => {
    switch (event.type) {
      case 'citation_load':
        metrics.current.citationLoadTime.push(event.duration);
        break;
      case 'pdf_load':
        metrics.current.pdfLoadTime.push(event.duration);
        break;
      case 'search':
        metrics.current.searchTime.push(event.duration);
        break;
      case 'navigation':
        metrics.current.navigationTime.push(event.duration);
        break;
    }

    // Keep only last 100 measurements to avoid memory issues
    Object.keys(metrics.current).forEach(key => {
      const metricValue = metrics.current[key as keyof PerformanceMetrics];
      if (Array.isArray(metricValue) && metricValue.length > 100) {
        (metrics.current as any)[key] = metricValue.slice(-100);
      }
    });

    // Log slow operations
    if (event.duration > 1000) {
      console.warn(`Slow ${event.type} operation: ${event.duration.toFixed(2)}ms`, event.metadata);
    }
  }, []);

  const measureCitationLoad = useCallback(async <T,>(
    citationId: string,
    loadFn: () => Promise<T>
  ): Promise<T> => {
    startTimer(`citation_${citationId}`);
    try {
      const result = await loadFn();
      const duration = endTimer(`citation_${citationId}`);
      recordEvent({ type: 'citation_load', duration, metadata: { citationId } });
      return result;
    } catch (error) {
      endTimer(`citation_${citationId}`);
      throw error;
    }
  }, [startTimer, endTimer, recordEvent]);

  const measurePdfLoad = useCallback(async <T,>(
    documentId: string,
    loadFn: () => Promise<T>
  ): Promise<T> => {
    startTimer(`pdf_${documentId}`);
    try {
      const result = await loadFn();
      const duration = endTimer(`pdf_${documentId}`);
      recordEvent({ type: 'pdf_load', duration, metadata: { documentId } });
      return result;
    } catch (error) {
      endTimer(`pdf_${documentId}`);
      throw error;
    }
  }, [startTimer, endTimer, recordEvent]);

  const measureSearch = useCallback(async <T,>(
    searchText: string,
    searchFn: () => Promise<T>
  ): Promise<T> => {
    const searchId = `search_${Date.now()}`;
    startTimer(searchId);
    try {
      const result = await searchFn();
      const duration = endTimer(searchId);
      recordEvent({ type: 'search', duration, metadata: { searchText } });
      return result;
    } catch (error) {
      endTimer(searchId);
      throw error;
    }
  }, [startTimer, endTimer, recordEvent]);

  // Monitor memory usage
  useEffect(() => {
    if (!('memory' in performance)) return;

    const checkMemory = () => {
      const memory = (performance as any).memory;
      if (memory) {
        const usedMB = memory.usedJSHeapSize / (1024 * 1024);
        metrics.current.memoryUsage.push(usedMB);
        
        // Warn if memory usage is high
        if (usedMB > 500) {
          console.warn(`High memory usage: ${usedMB.toFixed(2)}MB`);
        }
      }
    };

    const interval = setInterval(checkMemory, 10000); // Check every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const getMetricsSummary = useCallback(() => {
    const average = (arr: number[]) => 
      arr.length > 0 ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;

    const percentile = (arr: number[], p: number) => {
      if (arr.length === 0) return 0;
      const sorted = [...arr].sort((a, b) => a - b);
      const index = Math.ceil(sorted.length * p / 100) - 1;
      return sorted[index] || 0;
    };

    return {
      citationLoad: {
        average: average(metrics.current.citationLoadTime),
        p95: percentile(metrics.current.citationLoadTime, 95),
        count: metrics.current.citationLoadTime.length
      },
      pdfLoad: {
        average: average(metrics.current.pdfLoadTime),
        p95: percentile(metrics.current.pdfLoadTime, 95),
        count: metrics.current.pdfLoadTime.length
      },
      search: {
        average: average(metrics.current.searchTime),
        p95: percentile(metrics.current.searchTime, 95),
        count: metrics.current.searchTime.length
      },
      navigation: {
        average: average(metrics.current.navigationTime),
        p95: percentile(metrics.current.navigationTime, 95),
        count: metrics.current.navigationTime.length
      },
      memory: {
        current: metrics.current.memoryUsage[metrics.current.memoryUsage.length - 1] || 0,
        average: average(metrics.current.memoryUsage),
        max: Math.max(...metrics.current.memoryUsage, 0)
      },
      cacheHitRate: metrics.current.cacheHitRate
    };
  }, []);

  // Log performance summary periodically in development
  useEffect(() => {
    if (process.env.NODE_ENV !== 'development') return;

    const logSummary = () => {
      const summary = getMetricsSummary();
      console.log('Performance Summary:', summary);
    };

    const interval = setInterval(logSummary, 60000); // Every minute
    return () => clearInterval(interval);
  }, [getMetricsSummary]);

  return {
    measureCitationLoad,
    measurePdfLoad,
    measureSearch,
    startTimer,
    endTimer,
    recordEvent,
    getMetricsSummary
  };
}