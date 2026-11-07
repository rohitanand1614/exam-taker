"""Batch 3b: ui_components.md_safe - make arbitrary question text safe for st.markdown."""
import pytest

from utils import ui_components as ui

pytestmark = pytest.mark.ui

NB = "\u00a0"


def test_none_and_empty():
    assert ui.md_safe(None) == ""
    assert ui.md_safe("") == ""


def test_plain_text_unchanged():
    assert ui.md_safe("Hello world.") == "Hello world."


def test_dunder_escaped():
    assert ui.md_safe("__init__") == "\\_\\_init\\_\\_"


@pytest.mark.parametrize("raw,expected", [
    ("a * b", "a \\* b"),
    ("list[AnyMessage]", "list\\[AnyMessage\\]"),
    ("a < b > c", "a \\< b \\> c"),
    ("a | b", "a \\| b"),
    ("snake_case_name", "snake\\_case\\_name"),
])
def test_control_chars_escaped(raw, expected):
    assert ui.md_safe(raw) == expected


def test_hash_escaped_at_line_start_only():
    assert ui.md_safe("# title") == "\\# title"
    assert ui.md_safe("C# is fine") == "C# is fine"


def test_list_markers_at_line_start_escaped():
    assert ui.md_safe("- item") == "\\- item"
    assert ui.md_safe("1. item") == "1\\. item"


def test_inline_math_unchanged():
    assert ui.md_safe("$x_1 * y$") == "$x_1 * y$"
    assert ui.md_safe("so $a_1$ and b_2") == "so $a_1$ and b\\_2"


def test_display_math_unchanged():
    assert ui.md_safe("$$a_1 * b[2]$$") == "$$a_1 * b[2]$$"
    assert ui.md_safe("x\n$$\na_1\n$$\ny") == "x  \n$$\na_1\n$$  \ny"


def test_inline_code_unchanged():
    assert ui.md_safe("call `__init__` now") == "call `__init__` now"


def test_fenced_code_unchanged():
    # the fenced block itself is untouched; newlines outside it become hard breaks
    assert ui.md_safe("see\n```\nx = a_1 * b\n```\nok") == "see  \n```\nx = a_1 * b\n```  \nok"


def test_line_breaks_become_hard_breaks():
    assert ui.md_safe("one\ntwo") == "one  \ntwo"


def test_indentation_kept_readable():
    out = ui.md_safe("class A:\n    messages: list[int]")
    first, second = out.split("  \n")
    assert first == "class A:"
    assert second == NB * 4 + "messages: list\\[int\\]"
    assert "    " not in out  # never 4 plain spaces: cannot turn into a code block


def test_code_like_stem():
    out = ui.md_safe("class AgentState(TypedDict):\n    messages: list[AnyMessage]")
    assert out == "class AgentState(TypedDict):  \n" + NB * 4 + "messages: list\\[AnyMessage\\]"


def test_dollar_amounts_follow_math_pairing():
    # same rule as Streamlit's KaTeX: a paired $...$ on one line is math
    assert ui.md_safe("costs $5 and $10") == "costs $5 and $10"


def test_backslash_before_punctuation_escaped():
    assert ui.md_safe("a \\* b") == "a \\\\\\* b"


def test_html_is_neutralised():
    out = ui.md_safe("<script>alert(1)</script>")
    assert out.replace("\\<", "").count("<") == 0
