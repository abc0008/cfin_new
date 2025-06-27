"""
Visualization needs classifier using Claude to determine what types of
visualizations and analysis should be generated for user queries.
"""

import json
import logging
from typing import Dict, Any, List
from models.viz_needs import VizNeeds, DocumentContext, ClassificationRequest, ChartType, TableType, MetricCategory, AnalysisFocus
from pdf_processing.api_service import ClaudeService

logger = logging.getLogger(__name__)

class VizClassifier:
    """
    Uses Claude to intelligently classify what visualizations and analysis
    are needed for a given user query and document context.
    """
    
    def __init__(self, claude_service: ClaudeService):
        self.claude_service = claude_service
        
    async def classify_viz_needs(
        self, 
        user_query: str,
        document_context: DocumentContext,
        conversation_history: List[str] = None
    ) -> VizNeeds:
        """
        Classify what visualizations and analysis are needed for a user query.
        
        Args:
            user_query: The user's query/message
            document_context: Context about available documents
            conversation_history: Recent conversation history for context
            
        Returns:
            VizNeeds object specifying what should be generated
        """
        try:
            classification_prompt = self._build_classification_prompt(
                user_query, document_context, conversation_history
            )
            
            # Use Claude to classify visualization needs
            response = await self.claude_service.generate_response(
                messages=[{"role": "user", "content": classification_prompt}],
                system="You are a financial analysis assistant that determines what visualizations and analysis are needed for user queries.",
                max_tokens=1000,
                temperature=0.1  # Low temperature for consistent classification
            )
            
            # Parse Claude's response to extract VizNeeds
            viz_needs = self._parse_classification_response(response.get("text", ""))
            
            logger.info(f"Classified viz needs: charts={viz_needs.needs_charts}, tables={viz_needs.needs_tables}, metrics={viz_needs.needs_metrics}")
            
            return viz_needs
            
        except Exception as e:
            logger.error(f"Error classifying visualization needs: {str(e)}")
            # Return safe default for financial documents
            return self._get_default_viz_needs(document_context)
    
    def _build_classification_prompt(
        self,
        user_query: str,
        document_context: DocumentContext,
        conversation_history: List[str] = None
    ) -> str:
        """Build the prompt for Claude to classify visualization needs."""
        
        prompt = f"""Analyze this user query and determine what visualizations and analysis should be generated.

USER QUERY: "{user_query}"

DOCUMENT CONTEXT:
- Has financial data: {document_context.has_financial_data}
- Document types: {', '.join(document_context.document_types)}
- Time periods: {', '.join(document_context.time_periods)}
- Data categories: {', '.join(document_context.data_categories)}"""

        if conversation_history:
            prompt += f"\n\nRECENT CONVERSATION:\n" + "\n".join(conversation_history[-3:])

        prompt += f"""

Based on the query and context, determine what should be generated alongside a streaming text response.

Return your analysis as JSON with this exact structure:
{{
    "needs_charts": boolean,
    "chart_types": ["line", "bar", "area", "stackedArea", "pie", "scatter"],
    "needs_tables": boolean, 
    "table_types": ["detailed", "comparison", "summary"],
    "needs_metrics": boolean,
    "metric_categories": ["profitability", "liquidity", "credit_quality", "growth", "efficiency"],
    "analysis_focus": "trends|comparisons|summary|deep_dive|performance",
    "reasoning": "Brief explanation of choices",
    "confidence": 0.0-1.0
}}

GUIDELINES:
- For financial documents, default to including visualizations unless explicitly declined
- "Trends over time" → line charts + tables
- "Compare/comparison" → bar charts + comparison tables  
- "Breakdown/composition" → pie or stacked area charts
- "Summary/overview" → summary tables + key metrics
- "Performance analysis" → multiple chart types + detailed tables + metrics
- Simple questions like "What is X?" may not need charts but should include key metrics
- If user says "no charts" or "text only", set needs_charts=false

Return ONLY the JSON, no other text."""

        return prompt
    
    def _parse_classification_response(self, response_text: str) -> VizNeeds:
        """Parse Claude's classification response into VizNeeds object."""
        try:
            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning("No JSON found in classification response, using defaults")
                return self._get_default_viz_needs()
                
            json_str = response_text[json_start:json_end]
            classification_data = json.loads(json_str)
            
            # Convert string enums to proper enum values
            chart_types = [ChartType(ct) for ct in classification_data.get("chart_types", []) if ct in [e.value for e in ChartType]]
            table_types = [TableType(tt) for tt in classification_data.get("table_types", []) if tt in [e.value for e in TableType]]
            metric_categories = [MetricCategory(mc) for mc in classification_data.get("metric_categories", []) if mc in [e.value for e in MetricCategory]]
            
            analysis_focus_str = classification_data.get("analysis_focus", "summary")
            analysis_focus = AnalysisFocus(analysis_focus_str) if analysis_focus_str in [e.value for e in AnalysisFocus] else AnalysisFocus.SUMMARY
            
            return VizNeeds(
                needs_charts=classification_data.get("needs_charts", False),
                chart_types=chart_types,
                needs_tables=classification_data.get("needs_tables", False),
                table_types=table_types,
                needs_metrics=classification_data.get("needs_metrics", False),
                metric_categories=metric_categories,
                analysis_focus=analysis_focus,
                reasoning=classification_data.get("reasoning"),
                confidence=float(classification_data.get("confidence", 0.5))
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing classification response: {str(e)}")
            logger.debug(f"Response text: {response_text}")
            return self._get_default_viz_needs()
    
    def _get_default_viz_needs(self, document_context: DocumentContext = None) -> VizNeeds:
        """Get default visualization needs for financial documents."""
        
        # For financial documents, default to comprehensive analysis
        if document_context and document_context.has_financial_data:
            return VizNeeds(
                needs_charts=True,
                chart_types=[ChartType.LINE],  # Safe default for trends
                needs_tables=True,
                table_types=[TableType.SUMMARY],
                needs_metrics=True,
                metric_categories=[MetricCategory.PROFITABILITY],
                analysis_focus=AnalysisFocus.SUMMARY,
                reasoning="Default comprehensive analysis for financial document",
                confidence=0.6
            )
        else:
            # For non-financial documents, minimal visualization
            return VizNeeds(
                needs_charts=False,
                chart_types=[],
                needs_tables=False,
                table_types=[],
                needs_metrics=False,
                metric_categories=[],
                analysis_focus=AnalysisFocus.SUMMARY,
                reasoning="Default minimal analysis for non-financial content",
                confidence=0.7
            )
    
    def extract_document_context(self, document_texts: List[Dict[str, Any]]) -> DocumentContext:
        """
        Extract document context from loaded documents.
        
        Args:
            document_texts: List of document dictionaries with metadata
            
        Returns:
            DocumentContext with relevant information
        """
        has_financial_data = False
        document_types = []
        time_periods = []
        data_categories = []
        
        for doc in document_texts:
            # Check if document has financial data
            if doc.get("extracted_data"):
                extracted = doc["extracted_data"]
                if any(key in extracted for key in ["balance_sheet", "income_statement", "credit_quality", "credit_quality_metrics"]):
                    has_financial_data = True
                    
                # Extract time periods
                if "time_periods" in extracted:
                    time_periods.extend(extracted["time_periods"])
                    
                # Extract document type information
                if "balance_sheet" in extracted:
                    document_types.append("balance_sheet")
                if "income_statement" in extracted:
                    document_types.append("income_statement")
                if "credit_quality" in extracted or "credit_quality_metrics" in extracted:
                    document_types.append("credit_quality")
                    
                # Extract data categories
                if "balance_sheet" in extracted and isinstance(extracted["balance_sheet"], dict):
                    bs = extracted["balance_sheet"]
                    if "loans" in bs or "total_loans" in bs:
                        data_categories.append("loans")
                    if "deposits" in bs or "total_deposits" in bs:
                        data_categories.append("deposits")
                    if "assets" in bs or "total_assets" in bs:
                        data_categories.append("assets")
                        
        return DocumentContext(
            has_financial_data=has_financial_data,
            document_types=list(set(document_types)),
            time_periods=list(set(time_periods)),
            data_categories=list(set(data_categories))
        )