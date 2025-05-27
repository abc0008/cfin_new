# backend/settings.py

# Combine all active beta flags in ONE header value
ANTHROPIC_BETA = ",".join([
    "token-efficient-tools-2025-02-19",   # 14% token reduction on tool calls
    "files-api-2025-04-14",               # enables /files endpoint
])

# Claude model IDs
MODEL_HAIKU = "claude-3-haiku-20250315"
MODEL_SONNET = "claude-3-7-sonnet-20250219"  # Latest stable release

# Extract prompt for PDF text extraction (for localization)
PDF_EXTRACT_PROMPT = "Extract the full plain text of this PDF document, preserving structure and formatting."

# Files-API hard limit
FILES_MAX_SIZE_MB = 32 