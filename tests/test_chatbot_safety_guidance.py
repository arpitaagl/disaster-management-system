from core.state import CommandCenter
from components.chatbot import _fallback, _safety_guidance


def _empty_center():
    return CommandCenter(bundle={
        "incidents": [], "resources": [], "hospitals": [],
        "shelters": [], "roads": [], "events": [],
    })


def test_earthquake_guidance_includes_drop_cover_hold_and_official_sources():
    answer = _safety_guidance("What should I do during an earthquake?")
    assert answer is not None
    assert "Drop, Cover, and Hold On" in answer
    assert "usgs.gov" in answer
    assert "ndma.gov.in" in answer


def test_flood_guidance_warns_against_entering_floodwater():
    answer = _safety_guidance("How do I stay safe in a flood?")
    assert answer is not None
    assert "Never walk, swim, or drive through floodwater" in answer
    assert "ready.gov/floods" in answer


def test_emergency_guidance_has_india_112_and_no_dispatch_claim():
    answer = _safety_guidance("What emergency number should I call?")
    assert answer is not None
    assert "112" in answer
    assert "112.gov.in" in answer
    assert "cannot call responders" in answer


def test_general_preparedness_links_official_sources():
    answer = _safety_guidance("What should go in an emergency kit?")
    assert answer is not None
    assert "drinking water" in answer
    assert "ndma.gov.in" in answer


def test_unmatched_question_falls_back_to_operational_snapshot_summary():
    answer = _fallback("Give me a dashboard summary", _empty_center())
    assert "active incidents" in answer.casefold()
    assert "simulated data" in answer.casefold()


def test_answer_question_uses_deterministic_safety_guidance_when_llm_is_configured(monkeypatch):
    import components.chatbot as chatbot

    monkeypatch.setattr(chatbot, "llm_configured", lambda: True)

    def unexpected_llm_call(*args, **kwargs):
        raise AssertionError("LLM should not be called for built-in safety guidance")

    monkeypatch.setattr(chatbot.LLMClient, "complete_json", unexpected_llm_call)
    answer = chatbot.answer_question("What should I do during an earthquake?", _empty_center())
    assert "Drop, Cover, and Hold On" in answer
    assert "usgs.gov" in answer


def test_answer_question_uses_llm_for_non_guidance_when_configured(monkeypatch):
    import components.chatbot as chatbot

    monkeypatch.setattr(chatbot, "llm_configured", lambda: True)

    class FakeLLMClient:
        def complete_json(self, system, prompt, timeout):
            return '{"answer": "Snapshot-based response"}'

    monkeypatch.setattr(chatbot, "LLMClient", FakeLLMClient)
    answer = chatbot.answer_question("Summarize the response snapshot", _empty_center())
    assert answer == "Snapshot-based response"


def test_answer_question_falls_back_when_llm_request_fails(monkeypatch):
    import components.chatbot as chatbot

    monkeypatch.setattr(chatbot, "llm_configured", lambda: True)

    class FailingLLMClient:
        def complete_json(self, system, prompt, timeout):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(chatbot, "LLMClient", FailingLLMClient)
    answer = chatbot.answer_question("Summarize the response snapshot", _empty_center())

    assert "active incidents" in answer.casefold()
    assert "simulated data" in answer.casefold()


def test_answer_question_falls_back_when_llm_returns_invalid_json(monkeypatch):
    import components.chatbot as chatbot

    monkeypatch.setattr(chatbot, "llm_configured", lambda: True)

    class InvalidJSONLLMClient:
        def complete_json(self, system, prompt, timeout):
            return "not valid JSON"

    monkeypatch.setattr(chatbot, "LLMClient", InvalidJSONLLMClient)
    answer = chatbot.answer_question("Summarize the response snapshot", _empty_center())

    assert "active incidents" in answer.casefold()
    assert "simulated data" in answer.casefold()

def test_ambulance_request_gets_emergency_guidance_without_llm(monkeypatch):
    import components.chatbot as chatbot

    monkeypatch.setattr(chatbot, "llm_configured", lambda: False)
    answer = chatbot.answer_question("I need an ambulance", _empty_center())

    assert "local emergency services" in answer
    assert "cannot call responders" in answer
    assert "active incidents" not in answer


def test_resource_availability_question_about_ambulances_stays_operational():
    answer = _fallback("Which ambulance resources are available?", _empty_center())

    assert "resources" in answer
    assert "local emergency services" not in answer



def test_app_help_explains_incident_reporting_steps():
    from components.chatbot import _app_help

    answer = _app_help("How do I report an incident?")
    assert answer is not None
    assert "Report Incident" in answer
    assert "ANALYZE INCIDENT" in answer
    assert "session-only" in answer


def test_app_help_explains_voice_controls_and_limitations():
    from components.chatbot import _app_help

    answer = _app_help("How do I use the voice assistant?")
    assert answer is not None
    assert "Start conversation" in answer
    assert "Interrupt / ask now" in answer
    assert "cannot place emergency calls" in answer


def test_app_help_describes_supported_app_pages():
    from components.chatbot import _app_help

    answer = _app_help("What features does this app have?")
    assert answer is not None
    for page in ("Command Center", "Report Incident", "Scenario Simulator",
                 "Live Government Alerts", "Incident Operations", "Situation Reports",
                 "Route Planner", "ResQ Assistant"):
        assert page in answer


def test_app_help_is_used_even_when_llm_is_configured(monkeypatch):
    import components.chatbot as chatbot

    monkeypatch.setattr(chatbot, "llm_configured", lambda: True)

    def unexpected_llm_call(*args, **kwargs):
        raise AssertionError("Known app how-to questions should not require an LLM")

    monkeypatch.setattr(chatbot.LLMClient, "complete_json", unexpected_llm_call)
    answer = chatbot.answer_question("How can I report an incident?", _empty_center())
    assert "ANALYZE INCIDENT" in answer


def test_app_help_matches_natural_variations_and_typos():
    from components.chatbot import _app_help

    canonical = _app_help("How do I report an incident?")
    variations = [
        "how can i report an incident in this app",
        "how to repot incident in the application",
        "pls tell me how to report an incident",
        "i need to submit incident report",
    ]
    assert canonical is not None
    for question in variations:
        assert _app_help(question) == canonical


def test_greeting_works_with_short_and_misspelled_inputs():
    from components.chatbot import _greeting_response

    for question in ("hi", "Hello!", "heyy", "hii there", "good morning"):
        answer = _greeting_response(question)
        assert answer is not None
        assert "ResQ Assistant" in answer


def test_answer_question_handles_greetings_deterministically_when_llm_is_configured(monkeypatch):
    import components.chatbot as chatbot

    monkeypatch.setattr(chatbot, "llm_configured", lambda: True)

    def unexpected_llm_call(*args, **kwargs):
        raise AssertionError("Greetings should not require an LLM")

    monkeypatch.setattr(chatbot.LLMClient, "complete_json", unexpected_llm_call)
    for question in ("hi", "Hello!", "heyy", "hii there", "good morning"):
        answer = chatbot.answer_question(question, _empty_center())
        assert "ResQ Assistant" in answer


def test_safety_intent_matching_tolerates_typos_and_extra_words():
    from components.chatbot import _safety_guidance

    assert _safety_guidance("what should i do in a big floood emergency") == _safety_guidance(
        "How do I stay safe in a flood?"
    )
    assert _safety_guidance("there is an earth quak, what should i do") is not None


def test_known_app_help_is_matched_before_llm(monkeypatch):
    import components.chatbot as chatbot

    monkeypatch.setattr(chatbot, "llm_configured", lambda: True)

    class UnexpectedLLMClient:
        def complete_json(self, *args, **kwargs):
            raise AssertionError("Known app-help intents should be handled consistently")

    monkeypatch.setattr(chatbot, "LLMClient", UnexpectedLLMClient)
    answer = chatbot.answer_question("how can i repot incident in this app", _empty_center())
    assert "ANALYZE INCIDENT" in answer


def test_earthquake_count_question_returns_count_not_reporting_instructions():
    from components.chatbot import _app_help, _incident_count_answer

    center = CommandCenter(bundle={
        "incidents": [
            {"id": "EQ-1", "disaster_type": "Earthquake"},
            {"id": "EQ-2", "disaster_type": "Earthquake"},
            {"id": "FL-1", "disaster_type": "Flood"},
        ],
        "resources": [], "hospitals": [], "shelters": [], "roads": [], "events": [],
    })
    question = "how many earthquakes reported"
    answer = _incident_count_answer(question, center)
    assert answer is not None
    assert "2 earthquakes" in answer
    assert "simulated or incomplete" in answer
    assert _app_help(question) is None


def test_incident_reporting_how_to_still_matches():
    from components.chatbot import _app_help

    for question in (
        "How do I report an incident?",
        "How do I report an incident in this app?",
        "how i report incident",
    ):
        answer = _app_help(question)
        assert answer is not None
        assert "Report Incident" in answer
        assert "ANALYZE INCIDENT" in answer



def test_incident_count_question_tolerates_typos_in_count_phrase_and_disaster_type():
    from components.chatbot import _incident_count_answer

    center = CommandCenter(bundle={
        "incidents": [
            {"id": "EQ-1", "disaster_type": "Earthquake"},
            {"id": "EQ-2", "disaster_type": "Earthquake"},
            {"id": "FL-1", "disaster_type": "Flood"},
        ],
        "resources": [], "hospitals": [], "shelters": [], "roads": [], "events": [],
    })

    for question in (
        "how many earthquaks reported",
        "how meny earthquakes reported",
        "whats the number of earthquke incidents",
    ):
        answer = _incident_count_answer(question, center)
        assert answer is not None, question
        assert "2 earthquakes" in answer, question
        assert "not a verified live" in answer, question


def test_incident_count_does_not_claim_a_count_without_count_intent():
    from components.chatbot import _incident_count_answer

    center = CommandCenter(bundle={
        "incidents": [{"id": "EQ-1", "disaster_type": "Earthquake"}],
        "resources": [], "hospitals": [], "shelters": [], "roads": [], "events": [],
    })

    assert _incident_count_answer("Tell me about earthquakes", center) is None

def test_count_question_with_no_matching_records_returns_zero():
    from components.chatbot import _incident_count_answer

    center = CommandCenter(bundle={
        "incidents": [{"id": "FL-1", "disaster_type": "Flood"}],
        "resources": [], "hospitals": [], "shelters": [], "roads": [], "events": [],
    })
    answer = _incident_count_answer("how many earthquakes reported", center)
    assert answer is not None
    assert "0 earthquakes" in answer




def test_emergency_dispatch_requests_preempt_resource_lookup_and_llm(monkeypatch):
    import components.chatbot as chatbot

    monkeypatch.setattr(chatbot, "llm_configured", lambda: True)

    def unexpected_llm_call(*args, **kwargs):
        raise AssertionError("Emergency dispatch requests must be handled deterministically")

    monkeypatch.setattr(chatbot.LLMClient, "complete_json", unexpected_llm_call)
    center = _empty_center()

    for question in (
        "Can you send an ambulance?",
        "please dispatch an ambulance",
        "I need an ambulance",
        "can someone send paramedics",
        "send medical help now",
    ):
        answer = chatbot.answer_question(question, center)
        assert "local emergency services" in answer, question
        assert "cannot call responders or dispatch resources" in answer, question
        assert "resources" not in answer.casefold() or "dispatch resources" in answer.casefold(), question


def test_ambulance_availability_question_is_not_misclassified_as_dispatch_request(monkeypatch):
    import components.chatbot as chatbot

    monkeypatch.setattr(chatbot, "llm_configured", lambda: False)
    answer = chatbot.answer_question("Which ambulance resources are available?", _empty_center())

    assert "resources" in answer.casefold()
    assert "local emergency services" not in answer.casefold()

def test_chatbot_intent_collisions_route_to_the_right_answer(monkeypatch):
    import components.chatbot as chatbot

    center = CommandCenter(bundle={
        "incidents": [
            {"id": "EQ-1", "disaster_type": "Earthquake"},
            {"id": "FL-1", "disaster_type": "Flood"},
        ],
        "resources": [], "hospitals": [], "shelters": [], "roads": [], "events": [],
    })
    monkeypatch.setattr(chatbot, "llm_configured", lambda: False)

    # Count wording must not be mistaken for a how-to request.
    count_answer = chatbot.answer_question("How many incidents were reported?", center)
    assert "2 incident records" in count_answer
    assert "Report Incident" not in count_answer

    # Reporting a named hazard is still an app-workflow question, not safety advice.
    report_answer = chatbot.answer_question("How do I report an earthquake?", center)
    assert "Report Incident" in report_answer
    assert "ANALYZE INCIDENT" in report_answer
    assert "Drop, Cover, and Hold On" not in report_answer

    # A general hazard prompt should remain safety guidance, not a count.
    safety_answer = chatbot.answer_question("Earthquake help", center)
    assert "Drop, Cover, and Hold On" in safety_answer
    assert "incident records" not in safety_answer

    # Do not imply the assistant can dispatch emergency resources.
    ambulance_answer = chatbot.answer_question("Can you send an ambulance?", center)
    assert "cannot call responders or dispatch resources" in ambulance_answer
    assert "local emergency services" in ambulance_answer

    # Live-alert navigation should distinguish the alert page from the operational snapshot.
    alerts_answer = chatbot.answer_question("Are these live government alerts?", center)
    assert "Live Government Alerts" in alerts_answer
    assert "not itself a live government-alert feed" in alerts_answer
