import React from 'react';

export interface DocumentDetailsProps {
  // Define props based on how it's used in DashboardPage or its intended functionality
  documentId?: string;
  // Add other props as needed
}

export const DocumentDetails: React.FC<DocumentDetailsProps> = ({ documentId }) => {
  if (!documentId) {
    return <div>No document selected.</div>;
  }

  // Fetch and display document details here
  return (
    <div>
      <h3 className="text-lg font-semibold">Document Details</h3>
      <p>Details for document ID: {documentId}</p>
      {/* Placeholder content - replace with actual details */}
    </div>
  );
};

// If it was meant to be a default export, you would use:
// export default DocumentDetails;
// However, the import in DashboardPage is a named import: import { DocumentDetails } from '@/components/document/DocumentDetails' 