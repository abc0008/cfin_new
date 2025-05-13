
Ran tool
Here’s a step-by-step plan for updating the frontend to support and clearly display multi-document analysis:

---

## 1. **UI/UX: Allow Multi-Document Selection for Analysis**

- **Current State:**  
  The workspace and analysis logic (e.g., in `src/app/workspace/page.tsx`) only pass a single document ID to `runAnalysis` and `runManualAnalysis`.
- **Update Needed:**  
  - Refactor the document selection UI to allow users to select multiple documents (e.g., with checkboxes or a multi-select list).
  - Store the selected document IDs in a state array (e.g., `selectedDocumentIds: string[]`).

---

## 2. **API Call: Send All Selected Document IDs**

- **Current State:**  
  `runAnalysis` and `runManualAnalysis` are called with `[selectedDocument.metadata.id]` (single-item array).
- **Update Needed:**  
  - Update these calls to use the full array of selected document IDs:  
    ```typescript
    await analysisApi.runAnalysis(selectedDocumentIds, analysisType, parameters, query);
    ```
  - Update all usages and handlers (including `onRunAnalysis` in `AnalysisControls` and any other analysis triggers).

---

## 3. **Display: Show All Analyzed Documents in Results**

- **Current State:**  
  The UI and system messages reference only one document per analysis.
- **Update Needed:**  
  - When displaying analysis results, show all document names/IDs included in the analysis (e.g., in the analysis summary, system messages, and result cards).
  - Update system messages to reference all analyzed documents, e.g.:
    ```
    I've completed the financial analysis for "Document A", "Document B", and "Document C".
    ```
  - In the `Canvas` and result display, show which documents were included (and, if possible, allow users to view details for each).

---

## 4. **Testing and Validation**

- **Test:**  
  - Select multiple documents, run an analysis, and verify:
    - The backend receives all document IDs.
    - The result includes all document IDs.
    - The UI displays all analyzed documents.
  - Test with one, two, and many documents.

---

## 5. **(Optional) Per-Document Breakdown**

- If the backend provides per-document results, update the UI to show a breakdown for each document (e.g., tabs or sections per document).

---

### Would you like to:
- Start with the UI change for multi-select in the document list/workspace?
- Or update the analysis trigger logic first?
- Or see a code example for a specific part of this plan?

Let me know your preferred starting point!
