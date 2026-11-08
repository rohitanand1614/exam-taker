"""pytest plugin (registered in pytest.ini next to isolation): make AppTest able to re-run a page that has a
single-select st.pills.

Streamlit 1.51 AppTest bug: a single-select st.pills keeps a scalar (or None) in session state, but
ButtonGroup.indices iterates it as a list, so ANY rerun of a page with such a widget raises ValueError.
Present the value as a list, as multi-select does. Test infrastructure only; the app is untouched.
conftest.py is not touched (it is byte-identical to tag ui-v1.1).
"""
from streamlit.testing.v1.element_tree import ButtonGroup

_original = ButtonGroup.value.fget


def _value(self):
    v = _original(self)
    return [] if v is None else (v if isinstance(v, list) else [v])


_value._etp_patched = True
if not getattr(_original, "_etp_patched", False):       # idempotent if the module is imported twice
    ButtonGroup.value = property(_value)
