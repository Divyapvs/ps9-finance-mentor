# backend/llm_advisor.py
# Gemini / optional Ollama + rich fallbacks. General financial education only (not regulated advice).

from __future__ import annotations

import hashlib
import json
import os
import random
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


def _api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def _call_gemini(prompt: str, temperature: float = 0.75, max_tokens: int = 1200) -> str | None:
    key = _api_key()
    if not key:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        if resp and resp.text:
            return resp.text.strip()
    except Exception:
        return None
    return None


def _call_ollama(prompt: str) -> str | None:
    model = os.getenv("OLLAMA_MODEL")
    if not model:
        return None
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    try:
        r = requests.post(
            f"{host}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.8},
            },
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        return (data.get("response") or "").strip() or None
    except Exception:
        return None


def _user_snapshot(user_data: dict[str, Any]) -> dict[str, Any]:
    """JSON-safe subset for LLM prompts."""
    out: dict[str, Any] = {}
    for k, v in user_data.items():
        if isinstance(v, (bool, int, float)):
            out[k] = v
        elif isinstance(v, str) and k == "career":
            out[k] = v[:500]
        elif isinstance(v, str) and len(v) < 80:
            try:
                out[k] = float(v.replace(",", ""))
            except ValueError:
                pass
    return out


def generate_health_score_advice(result: dict[str, Any], language: str) -> str:
    payload = {
        "score": result.get("score"),
        "missed_money": result.get("missed_money"),
        "breakdown": result.get("breakdown"),
        "months_emergency": result.get("months_emergency"),
    }
    prompt = (
        "You are Artha, a friendly money coach for everyday people in India. "
        f"Respond in 2–3 short paragraphs. Prefer language/locale: {language}. "
        "No jargon; be practical. Here is their summary (JSON):\n"
        f"{json.dumps(payload, indent=2)}"
    )
    out = _call_gemini(prompt, temperature=0.65, max_tokens=512)
    if out:
        return out
    out = _call_ollama(prompt)
    if out:
        return out
    return _fallback_health_advice(result, language)


def generate_personalized_investment_plan(
    user_data: dict[str, Any],
    result: dict[str, Any],
    language: str,
) -> str:
    """
    Long-form, numbered, step-by-step plan tied to this user's numbers.
    """
    snap = _user_snapshot(user_data)
    summary = {
        "score": result.get("score"),
        "missed_money": result.get("missed_money"),
        "breakdown": result.get("breakdown"),
        "months_emergency": result.get("months_emergency"),
        "actions": result.get("actions", [])[:5],
    }
    salt = hashlib.sha256(
        json.dumps(snap, sort_keys=True, default=str).encode()
    ).hexdigest()[:12]
    prompt = (
        "You are Artha, a clear financial educator for Indian households (general education, not a SEBI-registered advisor). "
        f"Preferred language: {language}.\n"
        f"Unique profile fingerprint: {salt} — write a fresh plan; do not copy generic templates.\n\n"
        "User situation (JSON — use these exact figures in your steps):\n"
        f"{json.dumps(snap, indent=2, default=str)}\n\n"
        "Score engine output (JSON):\n"
        f"{json.dumps(summary, indent=2, default=str)}\n\n"
        "Output format (strict):\n"
        "## Summary\nOne short paragraph in the user's voice.\n\n"
        "## Your step-by-step plan\n"
        "Numbered list 1. through at least 8. Each step must:\n"
        "- Name one concrete action (emergency fund, term insurance, health cover, 80C/ELSS/PPF, NPS, debt prepayment, SIP, asset allocation).\n"
        "- Reference their numbers where relevant (₹ amounts, age, family size, EMI, SIP).\n"
        "- Say *when* to do it (this week / this month / this quarter).\n"
        "End with one line on reviewing the plan every 6 months.\n"
    )
    out = _call_gemini(prompt, temperature=0.88, max_tokens=1200)
    if out:
        return out
    out = _call_ollama(prompt)
    if out:
        return out
    return _fallback_investment_plan(user_data, result, language, salt)


def _fallback_health_advice(result: dict[str, Any], language: str) -> str:
    score = float(result.get("score") or 0)
    missed = float(result.get("missed_money") or 0)
    months = float(result.get("months_emergency") or 0)
    b = result.get("breakdown") or {}

    if language == "tamil":
        lines = [
            f"உங்கள் மதிப்பெண் {score:.0f}/100.",
            f"அவசர நிதி: சுமார் {months:.1f} மாத செலவு சேமிப்பு உள்ளது.",
        ]
        if missed > 0:
            lines.append(f"வரி மற்றும் வாய்ப்பு செலவில் ஆண்டுக்கு ~₹{missed:,.0f} மிச்சம் செய்யலாம்.")
        lines.append("கீழே உள்ள படிப்படியான திட்டத்தைப் பின்பற்றுங்கள்.")
        return " ".join(lines)

    if language == "hindi":
        lines = [
            f"आपका स्कोर {score:.0f}/100 है।",
            f"आपात कोष: लगभग {months:.1f} महीने का खर्च बचा है।",
        ]
        if missed > 0:
            lines.append(f"कर और मौकों पर सालाना ~₹{missed:,.0f} तक बेहतर कर सकते हैं।")
        lines.append("नीचे दिए स्टेप-बाय-स्टेप प्लान से शुरुआत करें।")
        return " ".join(lines)

    lines = [
        f"Your money health score is {score:.0f} out of 100.",
        f"You have about {months:.1f} months of expenses in emergency savings.",
    ]
    if missed > 0:
        lines.append(
            f"You could improve tax and idle-money choices by roughly ₹{missed:,.0f} per year."
        )
    low = [k for k, v in b.items() if isinstance(v, (int, float)) and v < 5]
    if low:
        lines.append(f"Focus next on: {', '.join(low)}.")
    else:
        lines.append("Follow the numbered plan below.")
    return " ".join(lines)


def _fallback_investment_plan(
    user_data: dict[str, Any],
    result: dict[str, Any],
    language: str,
    salt: str,
) -> str:
    """Deterministic-but-varied copy from real numbers (no LLM)."""
    career = str(user_data.get("career") or "your situation").strip()[:120]
    inc = float(user_data.get("annual_income") or 0)
    exp_m = float(user_data.get("monthly_expense") or 20000)
    liq = float(user_data.get("liquid_savings") or 0)
    emi = float(user_data.get("monthly_emi") or 0)
    sip = float(user_data.get("monthly_sip") or 0)
    age = int(user_data.get("age") or 35)
    fam = int(user_data.get("family_size") or 2)
    life = float(user_data.get("life_cover") or 0)
    health = float(user_data.get("health_cover") or 0)
    s80 = float(user_data.get("sec80c_used") or 0)
    target_em = 6 * exp_m
    gap_em = max(0, target_em - liq)
    life_need = max(0, 10 * inc - life)
    health_need = max(0, 1_000_000 * fam - health)
    s80_gap = max(0, 150_000 - s80)

    rng = random.Random(salt)
    lead = [
        "First, stabilise cash flow",
        "Start with safety, then grow",
        "Build your base, then invest more",
    ]
    intro = rng.choice(lead)

    steps = [
        f"**Summary** — {intro}. You ({career}) are aiming from a score of **{result.get('score', 0):.0f}/100**; "
        f"annual income about **₹{inc:,.0f}** and monthly spending about **₹{exp_m:,.0f}**.",
        f"1. **Emergency fund** — Keep **₹{target_em:,.0f}** (6 months' expenses). You are short by about **₹{gap_em:,.0f}**; "
        f"move a fixed sum to a savings account or liquid fund every month until this is full (**this quarter**).",
        f"2. **Term life** — Rough cover target **₹{10 * inc:,.0f}** (10× income). Gap about **₹{life_need:,.0f}** — compare 2–3 insurers (**this month**).",
        f"3. **Health insurance** — Target about **₹{1_000_000 * fam:,.0f}** for **{fam}** family members; gap **₹{health_need:,.0f}** — top up or add a floater (**this month**).",
        f"4. **High-cost debt** — EMI **₹{emi:,.0f}/month**; if any loan is >10% p.a., prepay extra **₹1,000–5,000** monthly after emergency fund starts (**ongoing**).",
        f"5. **80C (₹1.5 lakh)** — Used **₹{s80:,.0f}**; unused headroom **₹{s80_gap:,.0f}**. Choose ELSS/PPF/NPS mix you understand (**before March 31**).",
        f"6. **Investments** — You invest **₹{sip:,.0f}/month** today. After emergency + insurance basics, consider raising SIP by **5–10%** of income or **₹500–2,000** steps (**this quarter**).",
        f"7. **Age {age} & goals** — Split long-term money: majority in diversified equity funds, rest in debt, review **once a year**.",
        "8. **Review** — Revisit this plan every **6 months** or when income or family size changes.",
    ]

    if language != "english":
        try:
            from deep_translator import GoogleTranslator

            code = {"tamil": "ta", "hindi": "hi", "telugu": "te", "bengali": "bn"}.get(language, "en")
            if code != "en":
                t = GoogleTranslator(source="en", target=code)
                steps = [t.translate(s) if s else s for s in steps]
        except Exception:
            pass

    return "\n\n".join(steps)


def generate_xray_advice(xray_data: dict[str, Any], language: str) -> str:
    prompt = (
        "You are Artha, a mutual fund coach in India. Give 4–6 bullet points of clear advice. "
        f"Language preference: {language}. Data (JSON):\n"
        f"{json.dumps(xray_data, indent=2)}"
    )
    out = _call_gemini(prompt, temperature=0.6, max_tokens=600)
    if out:
        return out
    out = _call_ollama(prompt)
    if out:
        return out
    inv = float(xray_data.get("total_invested") or 0)
    fc = int(xray_data.get("fund_count") or 0)
    if language == "tamil":
        return (
            f"₹{inv:,.0f} முதலீடு, {fc} ஃபண்ட்கள். "
            "ஒரே வகை ஃபண்ட்கள் அதிகமாக இருந்தால் ஒன்றிணைக்கவும்; "
            "செலவு விகிதம் மற்றும் மீள் balance பார்க்கவும்."
        )
    if language == "hindi":
        return (
            f"₹{inv:,.0f} निवेश, {fc} फंड। "
            "एक जैसे फंड कम करें, खर्च अनुपात देखें, और लक्ष्य के हिसाब से एलोकेशन जांचें।"
        )
    return (
        f"You have about ₹{inv:,.0f} invested across {fc} funds. "
        "Check for overlapping funds, review expense ratios, and align allocation with your goals and timeline."
    )
