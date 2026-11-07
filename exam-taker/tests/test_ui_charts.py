"""Batch 6.1: Plotly theme + chart colours.

Data arrays are compared with the 6.0 capture in tests/test_insights_flow.py (same numbers),
so styling is proven not to change WHAT is plotted.
"""
import json

import plotly.io as pio
import pytest

from tests.test_insights_flow import (  # noqa: F401  (fixtures/helpers reused, not copied)
    spread, no_network, select_suite, chart_data, decode, by_label)
from utils import ui_components, ui_helpers
from utils.ui_helpers import TOKENS

pytestmark = pytest.mark.ui


# ------------------------------------------------------------ apply_plotly_theme
def test_apply_plotly_theme_registers_default_template():
    ui_helpers.apply_plotly_theme()
    assert pio.templates.default == "etp"
    layout = pio.templates["etp"].layout
    assert layout.paper_bgcolor == TOKENS["surface"]
    assert layout.plot_bgcolor == TOKENS["surface"]
    assert layout.font.color == TOKENS["ink_reading"]
    assert list(layout.colorway)[:4] == [TOKENS["success"], TOKENS["warning"], TOKENS["danger"], TOKENS["info"]]
    assert layout.xaxis.gridcolor == TOKENS["border"] and layout.yaxis.gridcolor == TOKENS["border"]


def test_apply_plotly_theme_is_idempotent():
    ui_helpers.apply_plotly_theme()
    ui_helpers.apply_plotly_theme()
    assert pio.templates.default == "etp"


# ------------------------------------------------------------------ mastery bands
@pytest.mark.parametrize("pct,token", [
    (100, "success"), (70, "success"), (69.99, "warning"), (40, "warning"),
    (39.99, "danger"), (0, "danger"),
])
def test_mastery_colour_bands(pct, token):
    assert ui_components.mastery_colour(pct) == TOKENS[token]


# ------------------------------------------------------- both pages call the theme
@pytest.mark.parametrize("page", ["pages/Progress_Dashboard.py", "pages/Topic_Analysis.py"])
def test_page_applies_plotly_theme(page, spread, app, monkeypatch):
    calls = []
    real = ui_helpers.apply_plotly_theme
    monkeypatch.setattr(ui_helpers, "apply_plotly_theme", lambda: (calls.append(1), real())[1])
    at = app(page).run()
    assert not at.exception
    assert calls, f"{page} must call apply_plotly_theme()"


# --------------------------------------------------------------- Topic_Analysis charts
@pytest.fixture
def topic(spread, app):
    at = app("pages/Topic_Analysis.py").run()
    return select_suite(at)


def specs(at):
    return [json.loads(c.proto.spec) for c in at.get("plotly_chart")]


def test_chart_data_equals_the_6_0_capture(topic):
    weak = [c for c in chart_data(topic) if c[0] == "h"]
    assert weak[0][2] == {"Sample Set": 33.33, "Topic A": 66.67, "Topic B": 100.0}
    stacked = {name: pairs for o, name, pairs in chart_data(topic) if o == "v"}
    assert stacked["Correct"] == {"Geography": 1, "Sample Set": 1, "Maths": 0, "LangGraph": 0,
                                  "Topic A": 2, "Topic B": 3}
    assert stacked["Wrong"] == {"Geography": 0, "Sample Set": 2, "Maths": 2, "LangGraph": 0,
                                "Topic A": 1, "Topic B": 0}
    assert stacked["Unattempted"] == {"Geography": 0, "Sample Set": 0, "Maths": 0, "LangGraph": 1,
                                      "Topic A": 0, "Topic B": 0}


def test_charts_use_the_etp_template_not_streamlits_override(topic):
    for c in topic.get("plotly_chart"):
        assert c.proto.theme == "", "theme=None so our template (token colours) is what is drawn"
    for spec in specs(topic):
        tpl = spec["layout"]["template"]["layout"]
        assert tpl["paper_bgcolor"] == TOKENS["surface"]
        assert tpl["plot_bgcolor"] == TOKENS["surface"]
        assert tpl["font"]["color"] == TOKENS["ink_reading"]
        assert tpl["colorway"][:4] == [TOKENS["success"], TOKENS["warning"], TOKENS["danger"], TOKENS["info"]]


def test_weak_areas_bars_are_coloured_by_mastery_band(topic):
    weak = [s for s in specs(topic) if s["data"][0].get("orientation") == "h"][0]
    trace = weak["data"][0]
    labels, values = decode(trace["y"]), decode(trace["x"])
    colours = decode(trace["marker"]["color"])
    assert labels == ["Sample Set", "Topic A", "Topic B"]
    assert colours == [TOKENS["danger"], TOKENS["warning"], TOKENS["success"]]       # 33% / 67% / 100%
    assert colours == [ui_components.mastery_colour(v) for v in values]


def test_weak_areas_axis_is_a_percentage_scale(topic):
    weak = [s for s in specs(topic) if s["data"][0].get("orientation") == "h"][0]
    assert list(weak["layout"]["xaxis"]["range"]) == [0, 100]


def test_stacked_chart_uses_status_tokens_not_hardcoded_hex(topic):
    stacked = [s for s in specs(topic) if s["data"][0].get("orientation") == "v"][0]
    colour = {t["name"]: t["marker"]["color"] for t in stacked["data"]}
    assert colour == {"Correct": TOKENS["success"], "Wrong": TOKENS["danger"],
                      "Unattempted": TOKENS["ink_faint"]}
    flat = json.dumps(stacked["data"])
    for old in ("#2ecc71", "#e74c3c", "#95a5a6"):
        assert old not in flat


def test_weak_chart_topic_labels_get_their_own_margin(topic):
    weak = [s for s in specs(topic) if s["data"][0].get("orientation") == "h"][0]
    assert weak["layout"]["yaxis"].get("automargin") is True


def test_stacked_chart_has_plain_legend_and_axis_titles(topic):
    stacked = [s for s in specs(topic) if s["data"][0].get("orientation") == "v"][0]
    assert stacked["layout"].get("legend", {}).get("title", {}).get("text") == ""
    assert stacked["layout"]["yaxis"]["title"]["text"] == "Questions"
