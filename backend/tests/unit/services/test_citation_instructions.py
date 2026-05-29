from services.citation_instructions import (
    BANKING_METRIC_FORMAT_INSTRUCTIONS,
    FINANCIAL_AGENT_INSTRUCTIONS,
    GRANULAR_CITATION_INSTRUCTIONS,
    VISUALIZATION_TOOL_FORMAT_SUFFIX,
    VISUALIZATION_TOOL_OUTPUT_INSTRUCTIONS,
    enhance_system_prompt_with_citation_instructions,
)


def test_granular_citation_instructions_include_number_first_selection():
    assert "NUMBER-FIRST SELECTION" in GRANULAR_CITATION_INSTRUCTIONS
    assert "numeric token" in GRANULAR_CITATION_INSTRUCTIONS


def test_granular_citation_instructions_include_table_source_preference():
    assert "TABLE SOURCE PREFERENCE" in GRANULAR_CITATION_INSTRUCTIONS
    assert "table cell > chart label > narrative mention" in GRANULAR_CITATION_INSTRUCTIONS
    assert "Default to financial tables over narrative sentences" in GRANULAR_CITATION_INSTRUCTIONS


def test_granular_citation_instructions_keep_granular_rules():
    assert "BE SPECIFIC AND GRANULAR" in GRANULAR_CITATION_INSTRUCTIONS
    assert "CITE AT THE VALUE LEVEL" in GRANULAR_CITATION_INSTRUCTIONS


def test_banking_metric_format_instructions_cover_common_metrics():
    assert "BANKING METRIC FORMATTING" in BANKING_METRIC_FORMAT_INSTRUCTIONS
    assert "two decimal places" in BANKING_METRIC_FORMAT_INSTRUCTIONS
    assert "125 bps" in BANKING_METRIC_FORMAT_INSTRUCTIONS
    assert "Per-share amounts" in BANKING_METRIC_FORMAT_INSTRUCTIONS
    assert "generate_graph_data" in BANKING_METRIC_FORMAT_INSTRUCTIONS


def test_visualization_tool_output_instructions_cover_chat_artifacts():
    assert "VISUALIZATION TOOL OUTPUT" in VISUALIZATION_TOOL_OUTPUT_INSTRUCTIONS
    assert "generate_financial_metric" in VISUALIZATION_TOOL_OUTPUT_INSTRUCTIONS
    assert "generate_table_data" in VISUALIZATION_TOOL_OUTPUT_INSTRUCTIONS
    assert "generate_graph_data" in VISUALIZATION_TOOL_OUTPUT_INSTRUCTIONS
    assert "adhoc" in VISUALIZATION_TOOL_OUTPUT_INSTRUCTIONS.lower()


def test_visualization_tool_format_suffix_is_compact():
    assert "table-sourced" in VISUALIZATION_TOOL_FORMAT_SUFFIX
    assert "2 decimal" in VISUALIZATION_TOOL_FORMAT_SUFFIX


def test_financial_agent_instructions_include_citation_formatting_and_visualizations():
    assert "CITATION GUIDELINES" in FINANCIAL_AGENT_INSTRUCTIONS
    assert "BANKING METRIC FORMATTING" in FINANCIAL_AGENT_INSTRUCTIONS
    assert "VISUALIZATION TOOL OUTPUT" in FINANCIAL_AGENT_INSTRUCTIONS


def test_enhance_system_prompt_appends_all_guidance_once():
    base_prompt = "You are a financial analyst."

    enhanced = enhance_system_prompt_with_citation_instructions(base_prompt)

    assert enhanced.startswith(base_prompt)
    assert enhanced.count("CITATION GUIDELINES") == 1
    assert enhanced.count("BANKING METRIC FORMATTING") == 1
    assert enhanced.count("VISUALIZATION TOOL OUTPUT") == 1
    assert "NUMBER-FIRST SELECTION" in enhanced


def test_enhance_system_prompt_is_idempotent_when_all_guidelines_present():
    base_prompt = (
        "You are a financial analyst.\n\n"
        "CITATION GUIDELINES:\nExisting rules.\n\n"
        "BANKING METRIC FORMATTING:\nExisting formatting.\n\n"
        "VISUALIZATION TOOL OUTPUT:\nExisting visualization rules."
    )

    enhanced = enhance_system_prompt_with_citation_instructions(base_prompt)

    assert enhanced == base_prompt


def test_enhance_system_prompt_adds_missing_visualization_rules():
    base_prompt = (
        "You are a financial analyst.\n\n"
        "CITATION GUIDELINES:\nExisting rules.\n\n"
        "BANKING METRIC FORMATTING:\nExisting formatting."
    )

    enhanced = enhance_system_prompt_with_citation_instructions(base_prompt)

    assert enhanced.count("VISUALIZATION TOOL OUTPUT") == 1
    assert "generate_graph_data" in enhanced
