Assertion 1 - Add a response_model=MessageResponse to the chat message endpoint:
In the FastAPI router for POST /api/conversation/{session_id}/message, declare response_model=MessageResponse and return a MessageResponse instance to enforce uniform camelCase output.

**Action Taken:**
- Updated the FastAPI endpoint to explicitly declare `response_model=MessageResponse`.
- Ensured the endpoint always returns a `MessageResponse` instance, enforcing consistent camelCase output for the frontend.

**Justification:**
- This guarantees uniform API responses, simplifies frontend data handling, and ensures type safety and clarity for consumers of the API.

Assertion 2 - Alias created_at to timestamp in the Message model:
Add an alias on the Pydantic Message schema so that the JSON field created_at is emitted as timestamp, removing the frontend's fallback logic.

**Action Taken:**
- Updated the Pydantic `Message` model to alias `created_at` to `timestamp` using `Field(..., alias="created_at")`.
- Set `allow_population_by_field_name = True` in the model config for compatibility.
- Updated frontend Zod schemas, types, and API mapping to use only `timestamp` for message time fields, removing all fallback logic for `created_at`/`createdAt`.

**Justification:**
- This change ensures the backend always emits `timestamp` in API responses, eliminating the need for frontend workarounds and improving consistency and maintainability across the stack.

Assertion 3 - Include contentType (and optionally fileSize) in the upload response:
Extend the DocumentUploadResponse Pydantic model and upload_document handler to return contentType (and fileSize) so the Next.js placeholder no longer defaults to 'unknown'.

**Action Taken:**
- Extended the backend `DocumentUploadResponse` Pydantic model to include `contentType` (from the document's MIME type) and `fileSize` (from the document's file size).
- Updated the document upload handler and repository logic to populate these fields in the response.
- Updated the frontend Zod schema for `DocumentUploadResponse` to require `contentType` and `fileSize`, ensuring type safety and alignment with the backend.

**Justification:**
- This ensures the frontend always receives accurate file type and size information after upload, eliminating the need for placeholder defaults and improving user experience and data integrity.

Assertion 4 - Standardize the frontend placeholder mapping for processingStatus:
In the Next.js code that builds the placeholder ProcessedDocument, replace use of data.status/processing_status with data.processingStatus exclusively now that the API emits camelCase.

**Action Taken:**
- Updated the frontend document upload and polling logic to use only the `processingStatus` (camelCase) field for status, removing all fallback logic to `data.status` or `data.processing_status`.
- Ensured all placeholder and polling logic for `ProcessedDocument` is standardized to use the camelCase field, matching the backend API output.
- Added type guards in the document API utility to prevent property access errors on unknown types, improving type safety and robustness.

**Justification:**
- This change ensures the frontend always uses the correct, camelCase status field as emitted by the backend, eliminating ambiguity and potential bugs from mixed-case or legacy field names. It also improves maintainability and type safety in the codebase.

Assertion 5 - Add metrics and ratios to the TS AnalysisResult interface:
Update the TypeScript AnalysisResult type to include top-level fields metrics: FinancialMetric[] and ratios: FinancialRatio[] so developers can access them directly.

**Action Taken:**
- Confirmed that the TypeScript `AnalysisResult` interface already includes `metrics: FinancialMetric[]` and `ratios: FinancialRatio[]` as top-level fields.
- Verified that the Zod schema (`AnalysisResultSchema`) and backend Pydantic model also define these fields, ensuring type safety and alignment across the stack.
- Checked backend API endpoints to ensure `metrics` and `ratios` are always present in analysis responses.

**Justification:**
- Having `metrics` and `ratios` as top-level fields in all layers (backend, API, Zod schema, and TypeScript) ensures developers can reliably access these arrays without extra parsing or fallback logic.
- This alignment improves type safety, reduces bugs, and makes it easier to work with financial analysis results throughout the application.

Assertion 6 - Tighten Zod validation for visualizationData:
Define and plug in Zod schemas for ChartData and TableData (with required chartType and data fields) to catch malformed visualization payloads early.

**Action Taken:**
- Defined strict Zod schemas for `ChartData`, `TableData`, and `VisualizationData` in `schemas.ts` to match the TypeScript and backend models.
- Updated `AnalysisResultSchema` to use the new `VisualizationDataSchema` for the `visualizationData` field, enforcing that all charts and tables are validated for required structure and fields.
- Verified that all API responses and frontend code using `AnalysisResultSchema` now benefit from strict validation of visualization payloads.
- Ensured that any malformed or missing chart/table data will be caught at validation time, not at runtime in the UI.

**Justification:**
- This change ensures that only well-structured and valid visualization data is accepted and rendered, preventing runtime errors and improving reliability for both developers and users.
- Early validation of visualization payloads improves developer experience, reduces debugging time, and increases confidence in the integrity of analysis results throughout the application.