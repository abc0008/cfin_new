import { Message, Citation } from '@/types';
import { MessageRequestSchema, ConversationCreateRequestSchema } from '@/validation/schemas';
import { validateRequest } from '../../lib/validation/api-validation';

// API base URL - would be configured based on environment
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

/**
 * Conversation API service
 * Handles communication with the backend for conversation operations
 */
class ConversationApiService {
  /**
   * Send a request to the API
   */
  private async request<T>(
    endpoint: string,
    method: string = 'GET',
    data?: any,
    formData?: FormData
  ): Promise<T> {
    // Ensure endpoint starts with / 
    if (!endpoint.startsWith('/')) {
      endpoint = '/' + endpoint;
    }
    
    // Fixed URL construction to prevent duplicated /api
    const finalUrl = API_BASE_URL.endsWith('/api') 
      ? `${API_BASE_URL}${endpoint}`
      : `${API_BASE_URL}/api${endpoint}`;
      
    console.log(`Sending ${method} request to ${finalUrl}`);
    
    // Create request options
    const options: RequestInit = {
      method,
      headers: {
        'Accept': 'application/json'
      }
    };
    
    // Add request body if provided
    if (data) {
      options.headers = {
        ...options.headers,
        'Content-Type': 'application/json'
      };
      options.body = JSON.stringify(data);
    }
    
    // Add form data if provided
    if (formData) {
      // Remove Content-Type header to let the browser set it with the boundary
      if (options.headers && typeof options.headers === 'object') {
        const headers = options.headers as Record<string, string>;
        delete headers['Content-Type'];
      }
      options.body = formData;
    }
    
    try {
      const response = await fetch(finalUrl, options);
      
      // Handle non-OK responses
      if (!response.ok) {
        let errorMessage = `API error: ${response.status} ${response.statusText}`;
        
        // Try to parse error response as JSON
        try {
          const errorData = await response.json();
          if (errorData.detail) {
            if (typeof errorData.detail === 'string') {
              errorMessage = errorData.detail;
            } else if (Array.isArray(errorData.detail)) {
              // Handle Pydantic validation errors
              errorMessage = errorData.detail.map((err: any) => 
                `${err.loc.join('.')}: ${err.msg}`
              ).join(', ');
            } else {
              errorMessage = JSON.stringify(errorData.detail);
            }
          } else {
            errorMessage = JSON.stringify(errorData);
          }
        } catch (e) {
          // If not JSON, try to get text
          try {
            const errorText = await response.text();
            if (errorText) {
              errorMessage = errorText;
            }
          } catch (textError) {
            // Keep the original error message if we can't parse the response
          }
        }
        
        throw new Error(errorMessage);
      }
      
      // Parse the response
      const responseData = await response.json();
      return responseData as T;
    } catch (error) {
      console.error('API request error:', error);
      throw error;
    }
  }
  
  /**
   * Create a new conversation
   */
  async createConversation(title: string = 'New Conversation', documentIds: string[] = []): Promise<{ sessionId?: string; session_id?: string }> {
    try {
      // Validate request data against schema
      const validatedData = validateRequest(ConversationCreateRequestSchema, {
        title,
        documentIds: documentIds,
        userId: 'default-user' // This is handled by the backend, but we'll include it for completeness
      });
      
      const response = await this.request<{ sessionId?: string; session_id?: string }>(
        `/conversation`,
        'POST',
        validatedData
      );
      
      console.log(`Created conversation session: ${response.sessionId || response.session_id}`);
      return response;
    } catch (error) {
      console.error('Error creating conversation:', error);
      throw new Error(`Failed to create conversation: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
  
  /**
   * List conversations
   */
  async listConversations(): Promise<any[]> {
    try {
      const conversations = await this.request<any[]>(
        '/conversation',
        'GET'
      );
      return conversations;
    } catch (error) {
      console.error('Error listing conversations:', error);
      return [];
    }
  }
  
  /**
   * Send a message to the conversation
   */
  async sendMessage(sessionId: string, message: string, documentIds: string[] = []): Promise<Message> {
    if (!sessionId) {
      throw new Error('Session ID is required');
    }

    try {
      // Format the request body to match the backend's expected format
      // The backend expects camelCase due to alias_generator=to_camel
      const requestBody = {
        sessionId: sessionId,
        content: message,
        userId: 'default-user',
        referencedDocuments: documentIds,
        referencedAnalyses: [],
        citationLinks: [],
        citationIds: []
      };
      
      const response = await this.request<Message>(
        `/conversation/${sessionId}/message`,
        'POST',
        requestBody
      );
      
      return response;
    } catch (error) {
      console.error('Error sending message:', error);
      throw new Error(`Failed to send message: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
  
  /**
   * Get messages for a conversation
   */
  async getMessages(sessionId: string, limit: number = 50, offset: number = 0): Promise<Message[]> {
    try {
      const response = await this.request<{ messages: Message[] }>(
        `/conversation/${sessionId}/history?limit=${limit}&offset=${offset}`,
        'GET'
      );
      
      return response.messages;
    } catch (error) {
      console.error('Error getting messages:', error);
      return [];
    }
  }
  
  /**
   * Get document citations
   */
  async getDocumentCitations(documentId: string): Promise<Citation[]> {
    try {
      const citations = await this.request<Citation[]>(
        `/document/${documentId}/citations`,
        'GET'
      );
      
      return citations;
    } catch (error) {
      console.error('Error getting document citations:', error);
      return [];
    }
  }

  /**
   * Add a document to a conversation
   */
  async addDocumentToConversation(conversationId: string, documentId: string): Promise<boolean> {
    try {
      await this.request(
        `/conversation/${conversationId}/document/${documentId}`,
        'POST',
        {} // Empty body, document ID is in the path
      );
      console.log(`Document ${documentId} added to conversation ${conversationId}`);
      return true;
    } catch (error) {
      console.error('Error adding document to conversation:', error);
      return false;
    }
  }

  /**
   * Generate follow-up questions for a conversation
   */
  async generateFollowUpQuestions(conversationId: string, limit: number = 3): Promise<string[]> {
    try {
      const questions = await this.request<string[]>(
        `/conversation/${conversationId}/generate-followups?limit=${limit}`,
        'POST'
      );
      
      console.log(`Generated ${questions.length} follow-up questions for conversation ${conversationId}`);
      return questions;
    } catch (error) {
      console.error('Error generating follow-up questions:', error);
      // Return default questions as fallback
      return [
        "What trends do you see in the financial performance?",
        "How does this compare to industry benchmarks?",
        "What are the key risk factors to consider?"
      ];
    }
  }

  /**
   * Check if a conversation exists
   */
  async checkConversationExists(conversationId: string): Promise<boolean> {
    try {
      await this.request<any>(
        `/conversation/${conversationId}`,
        'GET'
      );
      return true;
    } catch (error) {
      // If we get a 404, the conversation doesn't exist
      if (error instanceof Error && error.message.includes('404')) {
        return false;
      }
      // For other errors, we'll assume it doesn't exist
      console.error('Error checking conversation existence:', error);
      return false;
    }
  }

  /**
   * Get a specific message by ID (with analysis_blocks)
   */
  async getMessage(messageId: string): Promise<Message | null> {
    try {
      const response = await this.request<Message>(
        `/conversation/message/${messageId}`,
        'GET'
      );
      
      return response;
    } catch (error) {
      console.error('Error getting message:', error);
      return null;
    }
  }
}

// Create a singleton instance
export const conversationApi = new ConversationApiService();