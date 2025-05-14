import type { AnalysisResult } from '@/validation/schemas';
import { apiService } from './apiService';
import { AnalysisResultSchema, ConversationAnalysisResponseSchema } from '@/validation/schemas';
import { EnhancedAnalysisResult, ConversationAnalysisResponse } from '@/types/enhanced';

// Function to handle API errors
const handleApiError = (error: any): never => {
  console.error('API Error:', error);
  if (error.response && error.response.data && error.response.data.detail) {
    throw new Error(error.response.data.detail);
  }
  throw new Error('An error occurred while communicating with the server');
};

interface EnhancedAnalysis {
  trends: any[];
  insights: any[];
  analysisBlocks?: any[]; // Optional field for direct analysis blocks
}

interface ChartDataResponse {
  chartData: any;
  chartType: string;
  title: string;
  description?: string;
}

// API class for analysis related operations
export const analysisApi = {
  /**
   * Runs a specific analysis type on a set of documents.
   * @param documentIds Array of document IDs to analyze
   * @param analysisType Type of analysis to run (e.g., 'financial_summary', 'sentiment_analysis')
   * @param parameters Additional parameters for the analysis
   * @param customKnowledgeBase Optional custom knowledge base ID
   * @param customUserQuery Optional custom user query for the analysis
   * @returns A promise that resolves to the analysis result
   */
  async runAnalysis(
    documentIds: string[], 
    analysisType: string, 
    parameters: Record<string, any> = {},
    customKnowledgeBase?: string,
    customUserQuery?: string
  ): Promise<AnalysisResult> {
    console.log(`Running analysis: ${analysisType} for documents ${documentIds.join(', ')}`, parameters);
    try {
      const payload: Record<string, any> = {
        document_ids: documentIds,
        analysis_type: analysisType,
        parameters: parameters,
      };
      if (customKnowledgeBase) {
        payload.custom_knowledge_base = customKnowledgeBase;
      }
      if (customUserQuery) {
        payload.custom_user_query = customUserQuery;
      }

      const response = await apiService.post<{ data: AnalysisResult }>(
        '/analysis/run',
        payload
      );
      console.log('Raw analysis response from backend:', response.data);

      // Validate the response against the Pydantic model schema
      const validationResult = AnalysisResultSchema.safeParse(response.data);
      if (!validationResult.success) {
        console.error('Backend response validation error:', validationResult.error.errors);
        throw new Error('Invalid analysis result received from backend: ' + JSON.stringify(validationResult.error.errors));
      }
      
      let result = validationResult.data;
      
      // THE ENTIRE FALLBACK BLOCK THAT USED THE DELETED FUNCTIONS IS REMOVED.
      // console.log("Sufficient visualization and metrics data received from backend or no text to parse for fallback.");
      // console.log("No text available (analysisText or summary) to perform client-side extraction.");

      console.log('Final processed analysis result:', result);
      return result;
    } catch (error: any) {
      return handleApiError(error);
    }
  },

  /**
   * Retrieves a specific analysis result.
   * @param analysisId ID of the analysis to retrieve
   * @returns A promise that resolves to the analysis result
   */
  async getAnalysis(analysisId: string): Promise<AnalysisResult> {
    console.log(`Fetching analysis with ID: ${analysisId}`);
    try {
      const response = await apiService.get<{ data: AnalysisResult }>(
        `/analysis/${analysisId}`
      );
      console.log('Raw getAnalysis response from backend:', response.data);

      const validationResult = AnalysisResultSchema.safeParse(response.data);
      if (!validationResult.success) {
        console.error('Backend getAnalysis response validation error:', validationResult.error.errors);
        throw new Error('Invalid analysis result received from backend: ' + JSON.stringify(validationResult.error.errors));
      }
      
      let result: AnalysisResult = validationResult.data;

      console.log('Final processed getAnalysis result:', result);
      return result;
    } catch (error: any) {
      return handleApiError(error);
    }
  },

  /**
   * Fetches available analysis types from the backend.
   * @returns Promise resolving to an array of analysis type objects
   */
  async getAvailableAnalysisTypes(): Promise<{ type: string; name: string; description: string }[]> {
    try {
      const response = await apiService.get<{ data: { type: string; name: string; description: string }[] }>(
        '/analysis/types'
      );
      // Basic validation, could be enhanced with a Zod schema
      if (!Array.isArray(response.data)) {
        console.error('Invalid format for analysis types:', response.data);
        throw new Error('Received invalid format for analysis types.');
      }
      return response.data.map((item: any) => ({
        type: item.type_name || 'Unknown Type',
        name: item.display_name || 'Unnamed Analysis',
        description: item.description || 'No description available.',
      }));
    } catch (error) {
      handleApiError(error);
      return []; // Return empty array on error
    }
  },


  /**
   * Fetches analysis results for a specific conversation.
   * @param conversationId ID of the conversation
   * @returns Promise resolving to conversation analysis response
   */
  async getConversationAnalysis(conversationId: string): Promise<ConversationAnalysisResponse> {
    try {
      const response = await apiService.get<{ data: ConversationAnalysisResponse }>(
        `/analysis/conversation/${conversationId}`
      );
      const validationResult = ConversationAnalysisResponseSchema.safeParse(response.data);
      if (!validationResult.success) {
        console.error('Conversation analysis validation error:', validationResult.error.errors);
        throw new Error('Invalid data received for conversation analysis.');
      }
      return validationResult.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  // Other methods like getChartData, getEnhancedAnalysis, generateTrendsFromAnalysis, 
  // generateEnhancedInsightsFromAnalysis, runSpecificAnalysis remain unchanged for now.
  // They might need review if they rely on the removed client-side parsing.

  async getChartData(analysisId: string, chartType: string): Promise<ChartDataResponse> {
    // This method might need review if it was expected to work with client-side generated charts
    console.warn("analysisApi.getChartData may need review after client-side fallbacks removal.");
    try {
      // Assuming this endpoint returns data that doesn't rely on the removed fallbacks
      const response = await apiService.get<{ data: ChartDataResponse }>(
        `/analysis/${analysisId}/chart/${chartType}`
      );
      return response.data as ChartDataResponse; 
    } catch (error: any) {
      return handleApiError(error);
    }
  },

  async getEnhancedAnalysis(analysisId: string): Promise<EnhancedAnalysis> {
    // This method might need review
    console.warn("analysisApi.getEnhancedAnalysis may need review after client-side fallbacks removal.");
    try {
      const response = await apiService.get<{ data: EnhancedAnalysis }>(
        `/analysis/${analysisId}/enhanced`
      );
      // Assuming this structure is fine
      return response.data as EnhancedAnalysis;
    } catch (error: any) {
      return handleApiError(error);
    }
  },

  generateTrendsFromAnalysis(analysis: AnalysisResult): any[] {
    // This was likely operating on backend-provided data or data that passed through
    // the now-removed fallbacks. If it relied on specific structures from those fallbacks,
    // it might behave differently.
    console.warn("analysisApi.generateTrendsFromAnalysis may behave differently after client-side fallbacks removal.");
    if (!analysis.visualizationData || !analysis.visualizationData.charts) return [];
    
    // Example: simple trend based on first chart data, if numeric
    const firstChart = analysis.visualizationData.charts[0];
    if (firstChart && firstChart.data && firstChart.data.length > 1) {
      const data = firstChart.data as any[];
      const values = data.map(d => d.value || d.y || d.count).filter(v => typeof v === 'number');
      if (values.length > 1) {
        const trend = values[values.length - 1] - values[0];
        return [{ name: `Trend for ${firstChart.config.title || 'chart'}`, value: trend > 0 ? 'Upward' : trend < 0 ? 'Downward' : 'Stable' }];
      }
    }
    return [];
  },

  generateEnhancedInsightsFromAnalysis(analysis: AnalysisResult): any[] {
    // Similar to generateTrendsFromAnalysis, review may be needed.
    console.warn("analysisApi.generateEnhancedInsightsFromAnalysis may behave differently after client-side fallbacks removal.");
    const insights = analysis.insights || [];
    if (analysis.visualizationData?.metrics && analysis.visualizationData.metrics.length > 0) {
      insights.push(`Key metrics identified: ${analysis.visualizationData.metrics.map(m => m.name).join(', ')}.`);
    }
    return insights.map(insight => ({ text: insight, type: 'auto' }));
  },

  async runSpecificAnalysis(
    analysisType: 'financial_ratios' | 'trend_analysis' | 'benchmark_comparison' | 'sentiment_analysis',
    documentIds: string[],
    specificParams: Record<string, any> = {}
  ): Promise<AnalysisResult> {
    console.warn("analysisApi.runSpecificAnalysis is calling runAnalysis, which no longer has client-side fallbacks.");
    return this.runAnalysis(documentIds, analysisType, specificParams);
  }
};
