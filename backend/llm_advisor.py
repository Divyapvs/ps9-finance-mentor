# backend/llm_advisor.py
# Gemini / optional Ollama + fast fallbacks. General financial education only (not regulated advice).

from __future__ import annotations

import hashlib
import json
import os
import random
from typing import Any

import requests
from dotenv import load_dotenv

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))


def _api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def _call_gemini(prompt: str, temperature: float = 0.55, max_tokens: int = 900) -> str | None:
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
    num_predict = int(os.getenv("OLLAMA_NUM_PREDICT", "700"))
    temp = float(os.getenv("OLLAMA_TEMPERATURE", "0.65"))
    try:
        r = requests.post(
            f"{host}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temp,
                    "num_predict": num_predict,
                },
            },
            timeout=int(os.getenv("OLLAMA_TIMEOUT_SEC", "180")),
        )
        r.raise_for_status()
        data = r.json()
        return (data.get("response") or "").strip() or None
    except Exception:
        return None


def _user_snapshot(user_data: dict[str, Any]) -> dict[str, Any]:
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


def _parse_combined_llm_output(text: str) -> tuple[str, str] | None:
    if "===SUMMARY===" not in text or "===STEPS===" not in text:
        return None
    try:
        rest = text.split("===SUMMARY===", 1)[1]
        summary_part, steps_part = rest.split("===STEPS===", 1)
        summary = summary_part.strip()
        plan = steps_part.strip()
        if summary and plan:
            return summary, plan
    except (ValueError, IndexError):
        return None
    return None


def generate_advice_and_plan_fast(
    user_data: dict[str, Any],
    result: dict[str, Any],
    language: str,
) -> tuple[str, str, bool]:
    """
    One LLM round-trip when possible (faster than two calls).
    Returns (summary_text, plan_markdown, used_llm).
    Plain language; no duplicate translate needed when used_llm True.
    """
    snap = _user_snapshot(user_data)
    payload = {
        "profile": snap,
        "score": round(float(result.get("score", 0)), 1),
        "missed_money_yearly": round(float(result.get("missed_money", 0)), 0),
        "months_of_expenses_saved": round(float(result.get("months_emergency", 0)), 1),
        "breakdown_out_of_100": result.get("breakdown", {}),
    }
    prompt = f"""You are Artha, a friendly money guide for families in India (general education only; you are not a licensed advisor).

Write in: **{language}** (match that language fully).

Rules:
- Use **very simple** words. A 15-year-old should understand.
- If you mention ELSS, PPF, SIP, or NPS, add **one short plain explanation** in brackets.
- No long paragraphs in the summary.
- Be specific to the numbers in the JSON.

User situation (JSON): {json.dumps(payload, separators=(",", ":"), default=str)}

Output **exactly** in this shape (keep the headers):

===SUMMARY===
Write 3–5 short sentences: what their score means, biggest win, one gentle warning in everyday language.

===STEPS===
Write 6–8 **numbered** steps (1. 2. 3. …). Each step: **what to do** → **when** (this week / this month) → **why it matters** in one plain line. Use their rupee amounts where relevant.

Keep the whole answer under ~800 words."""

    raw = _call_gemini(prompt, temperature=0.5, max_tokens=950)
    if not raw:
        raw = _call_ollama(prompt)

    parsed = _parse_combined_llm_output(raw) if raw else None
    if parsed:
        return parsed[0], parsed[1], True

    salt = hashlib.sha256(
        json.dumps(snap, sort_keys=True, default=str).encode()
    ).hexdigest()[:12]
    fb_sum = _fallback_health_advice(result, language)
    fb_plan = _fallback_investment_plan(user_data, result, language, salt)
    return fb_sum, fb_plan, False


def generate_health_score_advice(result: dict[str, Any], language: str) -> str:
    """Quick summary from score only (no LLM). Use generate_advice_and_plan_fast in the app."""
    return _fallback_health_advice(result, language)


def generate_personalized_investment_plan(
    user_data: dict[str, Any],
    result: dict[str, Any],
    language: str,
) -> str:
    """Backward-compatible; prefer generate_advice_and_plan_fast."""
    _, p, _ = generate_advice_and_plan_fast(user_data, result, language)
    return p


def _fallback_health_advice(result: dict[str, Any], language: str) -> str:
    score = float(result.get("score") or 0)
    missed = float(result.get("missed_money") or 0)
    months = float(result.get("months_emergency") or 0)
    b = result.get("breakdown") or {}

    if language == "tamil":
        lines = [
            f"உங்கள் பண ஆரோக்கிய மதிப்பெண் {score:.0f} / 100.",
            f"இது என்ன அர்த்தம்: உங்கள் சேமிப்பு சுமார் {months:.1f} மாத செலவுக்கு போதும்.",
        ]
        if missed > 0:
            lines.append(
                f"வரி மற்றும் சேமிப்பு தேர்வுகளை சிறப்பாக செய்தால் ஆண்டுக்கு சுமார் ₹{missed:,.0f} வரை மிச்சம் படலாம்."
            )
        lines.append("கீழே எளிய படிநிலை வழிகாட்டி உள்ளது — ஒவ்வொன்றாக செய்யுங்கள்.")
        return " ".join(lines)

    if language == "hindi":
        lines = [
            f"आपका पैसे की सेहत स्कोर {score:.0f} में से 100 है।",
            f"मतलब: आपके पास लगभग {months:.1f} महीने के खर्च जितनी बचत है।",
        ]
        if missed > 0:
            lines.append(
                f"टैक्स और बचत के बेहतर विकल्पों से सालाना लगभग ₹{missed:,.0f} तक बेहतर कर सकते हैं।"
            )
        lines.append("नीचे आसान चरण-दर-चरण सूची है — एक-एक करके करें।")
        return " ".join(lines)

    lines = [
        f"Your **money health score** is **{score:.0f} out of 100**.",
        f"In simple terms: you have about **{months:.1f} months** of spending saved as a safety cushion.",
    ]
    if missed > 0:
        lines.append(
            f"With smarter tax and savings choices, you might keep closer to **₹{missed:,.0f} more per year** in your pocket (rough estimate)."
        )
    low = [k.replace("_", " ") for k, v in b.items() if isinstance(v, (int, float)) and v < 5]
    if low:
        lines.append(f"**Focus areas next:** {', '.join(low)}.")
    else:
        lines.append("Follow the **numbered steps** below — do one at a time.")
    return " ".join(lines)


def _fallback_investment_plan(
    user_data: dict[str, Any],
    result: dict[str, Any],
    language: str,
    salt: str,
) -> str:
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
    intro = rng.choice(
        [
            "Start with safety, then grow your money slowly.",
            "Fix the basics first, then think about bigger investments.",
            "Small steady steps beat one big confusing move.",
        ]
    )

    steps = [
        f"**What this means** — {intro} You said you work as: *{career}*. Score **{result.get('score', 0):.0f}/100**. "
        f"Yearly income about **₹{inc:,.0f}**, monthly spending about **₹{exp_m:,.0f}**.",
        f"1. **Emergency jar** — Aim for **₹{target_em:,.0f}** (about **6 months** of spending). "
        f"You are short by about **₹{gap_em:,.0f}**. Each month, move a fixed amount to savings or a **liquid fund** (like a savings account that earns a bit more) until you reach this.",
        f"2. **Life cover (term insurance)** — Rough guide: **10× yearly income** ≈ **₹{10 * inc:,.0f}**. Gap ≈ **₹{life_need:,.0f}**. Compare **2–3** term plans online this month.",
        f"3. **Health insurance** — For **{fam}** people, a common goal is **₹{1_000_000 * fam:,.0f}** total cover. Gap ≈ **₹{health_need:,.0f}**. Look for a **family floater** you can afford.",
        f"4. **Loans / EMI** — You pay **₹{emi:,.0f}/month** in EMI. If any loan charges **very high interest**, pay a little extra on that loan after your emergency fund has started.",
        f"5. **Tax saving (Section 80C)** — You used **₹{s80:,.0f}** of the **₹1,50,000** yearly limit. Unused room ≈ **₹{s80_gap:,.0f}**. Options include **PPF** (safe, long lock-in) or **ELSS** (mutual funds with 3-year lock-in) — pick what you understand.",
        f"6. **Monthly investing (SIP)** — You invest **₹{sip:,.0f}/month** today. After insurance basics, try increasing SIP by a small fixed amount every few months.",
        f"7. **Age {age}** — Long-term money can go mostly into **diversified equity funds**; keep some in safer debt if you need money in **under 5 years**.",
        "8. **Check-in** — Re-read this list every **6 months** or when your income or family size changes.",
    ]

    text = "\n\n".join(steps)
    if language != "english":
        try:
            from deep_translator import GoogleTranslator

            code = {"tamil": "ta", "hindi": "hi", "telugu": "te", "bengali": "bn"}.get(language, "en")
            if code != "en":
                return GoogleTranslator(source="en", target=code).translate(text)
        except Exception:
            pass
    return text


def generate_xray_advice(xray_data: dict[str, Any], language: str) -> str:
    prompt = (
        f"Language: {language}. Simple bullets, no jargon. Max 5 bullets. JSON: "
        + json.dumps(xray_data, separators=(",", ":"))
    )
    out = _call_gemini(prompt, temperature=0.5, max_tokens=400)
    if out:
        return out
    out = _call_ollama(prompt)
    if out:
        return out
    inv = float(xray_data.get("total_invested") or 0)
    fc = int(xray_data.get("fund_count") or 0)
    if language == "tamil":
        return (
            f"₹{inv:,.0f} முதலீடு, {fc} ஃபண்ட்கள். ஒரே மாதிரி ஃபண்ட்கள் குறைக்கவும்; "
            "செலவு விகிதம் பார்க்கவும்."
        )
    if language == "hindi":
        return (
            f"₹{inv:,.0f} निवेश, {fc} फंड। समान फंड घटाएँ, खर्च अनुपात देखें।"
        )
    return (
        f"About **₹{inv:,.0f}** in **{fc}** funds. Check for **duplicate** funds, **fees**, and whether mix matches your **goal** and **timeline**."
    )
