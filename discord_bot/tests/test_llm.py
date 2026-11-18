from llm import LLMError, gemini_text, to_gemini_schema
from analyzer import SCHEMA


def test_schema_types_are_uppercase_and_nested():
    g = to_gemini_schema(SCHEMA)
    assert g["type"] == "OBJECT"
    assert g["properties"]["summary"] == {"type": "ARRAY", "items": {"type": "STRING"}}
    person = g["properties"]["people"]["items"]
    assert person["type"] == "OBJECT" and "name" in person["required"]
    assert person["properties"]["available"]["items"]["properties"]["start_at"]["type"] == "STRING"
    assert g["properties"]["duration_minutes"]["type"] == "INTEGER"


def test_gemini_text_joins_parts_and_skips_thoughts():
    data = {"candidates": [{"content": {"parts": [
        {"text": "생각중", "thought": True}, {"text": '{"a":'}, {"text": " 1}"}]}}]}
    assert gemini_text(data) == '{"a": 1}'


def test_gemini_text_errors():
    for bad in ({}, {"candidates": []}, {"promptFeedback": {"blockReason": "SAFETY"}},
                {"candidates": [{"content": {"parts": []}}]}):
        try:
            gemini_text(bad)
            assert False
        except LLMError:
            pass
