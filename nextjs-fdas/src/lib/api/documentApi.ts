// Placeholder for document API functions
import { ProcessedDocument, DocumentMetadata } from '@/types'; // Assuming ProcessedDocument is in @/types

const MOCK_DOCUMENTS: ProcessedDocument[] = [
  // Add some mock document data if needed for local dev without a backend
];

export async function fetchDocuments(): Promise<ProcessedDocument[]> {
  console.log('Fetching documents...');
  // Replace with actual API call
  await new Promise(resolve => setTimeout(resolve, 500));
  return MOCK_DOCUMENTS;
}

export async function fetchDocument(id: string): Promise<ProcessedDocument | undefined> {
  console.log(`Fetching document ${id}...`);
  await new Promise(resolve => setTimeout(resolve, 500));
  return MOCK_DOCUMENTS.find(doc => doc.metadata.id === id);
}

export async function uploadFile(file: File): Promise<ProcessedDocument> {
  console.log(`Uploading file ${file.name}...`);
  // Replace with actual API call
  await new Promise(resolve => setTimeout(resolve, 1000));
  const newDoc: ProcessedDocument = {
    metadata: {
      id: String(Date.now()),
      filename: file.name,
      uploadTimestamp: new Date().toISOString(),
      fileSize: file.size,
      mimeType: file.type,
      userId: 'mockUser',
    },
    contentType: 'other',
    extractionTimestamp: new Date().toISOString(),
    periods: [],
    extractedData: {},
    confidenceScore: 0.95,
    processingStatus: 'completed',
  };
  MOCK_DOCUMENTS.push(newDoc);
  return newDoc;
}

export async function fetchAnalysesForDocument(documentId: string): Promise<any[]> { // Replace 'any' with AnalysisResult or similar
  console.log(`Fetching analyses for document ${documentId}...`);
  await new Promise(resolve => setTimeout(resolve, 500));
  return []; // Placeholder
}

// Add other API functions as needed: deleteDocument, runAnalysis, etc. 