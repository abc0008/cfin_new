from services.citation_instructions import (
    GRANULAR_CITATION_INSTRUCTIONS,
    enhance_system_prompt_with_citation_instructions,
)


def test_granular_citation_instructions_include_number_first_selection():
    assert "NUMBER-FIRST SELECTION" in GRANULAR_CITATION_INSTRUCTIONS
    assert "numeric token" in GRANULAR_CITATION_INSTRUCTIONS


def test_granular_citation_instructions_include_table_source_preference():
    assert "TABLE SOURCE PREFERENCE" in GRANULAR_CITATION_INSTRUCTIONS
    assert "table cell > chart label > narrative mention" in GRANULAR_CITATION_INSTRUCTIONS


def test_granular_citation_instructions_keep_granular_rules():
    assert "BE SPECIFIC AND GRANULAR" in GRANULAR_CITATION_INSTRUCTIONS
    assert "CITE AT THE VALUE LEVEL" in GRANULAR_CITATION_INSTRUCTIONS


def test_enhance_system_prompt_appends_citation_guidelines_once():
    base_prompt = "You are a financial analyst."

    enhanced = enhance_system_prompt_with_citation_instructions(base_prompt)

    assert enhanced.startswith(base_prompt)
    assert enhanced.count("CITATION GUIDELINES") == 1
    assert "NUMBER-FIRST SELECTION" in enhanced


def test_enhance_system_prompt_is_idempotent_when_guidelines_present():
    base_prompt = "You are a financial analyst.\n\nCITATION GUIDELINES:\nExisting rules."

    enhanced = enhance_system_prompt_with_citation_instructions(base_prompt)

    assert enhanced == base_prompt
