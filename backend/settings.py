# backend/settings.py

# Combine all active beta flags in ONE header value
ANTHROPIC_BETA = ",".join([
    "token-efficient-tools-2025-02-19",   # 14% token reduction on tool calls
    "files-api-2025-04-14",               # enables /files endpoint
])

# Claude model IDs  
MODEL_HAIKU = "claude-3-5-haiku-20241022"  # Fast and cheap for basic extraction WITH PDF support
MODEL_SONNET = "claude-3-5-sonnet-20241022" # Was claude-3-5-sonnet-20241022 Higher token limit: 80K vs 40K input tokens/min

# Processing mode: 'fast' uses Haiku, 'detailed' uses Sonnet
# Can be overridden by CLAUDE_PROCESSING_MODE environment variable
# Set CLAUDE_PROCESSING_MODE=detailed for highest quality but slower processing
import os
PROCESSING_MODE = os.getenv("CLAUDE_PROCESSING_MODE", "fast")  # Default to fast for better user experience

# Model selection based on processing mode
SELECTED_MODEL = MODEL_HAIKU if PROCESSING_MODE == "fast" else MODEL_SONNET

# Extract prompt for PDF text extraction (for localization)
PDF_EXTRACT_PROMPT = "EXTRACT ALL TEXT: You must extract the complete, full text content from this entire PDF document. Include every page, every table, every number, every financial statement, and every section. Output ONLY the extracted text content - do not ask questions, do not provide commentary, do not suggest options. Extract the complete document text now."

# Files-API hard limit
FILES_MAX_SIZE_MB = 32 