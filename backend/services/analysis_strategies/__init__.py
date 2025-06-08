# This __init__.py file makes 'analysis_strategies' a Python package.
# It exports the strategy_map used by AnalysisService to route analysis requests.

# Import concrete strategy classes.
# These will be defined in comprehensive_strategy.py (Story #6) 
# and financial_template_strategy.py (Story #7).
from .comprehensive_strategy import ComprehensiveAnalysisStrategy
from .financial_template_strategy import FinancialTemplateStrategy
from .basic_financial_strategy import BasicFinancialStrategy
from .sentiment_analysis_strategy import SentimentAnalysisStrategy # Added for this change

# Strategy map to route analysis types to their respective strategy classes
strategy_map = {
    "comprehensive_tools": ComprehensiveAnalysisStrategy,
    "financial_template": FinancialTemplateStrategy,
    "basic_financial": BasicFinancialStrategy,
    "sentiment_analysis": SentimentAnalysisStrategy, # Added for this change
    # Future strategies will be added here as they are implemented.
}

# Explicitly define what is exported when `from .analysis_strategies import *` is used.
__all__ = ['strategy_map'] 