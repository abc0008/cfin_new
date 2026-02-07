import { Citation } from '@/types/citation';

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiresAt: number;
}

interface CacheOptions {
  ttl?: number; // Time to live in milliseconds
  maxSize?: number; // Maximum number of entries
}

export class CitationCache {
  private cache: Map<string, CacheEntry<Citation>>;
  private documentCitationsCache: Map<string, CacheEntry<Citation[]>>;
  private fileIdCache: Map<string, CacheEntry<string>>;
  private ttl: number;
  private maxSize: number;
  private accessOrder: string[];

  constructor(options: CacheOptions = {}) {
    this.cache = new Map();
    this.documentCitationsCache = new Map();
    this.fileIdCache = new Map();
    this.ttl = options.ttl || 1000 * 60 * 30; // 30 minutes default
    this.maxSize = options.maxSize || 1000;
    this.accessOrder = [];
  }

  // Citation caching
  setCitation(citation: Citation): void {
    this.evictIfNeeded();
    
    const entry: CacheEntry<Citation> = {
      data: citation,
      timestamp: Date.now(),
      expiresAt: Date.now() + this.ttl
    };
    
    this.cache.set(citation.id, entry);
    this.updateAccessOrder(citation.id);
  }

  getCitation(id: string): Citation | null {
    const entry = this.cache.get(id);
    
    if (!entry) return null;
    
    if (Date.now() > entry.expiresAt) {
      this.cache.delete(id);
      return null;
    }
    
    this.updateAccessOrder(id);
    return entry.data;
  }

  // Document citations caching
  setDocumentCitations(documentId: string, citations: Citation[]): void {
    const entry: CacheEntry<Citation[]> = {
      data: citations,
      timestamp: Date.now(),
      expiresAt: Date.now() + this.ttl
    };
    
    this.documentCitationsCache.set(documentId, entry);
    
    // Also cache individual citations
    citations.forEach(citation => this.setCitation(citation));
  }

  getDocumentCitations(documentId: string): Citation[] | null {
    const entry = this.documentCitationsCache.get(documentId);
    
    if (!entry) return null;
    
    if (Date.now() > entry.expiresAt) {
      this.documentCitationsCache.delete(documentId);
      return null;
    }
    
    return entry.data;
  }

  // File ID caching for Files API
  setFileId(documentId: string, fileId: string): void {
    const entry: CacheEntry<string> = {
      data: fileId,
      timestamp: Date.now(),
      expiresAt: Date.now() + (1000 * 60 * 60 * 24 * 7) // 7 days for file IDs
    };
    
    this.fileIdCache.set(documentId, entry);
  }

  getFileId(documentId: string): string | null {
    const entry = this.fileIdCache.get(documentId);
    
    if (!entry) return null;
    
    if (Date.now() > entry.expiresAt) {
      this.fileIdCache.delete(documentId);
      return null;
    }
    
    return entry.data;
  }

  // Cache management
  private updateAccessOrder(key: string): void {
    const index = this.accessOrder.indexOf(key);
    if (index > -1) {
      this.accessOrder.splice(index, 1);
    }
    this.accessOrder.push(key);
  }

  private evictIfNeeded(): void {
    if (this.cache.size >= this.maxSize && this.accessOrder.length > 0) {
      const lru = this.accessOrder.shift()!;
      this.cache.delete(lru);
    }
  }

  // Bulk operations
  addCitations(citations: Citation[]): void {
    citations.forEach(citation => this.setCitation(citation));
  }

  // Cache statistics
  getStats(): {
    citationCount: number;
    documentCount: number;
    fileIdCount: number;
    hitRate: number;
  } {
    // Clean expired entries first
    this.cleanExpired();
    
    return {
      citationCount: this.cache.size,
      documentCount: this.documentCitationsCache.size,
      fileIdCount: this.fileIdCache.size,
      hitRate: this.calculateHitRate()
    };
  }

  private cleanExpired(): void {
    const now = Date.now();
    
    // Clean citation cache
    Array.from(this.cache.entries()).forEach(([key, entry]) => {
      if (now > entry.expiresAt) {
        this.cache.delete(key);
      }
    });
    
    // Clean document citations cache
    Array.from(this.documentCitationsCache.entries()).forEach(([key, entry]) => {
      if (now > entry.expiresAt) {
        this.documentCitationsCache.delete(key);
      }
    });
    
    // Clean file ID cache
    Array.from(this.fileIdCache.entries()).forEach(([key, entry]) => {
      if (now > entry.expiresAt) {
        this.fileIdCache.delete(key);
      }
    });
  }

  private hits = 0;
  private misses = 0;

  private recordHit(): void {
    this.hits++;
  }

  private recordMiss(): void {
    this.misses++;
  }

  private calculateHitRate(): number {
    const total = this.hits + this.misses;
    return total === 0 ? 0 : this.hits / total;
  }

  // Clear cache
  clear(): void {
    this.cache.clear();
    this.documentCitationsCache.clear();
    this.fileIdCache.clear();
    this.accessOrder = [];
    this.hits = 0;
    this.misses = 0;
  }
}

// Singleton instance
let citationCacheInstance: CitationCache | null = null;

export function getCitationCache(): CitationCache {
  if (!citationCacheInstance) {
    citationCacheInstance = new CitationCache();
  }
  return citationCacheInstance;
}