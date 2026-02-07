import { convertCitationToHighlight } from '../citationService';
import { Citation } from '@/types/citation';

const makeCitation = (overrides: Partial<Citation> = {}): Citation => ({
  id: 'cite-uuid-1',
  highlightId: 'cite-uuid-1',
  documentId: 'doc-1',
  documentTitle: 'Test Document',
  type: 'page_location',
  citedText: 'Revenue increased',
  rects: [
    {
      x1: 100,
      y1: 120,
      x2: 180,
      y2: 140,
      width: 80,
      height: 20,
      pageNumber: 2,
    },
  ],
  startPageNumber: 2,
  endPageNumber: 2,
  ...overrides,
});

describe('convertCitationToHighlight', () => {
  test('converts citation rects using PDF coordinate mode', () => {
    const citation = makeCitation();
    const highlight = convertCitationToHighlight(citation);

    expect(highlight.id).toBe(citation.id);
    expect(highlight.position.usePdfCoordinates).toBe(true);
    expect(highlight.position.pageNumber).toBe(2);
    expect(highlight.position.rects).toHaveLength(1);

    const rect = highlight.position.rects[0] as any;
    expect(rect.x1).toBe(100);
    expect(rect.y1).toBe(120);
    expect(rect.x2).toBe(180);
    expect(rect.y2).toBe(140);
    expect(rect.pageNumber).toBe(2);
    // Page dimensions are required by react-pdf-highlighter scaled position format.
    expect(rect.width).toBe(612);
    expect(rect.height).toBe(792);
  });

  test('preserves temp mapping metadata for merged backend citations', () => {
    const citation = {
      ...makeCitation({ id: 'backend-uuid-1', highlightId: 'backend-uuid-1' }),
      tempId: 'cite-temp-1',
      tempHighlightId: 'cite-temp-1',
    } as Citation & { tempId: string; tempHighlightId: string };

    const highlight = convertCitationToHighlight(citation);
    const raw = highlight.rawClaudeCitation as any;

    expect(raw.id).toBe('backend-uuid-1');
    expect(raw.tempId).toBe('cite-temp-1');
    expect(raw.tempHighlightId).toBe('cite-temp-1');
  });

  test('creates a tiny anchor rect when citation has no rects', () => {
    const citation = makeCitation({ rects: [], startPageNumber: 5, endPageNumber: 5 });
    const highlight = convertCitationToHighlight(citation);

    expect(highlight.position.rects).toHaveLength(1);
    expect(highlight.position.pageNumber).toBe(5);
    expect((highlight.position.boundingRect as any).x1).toBe(0);
    expect((highlight.position.boundingRect as any).y1).toBe(0);
    expect((highlight.position.boundingRect as any).x2).toBe(1);
    expect((highlight.position.boundingRect as any).y2).toBe(1);
    expect(highlight.position.usePdfCoordinates).toBe(true);
  });
});

