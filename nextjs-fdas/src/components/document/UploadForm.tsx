'use client';

import React, { useState, useRef, useCallback } from 'react';
import { Upload, Loader2, File, AlertCircle, CheckCircle2, RefreshCw } from 'lucide-react';
import { ProcessedDocument } from '@/types';
import { documentsApi } from '@/lib/api/documents';
import { conversationApi } from '@/lib/api/conversation';

interface UploadFormProps {
  onUploadSuccess?: (document: ProcessedDocument) => void;
  onUploadError?: (error: Error) => void;
  sessionId?: string;
}

export function UploadForm({ onUploadSuccess, onUploadError, sessionId }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadComplete, setUploadComplete] = useState(false);
  
  // Reference to the XMLHttpRequest for cancellation support
  const xhrRef = useRef<XMLHttpRequest | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Handle file selection from input
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    console.log("File selected:", selectedFile?.name);
    
    if (selectedFile) {
      validateAndSetFile(selectedFile);
    }
  };
  
  // Validate file and set it if valid
  const validateAndSetFile = (selectedFile: File) => {
    console.log("Validating file:", selectedFile.name);
    
    // Reset states
    setError(null);
    setWarning(null);
    setIsUploading(false); // Ensure we're not showing the loading state
    
    // Check file type
    if (selectedFile.type !== 'application/pdf') {
      console.error("Invalid file type:", selectedFile.type);
      setError('Only PDF files are supported');
      return false;
    }
    
    // Check file size (10MB limit)
    if (selectedFile.size > 10 * 1024 * 1024) {
      console.error("File too large:", selectedFile.size);
      setError('File size must be less than 10MB');
      return false;
    }
    
    console.log("File validation successful");
    
    // Set the file if validation passes
    setFile(selectedFile);
    return true;
  };
  
  // Handle drag events for drag-and-drop functionality
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);
  
  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);
  
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);
  
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      validateAndSetFile(files[0]);
    }
  }, []);
  
  // Cancel the current upload
  const cancelUpload = () => {
    if (xhrRef.current && isUploading) {
      xhrRef.current.abort();
      xhrRef.current = null;
      setIsUploading(false);
      setProgress(0);
      console.log('Upload cancelled');
    } else {
      // Just reset the form if not uploading
      setFile(null);
      setProgress(0);
      setError(null);
      setWarning(null);
      setUploadComplete(false);
    }
  };
  
  // Retry upload after a failure
  const retryUpload = () => {
    setError(null);
    setProgress(0);
    handleUpload();
  };
  
  const handleUpload = async () => {
    if (!file) return;
    
    try {
      setIsUploading(true);
      setError(null);
      setWarning(null);
      setUploadComplete(false);
      setProgress(0); // Reset progress at the start of a new upload
      
      // Use the documentsApi's uploadAndVerifyDocumentWithProgress
      const document = await documentsApi.uploadAndVerifyDocumentWithProgress(
        file,
        (currentProgress, stage) => {
          // Update progress based on the stage
          // Example: Uploading (0-75%), Processing (75-90%), Verifying (90-100%)
          // This is a simplified mapping; adjust as needed based on actual stages
          let overallProgress = currentProgress; // Default to using the direct progress if specific stages aren't granularly mapped
          if (stage === 'uploading_file') { // Assuming 'uploading_file' is a stage string from the API
            overallProgress = currentProgress * 0.75; // Scale upload progress to 0-75%
          } else if (stage === 'processing_document') { // Assuming 'processing_document'
            overallProgress = 75 + (currentProgress * 0.15); // Scale processing to 75-90%
          } else if (stage === 'verifying_data') { // Assuming 'verifying_data'
            overallProgress = 90 + (currentProgress * 0.10); // Scale verification to 90-100%
          } else if (stage === 'completed') {
            overallProgress = 100;
          }
          setProgress(Math.min(overallProgress, 100)); // Ensure progress doesn't exceed 100
          console.log(`Upload progress: ${overallProgress.toFixed(2)}%, Stage: ${stage}`);
        }
      );
      
      // Document processing and verification complete
      setProgress(100);
      setUploadComplete(true);
      console.log("Document verification completed:", document);
      
      // Check if the document has financial data (using the structure from ProcessedDocument)
      if (document.extractedData?.financialVerification) {
        const hasFinancialData = document.extractedData.financialVerification.hasFinancialData;
        const diagnosis = document.extractedData.financialVerification.diagnosis;
        
        if (!hasFinancialData) {
          console.warn("Document may not have ideal financial data:", diagnosis);
          setWarning(`The document was processed but may not contain structured financial data. ${diagnosis || ''}`.trim());
        }
      } else if (document.processingStatus === 'completed' && (!document.extractedData || Object.keys(document.extractedData).length === 0)) {
        // If processing completed but no extracted data, it might be a non-financial or problematic PDF
         console.warn("Document processed, but no specific financial data was extracted.");
         setWarning("Document processed. It might be a non-financial PDF or the content couldn't be structured.");
      }
      
      // If we have a session ID, associate the document with the current conversation
      if (sessionId && document.metadata && document.metadata.id) {
        try {
          console.log(`Associating document ${document.metadata.id} with conversation ${sessionId}`);
          await conversationApi.addDocumentToConversation(sessionId, document.metadata.id);
          console.log("Document successfully associated with conversation");
        } catch (err) {
          console.error("Failed to associate document with conversation:", err);
          // Do not fail the entire upload for this, but maybe show a non-critical warning
          setWarning((prevWarning) => (prevWarning ? prevWarning + " " : "") + "Could not link document to the current chat session.");
        }
      }
      
      // Notify parent component of successful upload
      onUploadSuccess?.(document);
      
      // Reset form after short delay to show 100% completion
      setTimeout(() => {
        setFile(null);
        setProgress(0);
        setIsUploading(false);
        setUploadComplete(false);
        // setWarning(null); // Optionally clear warning on new upload cycle
      }, 3000); // Increased delay slightly
      
    } catch (err) {
      console.error("Document upload failed:", err);
      
      const errorMessage = err instanceof Error ? err.message : 'Failed to upload document';
      
      if (errorMessage.includes('Network error')) {
        setError('Network error. Please check your internet connection and try again.');
      } else if (errorMessage.includes('aborted') || errorMessage.includes('cancelled')) { // Added 'cancelled'
        setError('Upload was cancelled.');
      } else if (errorMessage.includes('size limit exceeded')) {
        setError('The file exceeds the maximum size limit (10MB).');
      } else if (errorMessage.includes('unsupported file type') || errorMessage.includes('Invalid file type')) {
        setError('The file type is not supported. Please upload a PDF document.');
      } else if (errorMessage.includes('processing failed') || errorMessage.includes('timed out')) { // More generic processing errors
        setError('Error processing the document. The PDF might be corrupted, password protected, or took too long to process.');
      } else {
        setError(errorMessage);
      }
      
      setIsUploading(false);
      setProgress(0);
      onUploadError?.(err instanceof Error ? err : new Error(errorMessage)); // Pass more specific error
    } finally {
      // Ensure xhrRef is nullified if it was part of the old code, though it's not used in the new logic
      if (xhrRef && xhrRef.current) {
        xhrRef.current = null;
      }
    }
  };
  
  return (
    <div className="space-y-4">
      {error && (
        <div className="p-4 border border-destructive rounded-md flex items-start space-x-2 bg-destructive/10 text-destructive">
          <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="text-sm font-medium">{error}</div>
            {isUploading === false && file && (
              <button 
                onClick={retryUpload}
                className="mt-2 inline-flex items-center text-xs font-medium text-destructive hover:text-destructive/80"
              >
                <RefreshCw className="h-3 w-3 mr-1" /> Try again
              </button>
            )}
          </div>
        </div>
      )}
      
      {warning && !error && (
        <div className="p-4 border border-brand-lust-border rounded-md flex items-start space-x-2 bg-brand-lust bg-opacity-10 text-brand-lust">
          <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
          <div className="text-sm">{warning}</div>
        </div>
      )}
      
      {uploadComplete && !error && !isUploading && (
        <div className="p-4 border border-secondary rounded-md flex items-start space-x-2 bg-secondary/10 text-secondary">
          <CheckCircle2 className="h-5 w-5 flex-shrink-0 mt-0.5" />
          <div className="text-sm">Document uploaded and processed successfully!</div>
        </div>
      )}
      
      <div 
        className={`flex flex-col items-center p-6 border-2 ${isDragging ? 'border-primary bg-primary/10' : 'border-dashed border-muted bg-background hover:bg-muted/30'} rounded-md transition-colors`}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {!file ? (
          <>
            <File className="h-8 w-8 text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground mb-4">Drag and drop your PDF or click to browse</p>
            <label className="cursor-pointer inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2">
              <Upload className="mr-2 h-4 w-4" />
              Select PDF
              <input 
                ref={fileInputRef}
                type="file" 
                accept=".pdf,application/pdf" 
                onChange={handleFileChange} 
                disabled={isUploading}
                className="hidden"
                key={`file-input-${isUploading ? 'uploading' : 'idle'}`}
              />
            </label>
          </>
        ) : (
          <div className="w-full space-y-4">
            <div className="flex items-center">
              <File className="h-6 w-6 text-primary mr-2" />
              <div className="text-sm font-medium flex-1 truncate">{file.name}</div>
              <div className="text-xs text-muted-foreground">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </div>
            </div>
            
            {isUploading ? (
              <div className="space-y-2">
                <div className="w-full bg-muted rounded-full h-2">
                  <div 
                    className="bg-primary h-full rounded-full transition-all duration-300 ease-in-out" 
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>
                    {progress < 75 ? 'Uploading...' : 
                     progress < 90 ? 'Processing...' : 
                     'Verifying...'}
                  </span>
                  <span>{Math.round(progress)}%</span>
                </div>
              </div>
            ) : (
              <div className="flex space-x-2">
                <button
                  type="button"
                  onClick={cancelUpload}
                  className="flex-1 border border-input bg-background text-foreground hover:bg-muted rounded-md font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 text-sm px-4 py-2"
                >
                  Cancel
                </button>
                <button 
                  type="button"
                  onClick={handleUpload}
                  disabled={isUploading}
                  className="flex-1 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none text-sm px-4 py-2 flex items-center justify-center"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Processing...
                    </>
                  ) : 'Upload'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
      
      {isUploading && (
        <div className="text-xs text-muted-foreground italic">
          {progress < 75 ? (
            <div>Uploading your document... {Math.round(progress)}% complete</div>
          ) : progress < 90 ? (
            <div>Processing your document. This may take a minute...</div>
          ) : (
            <div className="text-primary font-medium">
              Verifying financial data extraction...
            </div>
          )}
        </div>
      )}
      
      <div className="text-xs text-muted-foreground">
        <p>Supported file types: PDF (max size: 10MB)</p>
      </div>
    </div>
  );
}
