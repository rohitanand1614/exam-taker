"""Batch 5.0: ui_components.repair_latex - display-only repair of single-backslash LaTeX.

In JSON, "\\frac" written as "\frac" decodes to a form feed + "rac" (same for \beta,
\times, \right, \nabla ...). Inside $...$ / $$...$$ we map the control character back.
Question files are never modified by this.
"""
import pytest

from utils import ui_components as ui

pytestmark = pytest.mark.ui


@pytest.mark.parametrize("broken,fixed", [
    ("$\x0crac{a}{b}$", "$\\frac{a}{b}$"),                 # \f  -> \frac
    ("$\x08eta + 1$", "$\\beta + 1$"),                     # \b  -> \beta
    ("$4 \times 3$", "$4 \\times 3$"),                     # \t  -> \times
    ("$\\left( x \right)$", "$\\left( x \\right)$"),       # \r  -> \right
    ("$\nabla f$", "$\\nabla f$"),                         # \n  -> \nabla
    ("$a \neq b$", "$a \\neq b$"),                         # \n  -> \neq
    ("$\nu_1$", "$\\nu_1$"),                               # \n  -> \nu
])
def test_repairs_inside_inline_math(broken, fixed):
    assert ui.repair_latex(broken) == fixed


def test_repairs_inside_display_math():
    assert ui.repair_latex("$$\x0crac{1}{2}$$") == "$$\\frac{1}{2}$$"
    assert ui.repair_latex("x $$a \times b$$ y") == "x $$a \\times b$$ y"


def test_repairs_several_spans_in_one_string():
    assert ui.repair_latex("$\x0crac12$ and $\x08eta$") == "$\\frac12$ and $\\beta$"


def test_math_spanning_a_single_newline():
    # a span that already contains a real newline is still recognised as one span
    assert ui.repair_latex("$a +\n\x0crac12$") == "$a +\n\\frac12$"


def test_outside_math_nothing_changes():
    for s in ("plain\x0ctext", "tab\there", "ret\rurn", "back\x08space",
              "cost\nabla outside", "line one\nline two"):
        assert ui.repair_latex(s) == s


def test_real_newline_before_ordinary_word_inside_math_is_kept():
    s = "$a\nb$"          # "\n" + "b" is not a known command: could be a real line break
    assert ui.repair_latex(s) == s


def test_word_boundary_for_n_commands():
    # "\nu" is repaired, but "\n" + "umber" (a word) is not
    assert ui.repair_latex("$\nu$") == "$\\nu$"
    assert ui.repair_latex("$a\number$") == "$a\number$"


def test_fixture_explanation_from_batch0():
    broken = "By the power rule, $\x0crac{d}{dx}x^2 = 2x$."
    assert ui.repair_latex(broken) == "By the power rule, $\\frac{d}{dx}x^2 = 2x$."


@pytest.mark.parametrize("s", ["$\x0crac12$", "$4 \times 3$", "$\nabla$", "plain", "$\\frac12$"])
def test_idempotent(s):
    once = ui.repair_latex(s)
    assert ui.repair_latex(once) == once


def test_none_and_empty_safe():
    assert ui.repair_latex(None) == ""
    assert ui.repair_latex("") == ""


def test_already_correct_text_is_untouched():
    s = "Use $\\frac{a}{b}$ and $\\beta$ with $x_1 * y$."
    assert ui.repair_latex(s) == s


# ----------------------------------------------------------------- md_text
def test_md_text_pipeline_repairs_then_escapes():
    out = ui.md_text("see $\x0crac{a}{b}$ and __init__ and \\(x_1\\)")
    assert "$\\frac{a}{b}$" in out        # repaired, math protected from md escaping
    assert "\\_\\_init\\_\\_" in out      # plain text still escaped
    assert "$x_1$" in out                 # \( \) converted to $ and kept intact


def test_md_text_none_safe():
    assert ui.md_text(None) == ""
