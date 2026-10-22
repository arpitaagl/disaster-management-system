from pathlib import Path


def test_settings_page_does_not_duplicate_theme_control():
    settings_page = Path("pages/12_Settings.py")
    assert not settings_page.exists()


def test_theme_remains_light_only_without_an_appearance_selector():
    source = Path("components/theme.py").read_text(encoding="utf-8")
    assert 'st.session_state["resq_theme"] = "Light"' in source
    assert 'st.sidebar.selectbox("Appearance"' not in source
    assert 'st.session_state.get("resq_theme", "Light") == "Dark"' not in source
