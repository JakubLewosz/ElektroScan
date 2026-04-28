from __future__ import annotations

from core.storage import sanitize_name


def test_sanitize_name_preserves_polish_letter_meaning() -> None:
    assert sanitize_name("łącznik świecznikowy") == "lacznik_swiecznikowy"
    assert sanitize_name("panel wywołania - wideodomofon") == "panel_wywolania_wideodomofon"
