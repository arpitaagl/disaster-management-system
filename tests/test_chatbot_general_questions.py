from core.state import CommandCenter
from components.chatbot import answer_question, _app_help, _fallback


def _empty_center():
    return CommandCenter(bundle={
        "incidents": [],
        "resources": [],
        "hospitals": [],
        "shelters": [],
        "roads": [],
        "events": [],
    })


def test_voice_style_question_about_app_purpose_gets_direct_answer(monkeypatch):
    import components.chatbot as chatbot

    monkeypatch.setattr(chatbot, "llm_configured", lambda: False)
    answer = answer_question("What is the purpose of this application?", _empty_center())

    assert "Purpose of ResQ-AI" in answer
    assert "incident reports" in answer
    assert "does not automatically" in answer
    assert "Try asking about incident counts" not in answer


def test_app_purpose_answer_matches_natural_variations():
    for question in (
        "What is this app for?",
        "Why was this app made?",
        "What problem does ResQ solve?",
        "Explain ResQ AI",
    ):
        answer = _app_help(question)
        assert answer is not None, question
        assert "Purpose of ResQ-AI" in answer


def test_unmatched_offline_question_does_not_repeat_restrictive_topic_menu():
    answer = _fallback("Can you explain a completely different topic?", _empty_center())

    assert "general-purpose AI model is not currently available" in answer
    assert "Try asking about incident counts" not in answer


def test_general_question_uses_configured_llm(monkeypatch):
    import components.chatbot as chatbot

    monkeypatch.setattr(chatbot, "llm_configured", lambda: True)

    class FakeLLMClient:
        def complete_json(self, system, prompt, timeout):
            assert "general-knowledge questions" in system
            assert "latest_question" in prompt
            return '{"answer": "Here is a direct general answer."}'

    monkeypatch.setattr(chatbot, "LLMClient", FakeLLMClient)
    answer = answer_question("Explain why the sky looks blue.", _empty_center())

    assert answer == "Here is a direct general answer."
