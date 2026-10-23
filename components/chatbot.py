"""Grounded Streamlit response copilot with a deterministic offline fallback."""
from __future__ import annotations

import json
import re
from pathlib import Path
from difflib import SequenceMatcher
from typing import Any

import streamlit as st

from core.llm_client import LLMClient, llm_configured
from core.state import CommandCenter
from components.voice_assistant import voice_assistant

SYSTEM_PROMPT = """You are ResQ Assistant, a helpful general-purpose conversational assistant embedded in ResQ-AI, a disaster-response decision-support application.
Answer the user's actual question directly, including ordinary general-knowledge questions, explanations, app-purpose questions, writing help, and follow-up questions. Do not force every question into a short list of supported topics and do not answer unrelated questions with a generic capability menu.
Use the supplied snapshot only for operational incident/resource facts; it is not a live government alert feed. Never invent incidents, resource availability, routes, capacities, or current warnings. If asked for a current fact you cannot verify, say so clearly.
For disaster-safety questions, provide concise, conservative guidance and refer to relevant official sources when appropriate.
Explain but never change deterministic priority scores. Never authorize dispatch or claim to contact responders. Direct people to local emergency services and official local instructions for immediate danger.
Keep answers short by default: usually 1–3 sentences. Answer the question first, and add detail only when asked or needed for safety. Avoid long introductions, repeated disclaimers, and unnecessary lists. Return JSON with one string field named answer."""


def _snapshot(center: CommandCenter) -> dict[str, Any]:
    incidents = sorted(center.incidents, key=lambda row: int(row.get("priority_score") or 0), reverse=True)
    return {
        "data_mode": "Current command-center records; not a live government-alert feed",
        "metrics": center.metrics(),
        "incidents": [{
            key: row.get(key) for key in (
                "id", "disaster_type", "priority_score", "urgency", "status", "people_affected",
                "medical_emergency", "accessibility", "summary", "description", "recommended_action",
                "priority_breakdown",
            )
        } for row in incidents[:30]],
        "assignments": center.assignments[:30],
        "resources": [{key: row.get(key) for key in ("id", "name", "type", "status", "medical_capable")} for row in center.resources],
        "hospitals": [{key: row.get(key) for key in ("id", "name", "available_beds", "total_beds")} for row in center.hospitals],
        "shelters": [{key: row.get(key) for key in ("id", "name", "capacity", "occupied")} for row in center.shelters],
    }




_STOP_WORDS = {
    "a", "an", "and", "are", "can", "could", "do", "does", "for", "from",
    "give", "help", "how", "i", "in", "is", "it", "me", "my", "of", "on",
    "please", "the", "this", "to", "want", "what", "where", "which", "with",
    "would", "you", "your", "app", "application", "resq",
}


def _intent_tokens(text: str) -> list[str]:
    """Normalize natural-language input, punctuation, and common speech-to-text noise."""
    return [token for token in re.findall(r"[a-z0-9]+", text.casefold())
            if token not in _STOP_WORDS]


def _has_phrase(question: str, phrases: tuple[str, ...]) -> bool:
    """Match an intent across reordered/extra words and small spelling mistakes."""
    question_tokens = _intent_tokens(question)
    if not question_tokens:
        return False
    for phrase in phrases:
        target = _intent_tokens(phrase)
        if not target:
            continue
        matched = 0
        for word in target:
            if any(
                candidate == word or (
                    min(len(word), len(candidate)) >= 4
                    and SequenceMatcher(None, word, candidate).ratio() >= 0.78
                )
                for candidate in question_tokens
            ):
                matched += 1
        # A multiword intent must match all meaningful words. Single-word hazard
        # names remain supported so urgent safety prompts are not missed.
        if matched == len(target):
            return True
        if len(target) == 1 and len(target[0]) >= 4 and matched == 1:
            return True
    return False


def _greeting_response(question: str) -> str | None:
    tokens = _intent_tokens(question)
    greeting_words = {"hi", "hii", "hiii", "hello", "helo", "helloo", "hey", "heyy", "heyyy", "hiya", "howdy", "yo", "morning", "afternoon", "evening"}
    if tokens and len(tokens) <= 5 and any(
        token in greeting_words or (
            len(token) >= 4 and any(SequenceMatcher(None, token, greeting).ratio() >= 0.82
                                    for greeting in ("hello", "hey", "howdy"))
        )
        for token in tokens
    ):
        return (
            "Hi! I'm ResQ Assistant. You can ask in your own words—even with typos—about how to use the app, "
            "report incidents, understand priority scores, check the available incident/resource records, "
            "find shelters, use voice controls, or get disaster-safety guidance. What would you like help with?"
        )
    return None



def _fuzzy_word_match(candidate: str, target: str) -> bool:
    """Match a word exactly or tolerate a small typo without accepting short-word noise."""
    return candidate == target or (
        min(len(candidate), len(target)) >= 4
        and SequenceMatcher(None, candidate, target).ratio() >= 0.75
    )


def _contains_fuzzy_phrase(question: str, phrases: tuple[str, ...]) -> bool:
    """Find a phrase in natural input while allowing small spelling errors in its words."""
    tokens = re.findall(r"[a-z0-9]+", question.casefold())
    for phrase in phrases:
        target = re.findall(r"[a-z0-9]+", phrase.casefold())
        if not target:
            continue
        for start in range(len(tokens) - len(target) + 1):
            if all(_fuzzy_word_match(tokens[start + offset], word)
                   for offset, word in enumerate(target)):
                return True
    return False


def _is_emergency_dispatch_request(question: str) -> bool:
    """Recognize requests to obtain emergency medical help without matching availability queries."""
    if _has_phrase(question, (
        "send an ambulance", "call an ambulance", "need an ambulance",
        "dispatch an ambulance", "request an ambulance", "get an ambulance",
        "send paramedics", "send medical help", "someone needs an ambulance",
    )):
        return True

    # Broader natural phrasing: "get medical help here" or "arrange paramedics".
    # Availability questions do not contain an action asking for help.
    action = _contains_fuzzy_phrase(question, (
        "send", "call", "dispatch", "request", "get", "arrange", "bring",
        "need", "summon",
    ))
    target = _contains_fuzzy_phrase(question, (
        "ambulance", "paramedics", "medical help", "emergency medical help",
        "emergency help",
    ))
    return action and target


def _is_operational_records_question(question: str) -> bool:
    """Identify questions whose factual answer must come from the loaded operational records."""
    return _contains_fuzzy_phrase(question, (
        "incident", "incidents", "incident id", "incident status",
        "resource", "resources", "ambulance", "ambulances", "rescue team",
        "hospital bed", "hospital beds", "medical capacity",
        "shelter", "shelters", "shelter capacity", "available unit",
        "highest priority", "most urgent", "priority score",
        "dashboard summary", "response snapshot", "situation summary",
    ))


def _incident_count_answer(question: str, center: CommandCenter) -> str | None:
    """Count matching incident records from the loaded snapshot for explicit count questions."""
    count_intent = _contains_fuzzy_phrase(
        question, ("how many", "number of", "count of", "incident count", "total", "count")
    )
    if not count_intent:
        return None
    aliases = {
        "earthquake": ("earthquake", "earthquakes", "earth quake", "tremor", "aftershock"),
        "flood": ("flood", "floods", "flooding"),
        "fire": ("fire", "fires", "wildfire", "wildfires"),
        "cyclone": ("cyclone", "cyclones", "hurricane", "hurricanes", "typhoon", "typhoons"),
        "landslide": ("landslide", "landslides"),
        "storm": ("storm", "storms"),
    }
    requested = next((kind for kind, words in aliases.items()
                      if _contains_fuzzy_phrase(question, words)), None)
    if requested:
        count = 0
        for row in center.incidents:
            kind = " " + re.sub(r"[^a-z0-9]+", " ", str(row.get("disaster_type") or "").casefold()).strip() + " "
            if any(f" {word} " in kind for word in aliases[requested]):
                count += 1
        label = requested.lower()
        plural = "" if count == 1 else "s"
        return (
            f"**{count} {label}{plural} in the current ResQ-AI incident records.**\n\n"
            "This counts only records currently loaded in the app. Operational records may be simulated or incomplete; "
            "this is not a verified live or government-wide count."
        )
    if _contains_fuzzy_phrase(question, ("incident", "incidents", "disaster", "disasters", "reported", "report")):
        return (
            f"**{len(center.incidents)} incident records** are currently loaded in ResQ-AI.\n\n"
            "This is a record count, not necessarily a count of unique real-world events. The data may be simulated or incomplete."
        )
    return None

def _app_help(question: str) -> str | None:
    """Answer common how-to questions using the repository's actual app workflow."""
    q = question.casefold()
    tokens = _intent_tokens(q)

    # Explain the product's purpose explicitly, including common voice phrasing.
    if any(phrase in q for phrase in (
        "what is the purpose of this application",
        "what is the purpose of this app",
        "what is this application for",
        "what is this app for",
        "why was this app made",
        "what problem does resq solve",
        "what is resq ai",
        "explain resq ai",
        "purpose of resq",
    )):
        return (
            "**Purpose of ResQ-AI:** It helps disaster-response teams manage incident reports, review priorities, check recorded resources and shelters, "
            "and view connected public alerts. It supports coordination but does not automatically dispatch responders; some data may be simulated."
        )

    report_verbs = ("report", "reporting", "submit", "submitting", "file", "filing", "create", "creating")
    incident_terms = {
        "incident", "incidents", "emergency", "emergencies", "disaster", "disasters",
        "earthquake", "earthquakes", "flood", "floods", "fire", "fires", "cyclone", "cyclones",
        "hurricane", "hurricanes", "typhoon", "typhoons", "landslide", "landslides", "storm", "storms",
    }
    # Keep count questions out of the how-to path even when they contain
    # "reported" and a disaster name (e.g. "how many earthquakes reported").
    if _contains_fuzzy_phrase(
        q, ("how many", "number of", "count of", "incident count", "total", "count")
    ):
        return None

    # Accept common typos (e.g. "repot") without turning "how many ... reported?"
    # into a how-to request: count intent is handled earlier in answer_question.
    has_report_action = any(
        token == verb or (
            min(len(token), len(verb)) >= 4
            and SequenceMatcher(None, token, verb).ratio() >= 0.78
        )
        for token in tokens for verb in report_verbs
    )
    if has_report_action and incident_terms.intersection(tokens):
        return (
            "**How to report an incident**\n\n"
            "1. Open **Report Incident** from the sidebar.\n"
            "2. Describe what happened, the exact location, hazards, and people affected.\n"
            "3. Enter the estimated number of people affected and the latitude/longitude. "
            "Choose the observed access condition; reporter name and an image are optional.\n"
            "4. Select **ANALYZE INCIDENT** and review the assessment, priority explanation, and resource recommendation.\n\n"
            "The priority score is calculated by deterministic rules; a coordinator must verify recommendations. "
            "A report may be session-only if database storage is not configured or saving fails. Check the result message—do not assume it was saved permanently."
        )
    if _has_phrase(q, ("command center", "main screen", "overview page", "where do i see incidents")):
        return (
            "**Command Center**\n\n"
            "Open **Command Center** in the sidebar for the main operational overview and incident snapshot. "
            "Use **Incident Operations** for operational incident review, and **Report Incident** to submit a new report. "
            "Some prototype operational records may be simulated rather than live."
        )
    if _has_phrase(q, ("priority score", "why is this incident", "incident priority", "how is priority", "how are incidents ranked", "most urgent incident")):
        return (
            "**Understanding incident priority**\n\n"
            "Open an incident in the Command Center or Incident Operations, then review its priority score, urgency, "
            "and the listed factors where available. The app's deterministic rules calculate the score; the assistant can explain "
            "the displayed result but must not change it. A score is decision support, not dispatch authorization."
        )
    if _has_phrase(q, ("scenario simulator", "simulate a disaster", "run a simulation", "test a scenario")):
        return (
            "**Scenario Simulator**\n\n"
            "Open **Scenario Simulator** from the sidebar, choose the available scenario/settings, and run the simulation to inspect its modeled outcomes. "
            "Treat these as simulated planning results, not verified live incidents or a real dispatch."
        )
    if _has_phrase(q, ("government alert", "live alert", "weather alert", "current warning", "official warning", "live warning")):
        return (
            "**Live Government Alerts**\n\n"
            "Open **Live Government Alerts** in the sidebar to review the public alert feeds supported by the app. "
            "Check each item’s source and timestamp and confirm urgent instructions with the relevant official agency. "
            "The ResQ Assistant's operational snapshot is not itself a live government-alert feed, and it cannot verify every local warning."
        )
    if _has_phrase(q, ("resource status", "available resources", "rescue vehicle", "rescue team", "resource availability", "hospital bed", "shelter capacity", "shelter space", "find a shelter")):
        return (
            "**Checking resources, hospitals, and shelters**\n\n"
            "Use **Command Center** or **Incident Operations** to review available operational records; ask ResQ Assistant "
            "which resources are available, which hospitals have beds, or which shelters have space. "
            "Availability shown in the prototype can be incomplete or simulated. Confirm it with an authorized coordinator before relying on it."
        )
    if _has_phrase(q, ("route planner", "plan a route", "find a route", "road route", "route to shelter")):
        return (
            "**Route Planner**\n\n"
            "Open **Route Planner** from the sidebar and enter the route details requested by the page to inspect its route output. "
            "Do not treat a planned route as proof that roads are currently safe or open; verify road closures and evacuation directions with local authorities."
        )
    if _has_phrase(q, ("situation report", "generate a report", "export report", "incident brief", "download report")):
        return (
            "**Situation Reports**\n\n"
            "Open **Situation Reports** in the sidebar to review the report-generation options available in this version. "
            "Review the report for completeness and remember that prototype records may be simulated or incomplete before sharing it as an operational update."
        )
    if _has_phrase(q, ("change theme", "light mode", "appearance", "theme setting")):
        return (
            "**App appearance**\n\n"
            "This app uses a fixed light appearance."
        )
    if _has_phrase(q, ("upload an image", "attach a photo", "incident photo", "image upload", "photo evidence")):
        return (
            "**Adding an image to an incident report**\n\n"
            "On **Report Incident**, use the optional image uploader to attach a PNG or JPG/JPEG image, then submit the report. "
            "In this prototype, the image is stored for operator review only; it is not analyzed by computer vision."
        )
    if _has_phrase(q, ("voice assistant", "talk to resq", "microphone", "speak to the assistant", "voice mode")):
        return (
            "**Using ResQ Voice**\n\n"
            "Open **ResQ Assistant**, select **Start conversation**, allow microphone access if your browser asks, and speak after the status says it is listening. "
            "The assistant may speak its reply; use **Interrupt / ask now** to cut in and **End conversation** to stop. "
            "Browser speech support varies. This is a web voice simulation, not a direct Alexa device/account connection, and it cannot place emergency calls or dispatch teams."
        )
    if _has_phrase(q, ("database", "save permanently", "saved permanently", "where is my report saved", "report disappeared", "persistence")):
        return (
            "**Is my incident report saved?**\n\n"
            "After submitting a report, read the success or error message. The app distinguishes a permanent database save from a session-only report. "
            "If storage is not configured or saving fails, the report may disappear when the session ends; do not assume persistence without a success confirmation."
        )
    if _has_phrase(q, ("what can this app do", "app features", "what features", "how do i use this app", "how can i use resq", "help me use the app", "app help", "what pages are there")):
        return (
            "**ResQ-AI app guide**\n\n"
            "- **Command Center:** main operational overview.\n"
            "- **Report Incident:** submit and analyze a new incident.\n"
            "- **Scenario Simulator:** explore modeled disaster scenarios.\n"
            "- **ResQ Assistant:** ask about incident records, resources, and disaster-safety guidance.\n"
            "- **Live Government Alerts:** review supported public alert feeds.\n"
            "- **Incident Operations:** review operational incident records.\n"
            "- **Situation Reports:** review report-generation tools.\n"
            "- **Route Planner:** inspect route-planning outputs.\n\n"
            "Choose the matching page in the sidebar. Operational data and route outputs may be simulated or incomplete; this app does not automatically contact responders or authorize dispatch."
        )
    return None


def _safety_guidance(question: str) -> str | None:
    """Conservative general safety guidance with links to official public sources."""
    q = question.casefold()
    if _has_phrase(q, ("earthquake", "earth quake", "tremor", "aftershock")):
        return (
            "**Earthquake safety**\n\n"
            "- If shaking starts indoors: **Drop, Cover, and Hold On**; protect your head and neck and stay away from windows. "
            "Do not use elevators.\n"
            "- If outdoors: move away from buildings, walls, trees, and power lines; protect yourself from falling debris.\n"
            "- After shaking: expect aftershocks, check for injuries only when safe, leave visibly damaged buildings, and avoid downed wires. "
            "Do not re-enter a damaged structure until authorities say it is safe.\n\n"
            "Official guidance: [USGS earthquake safety](https://www.usgs.gov/programs/earthquake-hazards) · "
            "[India NDMA](https://ndma.gov.in/)\n\n"
            "This is general guidance, not a location-specific warning. Follow local emergency instructions."
        )
    if _has_phrase(q, ("flood", "flash flood", "floodwater", "waterlogging")):
        return (
            "**Flood safety**\n\n"
            "- Move to higher ground early if flooding threatens; follow official evacuation instructions.\n"
            "- Never walk, swim, or drive through floodwater. Water depth and road damage can be deceptive.\n"
            "- Keep away from drains, riverbanks, and fallen power lines. If safe, switch off electricity before water reaches equipment.\n\n"
            "Official guidance: [India NDMA](https://ndma.gov.in/) · "
            "[Ready.gov flood safety](https://www.ready.gov/floods)\n\n"
            "Check local authority alerts for current routes and evacuation orders; this assistant cannot verify road conditions."
        )
    if _has_phrase(q, ("cyclone", "hurricane", "typhoon", "severe storm", "strong wind")):
        return (
            "**Cyclone and severe-storm safety**\n\n"
            "- Follow official warnings and evacuate when instructed; do not wait for visible conditions to worsen.\n"
            "- Shelter in a sturdy building, away from windows; secure loose outdoor items only if it is safe to do so.\n"
            "- Avoid beaches, flood-prone areas, and downed wires. Do not go outside during a lull unless officials confirm the danger has passed.\n\n"
            "Official guidance: [India NDMA](https://ndma.gov.in/) · "
            "[India Meteorological Department](https://mausam.imd.gov.in/)\n\n"
            "Use IMD and local-authority updates for current warnings; this answer is not a live forecast."
        )
    if _has_phrase(q, ("fire", "wildfire", "smoke", "building burning")):
        return (
            "**Fire and smoke safety**\n\n"
            "- Leave immediately using the safest available exit; stay low under smoke and do not use elevators.\n"
            "- Once outside, stay outside and call local emergency services. Do not re-enter to retrieve belongings.\n"
            "- If trapped, close doors between you and smoke, signal from a window if safe, and follow dispatcher instructions.\n\n"
            "Official guidance: [India NDMA](https://ndma.gov.in/) · "
            "[Ready.gov](https://www.ready.gov/)\n\n"
            "If there is an active fire or immediate danger, contact emergency services now."
        )
    if _has_phrase(q, ("heatwave", "heat wave", "extreme heat", "heat stroke", "hot weather")):
        return (
            "**Extreme-heat safety**\n\n"
            "- Move to a cool or shaded place, reduce exertion, and drink water regularly if the person is conscious and able to swallow.\n"
            "- Check on older adults, young children, and people working outdoors. Never leave a person or child in a parked vehicle.\n"
            "- Confusion, fainting, seizures, or very hot skin can indicate a life-threatening emergency: seek urgent medical help and follow dispatcher guidance.\n\n"
            "Official guidance: [India NDMA](https://ndma.gov.in/) · "
            "[India Meteorological Department](https://mausam.imd.gov.in/)\n\n"
            "This is general preparedness guidance, not a diagnosis or a current local heat alert."
        )
    if any(phrase in q for phrase in (
        "emergency number", "call emergency", "immediate danger", "urgent help",
        "call an ambulance", "need an ambulance", "send an ambulance",
        "someone is injured", "person is injured", "medical emergency",
        "call the police", "call police", "call fire brigade", "need emergency help",
    )):
        return (
            "**If someone is in immediate danger**\n\n"
            "- Contact local emergency services and give the exact location, hazard, injuries, and any immediate access risks.\n"
            "- In India, **112** is the pan-India emergency response number: [official 112 portal](https://112.gov.in/). "
            "If you are elsewhere, use your local emergency number.\n"
            "- Do not enter an unsafe area or delay calling for help to use this chatbot. ResQ Assistant cannot call responders or dispatch resources."
        )
    if _has_phrase(q, ("safety advice", "prepare for disaster", "emergency kit", "preparedness", "go bag")):
        return (
            "**Basic disaster preparedness**\n\n"
            "- Keep drinking water, essential medicines, a first-aid kit, a torch, batteries/power bank, important documents, and emergency contacts ready.\n"
            "- Agree on a family meeting point and out-of-area contact; plan for children, older adults, disabilities, and pets.\n"
            "- Monitor official local alerts and know your evacuation route and nearest designated shelter before an emergency.\n\n"
            "Official guidance: [India NDMA](https://ndma.gov.in/) · "
            "[National Institute of Disaster Management](https://nidm.gov.in/)\n\n"
            "Shelter availability, routes, and warnings must be confirmed with local authorities; ResQ does not currently verify them in this chat."
        )
    return None


def smart_emergency_guidance(
    hazard: str,
    situation: str,
    injured: bool = False,
    trapped: bool = False,
) -> str:
    """Build conservative, situation-specific next steps from user-selected facts."""
    hazard = (hazard or "Other emergency").strip()
    situation = (situation or "Not sure").strip()
    guidance = {
        "Flood": {
            "Indoors": "Move to higher ground if you can do so safely and follow official evacuation instructions. Do not enter floodwater.",
            "Outdoors": "Move away from drains, riverbanks, and floodwater toward higher ground. Do not walk or drive through water.",
            "In a vehicle": "If floodwater is around the vehicle, leave it only if you can reach safer high ground without entering fast-moving water; otherwise call emergency services and follow their instructions.",
            "Near water": "Move away from the water edge to higher ground. Do not attempt to cross flooded roads or streams.",
        },
        "Earthquake": {
            "Indoors": "If shaking is happening, Drop, Cover, and Hold On; stay away from windows and do not use elevators. After shaking, leave damaged buildings when safe.",
            "Outdoors": "Move to an open area away from buildings, walls, trees, and power lines; protect your head from falling debris.",
            "In a vehicle": "Pull over away from bridges, buildings, and power lines; remain inside until shaking stops, then check for hazards before moving.",
            "Near water": "Move away from the shoreline after strong or long shaking and follow official tsunami or evacuation alerts.",
        },
        "Fire or smoke": {
            "Indoors": "Leave by the safest exit, stay low under smoke, and do not use elevators. Once outside, stay outside.",
            "Outdoors": "Move away from smoke and fire toward a safe area; do not re-enter a burning building.",
            "In a vehicle": "Stop away from smoke and flames if safe, leave the vehicle, and move to a safe area. Do not drive through smoke or fire.",
            "Near water": "Move away from fire and smoke toward a safe exit; do not enter an unsafe area to retrieve belongings.",
        },
        "Cyclone or severe storm": {
            "Indoors": "Shelter in a sturdy building away from windows. Follow official evacuation instructions and stay sheltered until authorities say it is safe.",
            "Outdoors": "Get to a sturdy shelter if it is safely reachable; avoid trees, signs, flood-prone areas, and downed wires.",
            "In a vehicle": "Avoid driving through floodwater or exposed areas. Follow official route and evacuation directions.",
            "Near water": "Move inland and away from beaches and storm-surge areas; obey evacuation instructions.",
        },
        "Building collapse": {
            "Indoors": "If the structure is unstable, leave by a safe exit if possible. Do not use elevators or re-enter a damaged building.",
            "Outdoors": "Move away from the building facade and falling debris. Keep clear of damaged structures and let responders assess them.",
            "In a vehicle": "Stop away from damaged buildings and overhead hazards if safe; do not drive through debris.",
            "Near water": "Move to a safe open area away from damaged structures and report hazards to responders.",
        },
        "Other emergency": {
            "Indoors": "Move away from the immediate hazard if you can do so safely, and follow instructions from local emergency services.",
            "Outdoors": "Move to a safer location away from the hazard and keep an exit route clear.",
            "In a vehicle": "Stop only when safe, avoid blocking responders, and follow emergency-service instructions.",
            "Near water": "Move away from the immediate hazard to a safer location and follow official instructions.",
        },
    }
    situation_steps = guidance.get(hazard, guidance["Other emergency"]).get(
        situation, "Move away from the immediate hazard if safe and follow local emergency instructions."
    )
    next_steps = [situation_steps]
    if injured:
        next_steps.append("Someone is injured: contact emergency services now and describe the injury and exact location. Avoid moving someone with a possible serious injury unless staying there is more dangerous.")
    if trapped:
        next_steps.append("Someone is trapped: call emergency services, share the exact location and safest access route, and do not enter unstable or hazardous areas to attempt a rescue.")
    if not injured and not trapped:
        next_steps.append("If anyone is hurt, trapped, or in immediate danger, contact emergency services now and share your exact location.")
    lines = [f"**Your situation: {hazard} · {situation}**", ""]
    lines.extend(f"{index}. {step}" for index, step in enumerate(next_steps, start=1))
    lines.extend([
        "",
        "In India, call [112](https://112.gov.in/) for emergency help; elsewhere, call your local emergency number. ResQ Assistant cannot contact or dispatch responders.",
        "Follow current instructions from local authorities. This guidance is general and cannot verify conditions at your location. [India NDMA](https://ndma.gov.in/)",
    ])
    return "\n".join(lines)


def _fallback(question: str, center: CommandCenter) -> str:
    q = question.lower()
    app_help = _app_help(question)
    if app_help:
        return app_help
    guidance = _safety_guidance(question)
    if guidance:
        return guidance
    metrics = center.metrics()
    active = [row for row in center.incidents if str(row.get("status", "")).lower() != "resolved"]
    active.sort(key=lambda row: int(row.get("priority_score") or 0), reverse=True)
    if _has_phrase(q, ("shelter", "evacuation centre", "evacuation center")):
        shelters = sorted(center.shelters, key=lambda row: max(0, int(row.get("capacity") or 0) - int(row.get("occupied") or 0)), reverse=True)
        lines = ["Shelter capacity in the simulated dataset:"]
        lines += [f"- **{r.get('name', r.get('id'))}**: {max(0, int(r.get('capacity') or 0)-int(r.get('occupied') or 0))} spaces reported free." for r in shelters[:5]]
        return "\n".join(lines) + "\n\nVerify capacity with local authorities before directing anyone to a shelter."
    if _has_phrase(q, ("hospital", "bed", "medical capacity")):
        lines = [f"Reported available hospital beds: **{metrics.get('hospital_beds_available', 0)}**."]
        lines += [f"- **{r.get('name', r.get('id'))}**: {r.get('available_beds', 0)} of {r.get('total_beds', 0)} beds reported available." for r in center.hospitals]
        return "\n".join(lines) + "\n\nThese are simulated figures and must be confirmed directly."
    if _has_phrase(q, ("resource", "team", "ambulance", "available unit")):
        rows = [r for r in center.resources if str(r.get("status", "")).lower() == "available"]
        return f"**{len(rows)} resources** are marked available in the demo state.\n" + "\n".join(f"- {r.get('id')}: {r.get('name', r.get('type', 'Resource'))}" for r in rows[:10]) + "\n\nConfirm availability before deployment."
    match = re.search(r"\bINC[- ]?\d+\b", question, re.I)
    if match:
        incident_id = match.group(0).upper().replace(" ", "-")
        row = next((r for r in center.incidents if str(r.get("id", "")).upper() == incident_id), None)
        if row:
            return (f"**{row.get('id')} — {row.get('disaster_type')}**\n\n"
                    f"- Priority: **{row.get('priority_score', 0)}/100 ({row.get('urgency', 'Unknown')})**\n"
                    f"- Status: {row.get('status')}\n- People affected: {row.get('people_affected', 0)}\n"
                    f"- Medical emergency: {row.get('medical_emergency', False)}\n"
                    f"- Access: {row.get('accessibility', 'Unknown')}\n"
                    f"- Recommendation: {row.get('recommended_action', 'Review with coordinator')}\n\n"
                    "The priority is calculated by the deterministic engine; this assistant cannot authorize dispatch.")
        return f"I couldn't find **{incident_id}** in the current demo snapshot."
    if _has_phrase(q, ("urgent", "critical", "highest priority", "most important", "top incident", "priorit")) and active:
        row = active[0]
        return (f"**Highest-priority active incident: {row.get('id')} — {row.get('disaster_type')}**\n\n"
                f"- Score: **{row.get('priority_score', 0)}/100 ({row.get('urgency', 'Unknown')})**\n"
                f"- People affected: {row.get('people_affected', 0)}; medical emergency: {row.get('medical_emergency', False)}\n"
                f"- Access: {row.get('accessibility', 'Unknown')}\n"
                f"- Recommendation: {row.get('recommended_action', 'Review with coordinator')}\n\n"
                "This is a deterministic ranking of simulated data, not dispatch authorization.")
    if any(phrase in q for phrase in ("what can you do", "your capabilities", "how can you help", "help me use", "what do you do")):
        return (
            "I can answer questions about incident IDs and priorities, reported rescue resources, hospital beds, "
            "shelter spaces, and safety steps for earthquakes, floods, cyclones, fires, and extreme heat. "
            "Operational records are demo data unless an authorized live source is explicitly connected. "
            "I cannot dispatch teams, contact emergency services, or verify a live emergency."
        )
    if any(phrase in q for phrase in ("hello", "hi", "hey", "good morning", "good afternoon", "good evening")) and len(q.split()) <= 6:
        return (
            "Hello! I'm ResQ Assistant. Ask me a specific question about an incident, reported resources, "
            "hospital beds, shelters, or disaster-safety guidance. I'll answer that question directly."
        )
    
    if any(phrase in q for phrase in (
        "how many active incidents",
        "active incident count",
        "incident statistics",
        "overall situation",
        "situation summary",
        "dashboard summary",
        "how many incidents",
        "summarize the response snapshot",
        "summary of the response snapshot",
        "summarize response snapshot",
    )):
        return (
            f"**Current demo snapshot**\n\n"
            f"- Active incidents: **{metrics.get('active_incidents', 0)}**\n"
            f"- Critical incidents: **{metrics.get('critical_incidents', 0)}**\n"
            f"- People affected: **{metrics.get('people_affected', 0)}**\n"
            f"- Resources marked available: **{metrics.get('available_resources', 0)}**\n\n"
            "These figures come from simulated data in the currently loaded prototype records, "
            "not verified live operations."
        )

    return (
        "I can still help with ResQ-AI's purpose, app workflows, and the operational records available in this session. "
        "A general-purpose AI model is not currently available for this question, so I don't want to guess or give you a made-up answer. "
        "The app is designed to organize incident reports, explain deterministic priorities, review resource/shelter records, "
        "show connected public alerts, and support disaster planning. "
        "For immediate danger, contact local emergency services; this assistant cannot call or dispatch responders."
    )



def answer_question(question: str, center: CommandCenter, history: list[dict[str, str]] | None = None) -> str:
    # Emergency dispatch requests outrank all data lookups, regardless of LLM configuration.
    if _is_emergency_dispatch_request(question):
        return _safety_guidance("send an ambulance") or (
            "Contact local emergency services now. ResQ Assistant cannot call responders or dispatch resources."
        )

    count_answer = _incident_count_answer(question, center)
    if count_answer:
        return count_answer

    # App how-to answers are grounded in known UI workflows and should not depend on LLM availability.
    app_help = _app_help(question)
    if app_help:
        return app_help

    # Safety-critical, well-defined guidance must not depend on LLM availability or output.
    # Keep these known hazard answers deterministic even when an AI provider is configured.
    guidance = _safety_guidance(question)
    if guidance:
        return guidance

    # Greetings should receive a stable response even when an LLM provider is configured.
    greeting = _greeting_response(question)
    if greeting:
        return greeting

    # Operational record questions must use deterministic answers from the loaded
    # snapshot, not free-form LLM text that could invent counts or availability.
    if _is_operational_records_question(question):
        return _fallback(question, center)

    if not llm_configured():
        return _fallback(question, center)
    prompt = json.dumps({
        "snapshot": _snapshot(center),
        "recent_conversation": (history or [])[-8:],
        "latest_question": question,
    }, ensure_ascii=False, default=str)
    try:
        parsed = json.loads(LLMClient().complete_json(SYSTEM_PROMPT, prompt, timeout=20))
        answer = parsed.get("answer") if isinstance(parsed, dict) else None
        if isinstance(answer, str) and answer.strip():
            return answer.strip()
    except Exception:
        pass
    return _fallback(question, center)


def render_chatbot(center: CommandCenter) -> None:
    st.markdown('<div class="resq-kicker">RESQ-AI / RESPONSE COPILOT</div>', unsafe_allow_html=True)
    st.title("ResQ Assistant")
    st.caption("Ask about incident priorities, operational records, or general disaster-safety guidance with official source links.")
    st.info("Operational records may be incomplete and are not a live government-alert feed. General safety answers link to official guidance; this assistant cannot verify local warnings, call responders, or authorize dispatch.", icon="ℹ️")
    st.caption("AI provider configured · grounded in the current snapshot" if llm_configured() else "Offline fallback active · no API key required for built-in question patterns")

    history: list[dict[str, str]] = st.session_state.setdefault("resq_chat_messages", [])
    assistant_icon = str(Path(__file__).resolve().parents[1] / "assets" / "resq-chatbot-icon.png")
    prompt = None

    voice_result = voice_assistant(
        response_text=st.session_state.get("resq_voice_response", ""),
        response_id=st.session_state.get("resq_voice_response_id", 0),
    )
    if isinstance(voice_result, dict) and voice_result.get("text"):
        voice_id = str(voice_result.get("id", ""))
        if voice_id and voice_id != st.session_state.get("resq_last_voice_id"):
            st.session_state["resq_last_voice_id"] = voice_id
            prompt = str(voice_result["text"]).strip()

    for item in history:
        avatar = assistant_icon if item["role"] == "assistant" else None
        with st.chat_message(item["role"], avatar=avatar):
            st.markdown(item["content"])

    if not history:
        st.markdown("**Try asking**")
        columns = st.columns(4)
        for column, label, question in zip(
            columns,
            ("Highest priority?", "Shelter capacity", "Resource status", "Earthquake safety"),
            (
                "Which incident is most urgent?",
                "Which shelters have space?",
                "Which rescue resources are available?",
                "What should I do during an earthquake?",
            ),
        ):
            if column.button(label, use_container_width=True):
                prompt = question

    typed = st.chat_input("Ask ResQ about the current response plan…")
    if typed:
        prompt = typed

    if prompt:
        prior = history.copy()
        history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant", avatar=assistant_icon):
            with st.spinner("Checking the current response snapshot…"):
                response = answer_question(prompt, center, prior)
            st.markdown(response)
        history.append({"role": "assistant", "content": response})
        st.session_state.resq_chat_messages = history[-24:]
        st.session_state["resq_voice_response"] = response
        st.session_state["resq_voice_response_id"] = int(
            st.session_state.get("resq_voice_response_id", 0)
        ) + 1
        st.rerun()
    with st.sidebar:
        st.markdown("### ResQ Assistant")
        st.caption("Read-only incident intelligence")
        if st.button("Clear conversation", use_container_width=True):
            st.session_state.resq_chat_messages = []
            st.rerun()
        st.caption("No dispatch actions are exposed through this chat.")
