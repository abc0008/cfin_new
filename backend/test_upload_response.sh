#\!/bin/bash
# Test document upload endpoint response format

# Create a small test PDF
echo "Test PDF content" > test.txt
# Note: This creates a text file, not a real PDF. For a proper test, you would need a real PDF file.

# Test the upload endpoint
echo "Testing document upload endpoint..."
curl -X POST "http://localhost:8000/api/documents/upload" \
  -F "file=@../Sample_PDFs/Bank_5Q_Trend_Report.pdf" \
  -F "user_id=test-user" \
  -H "Accept: application/json" \
  -s | python3 -m json.tool

