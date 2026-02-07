
Plan for citations feature with PDF highlighting
Jun 26
abc0008/cfin_new
Citations
+53
-0

Archive

Share

Create PR


I am working on building a citations feature with react based PDF highlighting. This feature intends to not only provide citations but also link citations back to the rendered PDF to the exact location of the citation in the PDF on my frontend's document pane.

I am using the FilesAPI and PDF Support features of the anthropic API. 

https://docs.anthropic.com/en/docs/build-with-claude/pdf-support

https://docs.anthropic.com/en/docs/build-with-claude/files

The react pdf documentation and repo can be found at:  https://github.com/agentcooper/react-pdf-highlighter

It can also be found in cfin/pdf_highlighter_repo.txt

<YOUR_JOB> 
Your job is to examine the documentation and existing infrastructure, which includes some citations initial infrastructure (pydantic and zod schemas, potentially some database columns), and come up with a super detailed coding and implementation plan to implement the feature requested above. 
</YOUR_JOB>

<Citations_Documentation>
# Citations

Claude is capable of providing detailed citations when answering questions about documents, helping you track and verify information sources in responses.

The citations feature is currently available on Claude Opus 4, Claude Sonnet 4, Claude Sonnet 3.7, Claude Sonnet 3.5 (new) and Haiku 3.5.

<Warning>
  *Citations with Claude Sonnet 3.7*

  Claude Sonnet 3.7 may be less likely to make citations compared to other Claude models without more explicit instructions from the user. When using citations with Claude Sonnet 3.7, we recommend including additional instructions in the `user` turn, like `"Use citations to back up your answer."` for example.

  We've also observed that when the model is asked to structure its response, it is unlikely to use citations unless explicitly told to use citations within that format. For example, if the model is asked to use <result /> tags in its response, you should add something like "Always use citations in your answer, even within <result />."
</Warning>

<Tip>
  Please share your feedback and suggestions about the citations feature using this [form](https://forms.gle/9n9hSrKnKe3rpowH9).
</Tip>

Here's an example of how to use citations with the Messages API:

<CodeGroup>
  ```bash Shell
  curl https://api.anthropic.com/v1/messages \
    -H "content-type: application/json" \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -d '{
      "model": "claude-opus-4-20250514",
      "max_tokens": 1024,
      "messages": [
        {
          "role": "user",
          "content": [
            {
              "type": "document",
              "source": {
                "type": "text",
                "media_type": "text/plain",
                "data": "The grass is green. The sky is blue."
              },
              "title": "My Document",
              "context": "This is a trustworthy document.",
              "citations": {"enabled": true}
            },
            {
              "type": "text",
              "text": "What color is the grass and sky?"
            }
          ]
        }
      ]
    }'
  ```

  ```python Python
  import anthropic

  client = anthropic.Anthropic()

  response = client.messages.create(
      model="claude-opus-4-20250514",
      max_tokens=1024,
      messages=[
          {
              "role": "user",
              "content": [
                  {
                      "type": "document",
                      "source": {
                          "type": "text",
                          "media_type": "text/plain",
                          "data": "The grass is green. The sky is blue."
                      },
                      "title": "My Document",
                      "context": "This is a trustworthy document.",
                      "citations": {"enabled": True}
                  },
                  {
                      "type": "text",
                      "text": "What color is the grass and sky?"
                  }
              ]
          }
      ]
  )
  print(response)
  ```

  ```java Java
  import java.util.List;

  import com.anthropic.client.AnthropicClient;
  import com.anthropic.client.okhttp.AnthropicOkHttpClient;
  import com.anthropic.models.messages.*;

  public class DocumentExample {

      public static void main(String[] args) {
          AnthropicClient client = AnthropicOkHttpClient.fromEnv();

          PlainTextSource source = PlainTextSource.builder()
                  .data("The grass is green. The sky is blue.")
                  .build();

          DocumentBlockParam documentParam = DocumentBlockParam.builder()
                  .source(source)
                  .title("My Document")
                  .context("This is a trustworthy document.")
                  .citations(CitationsConfigParam.builder().enabled(true).build())
                  .build();
          
          TextBlockParam textBlockParam = TextBlockParam.builder()
                  .text("What color is the grass and sky?")
                  .build();

          MessageCreateParams params = MessageCreateParams.builder()
                  .model(Model.CLAUDE_SONNET_4_20250514)
                  .maxTokens(1024)
                  .addUserMessageOfBlockParams(List.of(ContentBlockParam.ofDocument(documentParam), ContentBlockParam.ofText(textBlockParam)))
                  .build();

          Message message = client.messages().create(params);
          System.out.println(message);
      }
  }
  ```
</CodeGroup>

<Tip>
  **Comparison with prompt-based approaches**

  In comparison with prompt-based citations solutions, the citations feature has the following advantages:

  * **Cost savings:** If your prompt-based approach asks Claude to output direct quotes, you may see cost savings due to the fact that `cited_text` does not count towards your output tokens.
  * **Better citation reliability:** Because we parse citations into the respective response formats mentioned above and extract `cited_text`, citations are guaranteed to contain valid pointers to the provided documents.
  * **Improved citation quality:** In our evals, we found the citations feature to be significantly more likely to cite the most relevant quotes from documents as compared to purely prompt-based approaches.
</Tip>

***

## How citations work

Integrate citations with Claude in these steps:

<Steps>
  <Step title="Provide document(s) and enable citations">
    * Include documents in any of the supported formats: [PDFs](#pdf-documents), [plain text](#plain-text-documents), or [custom content](#custom-content-documents) documents
    * Set `citations.enabled=true` on each of your documents. Currently, citations must be enabled on all or none of the documents within a request.
    * Note that only text citations are currently supported and image citations are not yet possible.
  </Step>

  <Step title="Documents get processed">
    * Document contents are "chunked" in order to define the minimum granularity of possible citations. For example, sentence chunking would allow Claude to cite a single sentence or chain together multiple consecutive sentences to cite a paragraph (or longer)!
      * **For PDFs:** Text is extracted as described in [PDF Support](/en/docs/build-with-claude/pdf-support) and content is chunked into sentences. Citing images from PDFs is not currently supported.
      * **For plain text documents:** Content is chunked into sentences that can be cited from.
      * **For custom content documents:** Your provided content blocks are used as-is and no further chunking is done.
  </Step>

  <Step title="Claude provides cited response">
    * Responses may now include multiple text blocks where each text block can contain a claim that Claude is making and a list of citations that support the claim.
    * Citations reference specific locations in source documents. The format of these citations are dependent on the type of document being cited from.
      * **For PDFs:** citations will include the page number range (1-indexed).
      * **For plain text documents:** Citations will include the character index range (0-indexed).
      * **For custom content documents:** Citations will include the content block index range (0-indexed) corresponding to the original content list provided.
    * Document indices are provided to indicate the reference source and are 0-indexed according to the list of all documents in your original request.
  </Step>
</Steps>

<Tip>
  **Automatic chunking vs custom content**

  By default, plain text and PDF documents are automatically chunked into sentences. If you need more control over citation granularity (e.g., for bullet points or transcripts), use custom content documents instead. See [Document Types](#document-types) for more details.

  For example, if you want Claude to be able to cite specific sentences from your RAG chunks, you should put each RAG chunk into a plain text document. Otherwise, if you do not want any further chunking to be done, or if you want to customize any additional chunking, you can put RAG chunks into custom content document(s).
</Tip>

### Citable vs non-citable content

* Text found within a document's `source` content can be cited from.
* `title` and `context` are optional fields that will be passed to the model but not used towards cited content.
* `title` is limited in length so you may find the `context` field to be useful in storing any document metadata as text or stringified json.

### Citation indices

* Document indices are 0-indexed from the list of all document content blocks in the request (spanning across all messages).
* Character indices are 0-indexed with exclusive end indices.
* Page numbers are 1-indexed with exclusive end page numbers.
* Content block indices are 0-indexed with exclusive end indices from the `content` list provided in the custom content document.

### Token costs

* Enabling citations incurs a slight increase in input tokens due to system prompt additions and document chunking.
* However, the citations feature is very efficient with output tokens. Under the hood, the model is outputting citations in a standardized format that are then parsed into cited text and document location indices. The `cited_text` field is provided for convenience and does not count towards output tokens.
* When passed back in subsequent conversation turns, `cited_text` is also not counted towards input tokens.

### Feature compatibility

Citations works in conjunction with other API features including [prompt caching](/en/docs/build-with-claude/prompt-caching), [token counting](/en/docs/build-with-claude/token-counting) and [batch processing](/en/docs/build-with-claude/batch-processing).

#### Using Prompt Caching with Citations

Citations and prompt caching can be used together effectively.

The citation blocks generated in responses cannot be cached directly, but the source documents they reference can be cached. To optimize performance, apply `cache_control` to your top-level document content blocks.

<CodeGroup>
  ```python Python
  import anthropic

  client = anthropic.Anthropic()

  # Long document content (e.g., technical documentation)
  long_document = "This is a very long document with thousands of words..." + " ... " * 1000  # Minimum cacheable length

  response = client.messages.create(
      model="claude-opus-4-20250514",
      max_tokens=1024,
      messages=[
          {
              "role": "user",
              "content": [
                  {
                      "type": "document",
                      "source": {
                          "type": "text",
                          "media_type": "text/plain",
                          "data": long_document
                      },
                      "citations": {"enabled": True},
                      "cache_control": {"type": "ephemeral"}  # Cache the document content
                  },
                  {
                      "type": "text",
                      "text": "What does this document say about API features?"
                  }
              ]
          }
      ]
  )
  ```

  ```typescript TypeScript
  import Anthropic from '@anthropic-ai/sdk';

  const client = new Anthropic();

  // Long document content (e.g., technical documentation)
  const longDocument = "This is a very long document with thousands of words..." + " ... ".repeat(1000);  // Minimum cacheable length

  const response = await client.messages.create({
    model: "claude-opus-4-20250514",
    max_tokens: 1024,
    messages: [
      {
        role: "user",
        content: [
          {
            type: "document",
            source: {
              type: "text",
              media_type: "text/plain",
              data: longDocument
            },
            citations: { enabled: true },
            cache_control: { type: "ephemeral" }  // Cache the document content
          },
          {
            type: "text",
            text: "What does this document say about API features?"
          }
        ]
      }
    ]
  });
  ```

  ```bash Shell
  curl https://api.anthropic.com/v1/messages \
       --header "x-api-key: $ANTHROPIC_API_KEY" \
       --header "anthropic-version: 2023-06-01" \
       --header "content-type: application/json" \
       --data '{
      "model": "claude-opus-4-20250514",
      "max_tokens": 1024,
      "messages": [
          {
              "role": "user",
              "content": [
                  {
                      "type": "document",
                      "source": {
                          "type": "text",
                          "media_type": "text/plain",
                          "data": "This is a very long document with thousands of words..."
                      },
                      "citations": {"enabled": true},
                      "cache_control": {"type": "ephemeral"}
                  },
                  {
                      "type": "text",
                      "text": "What does this document say about API features?"
                  }
              ]
          }
      ]
  }'
  ```
</CodeGroup>

In this example:

* The document content is cached using `cache_control` on the document block
* Citations are enabled on the document
* Claude can generate responses with citations while benefiting from cached document content
* Subsequent requests using the same document will benefit from the cached content

## Document Types

### Choosing a document type

We support three document types for citations. Documents can be provided directly in the message (base64, text, or URL) or uploaded via the [Files API](/en/docs/build-with-claude/files) and referenced by `file_id`:

| Type           | Best for                                                        | Chunking               | Citation format               |
| :------------- | :-------------------------------------------------------------- | :--------------------- | :---------------------------- |
| Plain text     | Simple text documents, prose                                    | Sentence               | Character indices (0-indexed) |
| PDF            | PDF files with text content                                     | Sentence               | Page numbers (1-indexed)      |
| Custom content | Lists, transcripts, special formatting, more granular citations | No additional chunking | Block indices (0-indexed)     |

<Note>
  .csv, .xlsx, .docx, .md, and .txt files are not supported as document blocks. Convert these to plain text and include directly in message content. See [Working with other file formats](/en/docs/build-with-claude/files#working-with-other-file-formats).
</Note>

### Plain text documents

Plain text documents are automatically chunked into sentences. You can provide them inline or by reference with their `file_id`:

<Tabs>
  <Tab title="Inline text">
    ```python
    {
        "type": "document",
        "source": {
            "type": "text",
            "media_type": "text/plain",
            "data": "Plain text content..."
        },
        "title": "Document Title", # optional
        "context": "Context about the document that will not be cited from", # optional
        "citations": {"enabled": True}
    }
    ```
  </Tab>

  <Tab title="Files API">
    ```python
    {
        "type": "document",
        "source": {
            "type": "file",
            "file_id": "file_011CNvxoj286tYUAZFiZMf1U"
        },
        "title": "Document Title", # optional
        "context": "Context about the document that will not be cited from", # optional
        "citations": {"enabled": True}
    }
    ```
  </Tab>
</Tabs>

<Accordion title="Example plain text citation">
  ```python
  {
      "type": "char_location",
      "cited_text": "The exact text being cited", # not counted towards output tokens
      "document_index": 0,
      "document_title": "Document Title",
      "start_char_index": 0,    # 0-indexed
      "end_char_index": 50      # exclusive
  }
  ```
</Accordion>

### PDF documents

PDF documents can be provided as base64-encoded data or by `file_id`. PDF text is extracted and chunked into sentences. As image citations are not yet supported, PDFs that are scans of documents and do not contain extractable text will not be citable.

<Tabs>
  <Tab title="Base64">
    ```python
    {
        "type": "document",
        "source": {
            "type": "base64",
            "media_type": "application/pdf",
            "data": base64_encoded_pdf_data
        },
        "title": "Document Title", # optional
        "context": "Context about the document that will not be cited from", # optional
        "citations": {"enabled": True}
    }
    ```
  </Tab>

  <Tab title="Files API">
    ```python
    {
        "type": "document",
        "source": {
            "type": "file",
            "file_id": "file_011CNvxoj286tYUAZFiZMf1U"
        },
        "title": "Document Title", # optional
        "context": "Context about the document that will not be cited from", # optional
        "citations": {"enabled": True}
    }
    ```
  </Tab>
</Tabs>

<Accordion title="Example PDF citation">
  ```python
  {
      "type": "page_location",
      "cited_text": "The exact text being cited", # not counted towards output tokens
      "document_index": 0,     
      "document_title": "Document Title", 
      "start_page_number": 1,  # 1-indexed
      "end_page_number": 2     # exclusive
  }
  ```
</Accordion>

### Custom content documents

Custom content documents give you control over citation granularity. No additional chunking is done and chunks are provided to the model according to the content blocks provided.

```python
{
    "type": "document",
    "source": {
        "type": "content",
        "content": [
            {"type": "text", "text": "First chunk"},
            {"type": "text", "text": "Second chunk"}
        ]
    },
    "title": "Document Title", # optional
    "context": "Context about the document that will not be cited from", # optional
    "citations": {"enabled": True}
}
```

<Accordion title="Example citation">
  ```python
  {
      "type": "content_block_location",
      "cited_text": "The exact text being cited", # not counted towards output tokens
      "document_index": 0,
      "document_title": "Document Title",
      "start_block_index": 0,   # 0-indexed
      "end_block_index": 1      # exclusive
  }
  ```
</Accordion>

***

## Response Structure

When citations are enabled, responses include multiple text blocks with citations:

```python
{
    "content": [
        {
            "type": "text",
            "text": "According to the document, "
        },
        {
            "type": "text",
            "text": "the grass is green",
            "citations": [{
                "type": "char_location",
                "cited_text": "The grass is green.",
                "document_index": 0,
                "document_title": "Example Document",
                "start_char_index": 0,
                "end_char_index": 20
            }]
        },
        {
            "type": "text",
            "text": " and "
        },
        {
            "type": "text",
            "text": "the sky is blue",
            "citations": [{
                "type": "char_location",
                "cited_text": "The sky is blue.",
                "document_index": 0,
                "document_title": "Example Document",
                "start_char_index": 20,
                "end_char_index": 36
            }]
        },
        {
            "type": "text",
            "text": ". Information from page 5 states that ",
        },
        {
            "type": "text",
            "text": "water is essential",
            "citations": [{
                "type": "page_location",
                "cited_text": "Water is essential for life.",
                "document_index": 1,
                "document_title": "PDF Document",
                "start_page_number": 5,
                "end_page_number": 6
            }]
        },
        {
            "type": "text",
            "text": ". The custom document mentions ",
        },
        {
            "type": "text",
            "text": "important findings",
            "citations": [{
                "type": "content_block_location",
                "cited_text": "These are important findings.",
                "document_index": 2,
                "document_title": "Custom Content Document",
                "start_block_index": 0,
                "end_block_index": 1
            }]
        }
    ]
}
```

### Streaming Support

For streaming responses, we've added a `citations_delta` type that contains a single citation to be added to the `citations` list on the current `text` content block.

<AccordionGroup>
  <Accordion title="Example streaming events">
    ```python
    event: message_start
    data: {"type": "message_start", ...}

    event: content_block_start
    data: {"type": "content_block_start", "index": 0, ...}

    event: content_block_delta
    data: {"type": "content_block_delta", "index": 0, 
           "delta": {"type": "text_delta", "text": "According to..."}}

    event: content_block_delta
    data: {"type": "content_block_delta", "index": 0,
           "delta": {"type": "citations_delta", 
                     "citation": {
                         "type": "char_location",
                         "cited_text": "...",
                         "document_index": 0,
                         ...
                     }}}

    event: content_block_stop
    data: {"type": "content_block_stop", "index": 0}

    event: message_stop
    data: {"type": "message_stop"}
    ```
  </Accordion>
</AccordionGroup>
</CItations_Documentation>
Copy
Version 1
Version 2
Version 3
Version 4
Summary

Created a new document detailing how to integrate Claude’s citation blocks with the existing React PDF highlighter setup. The plan outlines model updates, backend changes, and frontend handling for linking citations directly to PDF locations
Testing

✅ git status --short

File (1)

CITATIONS_FEATURE_IMPLEMENTATION_PLAN.md
New


Hide
Diff
Logs
CITATIONS_FEATURE_IMPLEMENTATION_PLAN.md
New
+53
-0

# Detailed Implementation Plan for PDF Citations with React Highlighting

This document outlines the steps required to deliver clickable citations that open the PDF viewer at the exact location referenced in Claude’s responses. The plan leverages Anthropic’s Files API and native PDF support together with the `react-pdf-highlighter` library.

## 1. Review Existing Infrastructure
- **Pydantic models** – `backend/models/citation.py` already defines `PageLocationCitation`, `CharLocationCitation`, `ContentBlockLocationCitation`, and the union type `Citation`【F:backend/models/citation.py†L12-L39】【F:backend/models/citation.py†L40-L56】.
- **Frontend types** – `nextjs-fdas/src/types/index.ts` contains a `Citation` interface with page number, bounding box and related metadata【F:nextjs-fdas/src/types/index.ts†L32-L63】.
- **Database** – the SQLAlchemy model `Citation` stores `page`, `text` and a `bounding_box` JSON column with coordinates【F:backend/models/database_models.py†L155-L168】.
- **PDF viewer** – `PDFViewer.tsx` fetches document citations and converts them to highlights using `react-pdf-highlighter`【F:nextjs-fdas/src/components/document/PDFViewer.tsx†L128-L176】【F:nextjs-fdas/src/components/document/PDFViewer.tsx†L200-L248】.

These pieces provide the foundation for a citation workflow but need to be expanded to support Claude’s new citation format and direct linking.

## 2. Data Model and Database Updates
1. **Normalize citation fields**
   - Add start/end page numbers, character indices and block indices to `Citation` in `database_models.py`.
   - Replace `bounding_box` with a `rects` JSONB column storing a list of highlight rectangles.
   - Create an alembic migration to add the new columns and migrate existing data (wrap any single bounding_box dict in a one‑element `rects` array).
2. **Update Pydantic models**
   - Extend `CitationBase` models to include the optional rectangle list.
   - Ensure all models use `alias_generator=to_camel` so API responses remain camelCase.
3. **Frontend Zod schemas**
   - Mirror the new structure in `src/validation/schemas.ts` and update the TypeScript `Citation` interface.

## 3. Claude Integration
1. **Upload PDFs via Files API** – during document processing, send the PDF bytes to `files.create` and persist the returned `file_id` so it can be reused across requests.
2. **Prepare document blocks** – when calling `client.messages.create`, build a list of document blocks referencing each file ID and set `"citations": {"enabled": true}` as described in the docs【CITATIONS_Documentation†L130-L139】.
3. **Generate responses** – append the user’s query as a text block and call the Messages API. The response will contain content blocks with `citations` fields.
4. **Parse citations** – walk through each text block, append a numbered `<sup>` hyperlink and collect the citation payloads. Use `document_index` to map to the stored document IDs and capture page or character ranges. Save the resulting list of `Citation` objects to the database.

## 4. API Endpoints
1. **Document routes** – `/api/documents/{id}/citations` should return all citations for the document, including rectangle data if available. `/api/documents/{id}/citations/{citation_id}` returns a single citation.
2. **Message responses** – include a `citations` array in `MessageResponse` so chat history contains the citation metadata for each message.
3. **Analysis results** – when analysis routines use Claude, persist and expose citations alongside charts or metrics.

## 5. Frontend Handling
1. **Citation context** – implement a React context to cache citations by ID. When a citation link is clicked in chat, fetch the citation if not already loaded.
2. **Chat rendering** – extend the markdown renderer so `<sup><a href="#cid">[1]</a></sup>` markers are turned into clickable elements. The click handler triggers `openCitation(cid)` from context.
3. **PDF viewer integration**
   - Ensure `PDFViewer` can scroll to a page when provided `startPageNumber`. If `rects` are present, draw transient highlight boxes using the existing highlight logic.
   - When `openCitation` is called, load the corresponding document if it is not already displayed, scroll to the cited page, and apply the highlight rectangles.
4. **Highlight search fallback** – if no rectangles are stored, use PDF.js text search (`findText`) to locate `cited_text` and create temporary highlight rectangles client-side.

## 6. Streaming Support (Optional)
- Capture `citations_delta` events during SSE streaming and push incremental markers to the UI so citations appear as the assistant types.
- Merge duplicated citations across turns using a `(documentId, startPage, citedText)` signature to keep the chat tidy.

## 7. Testing and Validation
1. Unit tests for the new Pydantic models and DB migration.
2. Integration tests for the document upload and citation retrieval endpoints.
3. Frontend tests ensuring that clicking a citation marker scrolls to the correct PDF location and highlights the text.
4. Manual tests with sample PDFs to confirm cross-document linking and streaming behaviour.

Implementing these steps will provide end‑to‑end citation support: Claude generates structured citation references, the backend stores them, and the frontend renders hyperlinks that jump to highlighted passages in the PDF viewer.


<Important_Notes>
Summary

backend/models/citation.py already defines Pydantic models for three kinds of citations, mapping fields like startCharIndex or startPageNumber and storing a list of citations within each content block.
Front‑end types mirror those fields, with each Citation containing highlightId, page number and bounding rectangles for PDF highlights.
The helper citationService.ts converts between a Citation and react-pdf-highlighter’s IHighlight type so citations can be rendered in the viewer.
pdf_highlighter_repo.txt shows the structure of the react-pdf-highlighter library, including components such as PdfHighlighter, PdfLoader, and utility functions for bounding‑box calculations.
citations_implementation_plan.md lays out a phased approach for fully linking citations to PDF pages and highlights, starting with correcting the rectangle array bug, then adding page-level citations, then bounding boxes, and finally streaming support
</Important_Notes>