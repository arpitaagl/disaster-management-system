from pathlib import Path


def test_theme_uses_light_mode_only():
    source = Path("components/theme.py").read_text(encoding="utf-8")
    assert 'st.session_state["resq_theme"] = "Light"' in source
    assert 'st.session_state.get("resq_theme", "Light") == "Dark"' not in source
    assert 'st.button("🌙 Dark mode"' not in source
