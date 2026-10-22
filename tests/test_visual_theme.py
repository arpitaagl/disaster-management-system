from pathlib import Path


def test_professional_typography_and_layout_styles_are_present():
    source = Path("components/theme.py").read_text(encoding="utf-8")
    assert "DM Sans" in source
    assert "IBM Plex Mono" in source
    assert "stSidebarNav" in source
    assert "prefers-reduced-motion" in source


def test_light_only_theme_remains_available_without_duplicate_settings_selector():
    theme = Path("components/theme.py").read_text(encoding="utf-8")
    assert 'st.session_state["resq_theme"] = "Light"' in theme
    assert 'st.session_state.get("resq_theme", "Light") == "Dark"' not in theme
    assert 'st.sidebar.selectbox("Appearance"' not in theme
    assert not Path("pages/12_Settings.py").exists()
