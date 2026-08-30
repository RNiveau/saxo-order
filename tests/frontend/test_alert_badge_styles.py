"""
The alert badge colours live in CSS, keyed by AlertType's stored values, and
the frontend has no test framework to guard them. Nothing else notices when
the two drift: adding an alert type leaves it falling through to the base
badge, which is how double_bottom came to sit unstyled beside a red
double_top.
"""

import re
from pathlib import Path

from model import AlertType

ALERT_CARD_CSS = Path("frontend/src/components/AlertCard.css")
LABELS_TS = Path("frontend/src/utils/alertLabels.ts")


def _styled_types() -> set:
    css = ALERT_CARD_CSS.read_text()
    return set(re.findall(r'data-alert-type="([a-z0-9_]+)"', css))


def _labelled_types() -> set:
    labels = LABELS_TS.read_text()
    body = labels[labels.index("{") : labels.index("}")]
    return set(re.findall(r"^\s*([a-z0-9_]+):", body, re.MULTILINE))


def test_every_alert_type_has_a_badge_colour() -> None:
    missing = {a.value for a in AlertType} - _styled_types()

    assert not missing, (
        f"no badge colour for {sorted(missing)} - they will render with the "
        "base badge and read as the odd ones out"
    )


def test_no_badge_colour_targets_an_unknown_type() -> None:
    stray = _styled_types() - {a.value for a in AlertType}

    assert (
        not stray
    ), f"badge colour for types that do not exist: {sorted(stray)}"


def test_every_alert_type_has_a_label() -> None:
    """titleCase covers an unmapped type, so this is about wording rather
    than breakage - "Mm7 Break" is what the fallback produces."""
    missing = {a.value for a in AlertType} - _labelled_types()

    assert not missing, f"no explicit label for {sorted(missing)}"
