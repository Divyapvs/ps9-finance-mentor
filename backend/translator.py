# backend/translator.py
# Free UI translation via deep-translator (no API key). Falls back to English on failure.

from __future__ import annotations

import re
from typing import Any

_LANG_CODE = {
    "english": "en",
    "tamil": "ta",
    "hindi": "hi",
    "telugu": "te",
    "bengali": "bn",
}

# How each question is collected in the UI (see frontend show_questions_screen).
_QUESTION_KIND: dict[str, str] = {
    "career": "text",
    "annual_income": "rupees",
    "monthly_expense": "rupees",
    "liquid_savings": "rupees",
    "life_cover": "rupees",
    "health_cover": "rupees",
    "monthly_emi": "rupees",
    "monthly_sip": "rupees",
    "sec80c_used": "rupees",
    "age": "age_int",
    "family_size": "count_int",
}

_QUESTIONS: dict[str, list[dict[str, Any]]] = {
    "english": [
        {
            "key": "career",
            "text": "What is your work or profession?",
            "example": "e.g. teacher, driver, shop owner, farmer",
        },
        {
            "key": "annual_income",
            "text": "What is your yearly income (before tax)?",
            "example": "e.g. 6 lakh or 600000",
        },
        {
            "key": "monthly_expense",
            "text": "Roughly how much do you spend each month?",
            "example": "e.g. 25000",
        },
        {
            "key": "liquid_savings",
            "text": "How much do you have in savings that you can use in an emergency (bank + liquid funds)?",
            "example": "e.g. 1 lakh",
        },
        {
            "key": "life_cover",
            "text": "Total life insurance cover (all policies combined)?",
            "example": "e.g. 0 if none, or 50 lakh",
        },
        {
            "key": "health_cover",
            "text": "Total health insurance cover for your family?",
            "example": "e.g. 5 lakh",
        },
        {
            "key": "monthly_emi",
            "text": "Total EMI you pay per month (all loans)?",
            "example": "e.g. 15000 or 0",
        },
        {
            "key": "monthly_sip",
            "text": "How much do you invest monthly (SIP, stocks, etc.)?",
            "example": "e.g. 5000 or 0",
        },
        {
            "key": "sec80c_used",
            "text": "How much have you put in 80C this year (ELSS, PPF, etc.)? Max 1.5 lakh.",
            "example": "e.g. 150000",
        },
        {
            "key": "age",
            "text": "How old are you?",
            "example": "e.g. 35",
        },
        {
            "key": "family_size",
            "text": "How many people are in your household?",
            "example": "e.g. 4",
        },
    ],
    "tamil": [
        {
            "key": "career",
            "text": "நீங்கள் என்ன தொழில் / வேலை செய்கிறீர்கள்?",
            "example": "எ.கா. ஆசிரியர், ஓட்டுநர், கடை",
        },
        {
            "key": "annual_income",
            "text": "உங்கள் வருட வருமானம் (வரி முன்) எவ்வளவு?",
            "example": "எ.கா. 6 லட்சம்",
        },
        {
            "key": "monthly_expense",
            "text": "மாதம் எவ்வளவு செலவு செய்கிறீர்கள்?",
            "example": "எ.கா. 25000",
        },
        {
            "key": "liquid_savings",
            "text": "அவசரத்திற்கு எடுக்கக்கூடிய சேமிப்பு (வங்கி + லிக்விட் ஃபண்ட்)?",
            "example": "எ.கா. 1 லட்சம்",
        },
        {
            "key": "life_cover",
            "text": "மொத்த ஆயுள் காப்பீட்டு தொகை?",
            "example": "இல்லையெனில் 0",
        },
        {
            "key": "health_cover",
            "text": "குடும்பத்திற்கான மொத்த ஆரோக்கிய காப்பீடு?",
            "example": "எ.கா. 5 லட்சம்",
        },
        {
            "key": "monthly_emi",
            "text": "மாதம் மொத்த EMI?",
            "example": "எ.கா. 15000",
        },
        {
            "key": "monthly_sip",
            "text": "மாதம் எவ்வளவு முதலீடு (SIP முதலியன)?",
            "example": "எ.கா. 5000",
        },
        {
            "key": "sec80c_used",
            "text": "இந்த ஆண்டு 80C-ல் எவ்வளவு?",
            "example": "அதிகபட்சம் 1.5 லட்சம்",
        },
        {
            "key": "age",
            "text": "வயது எவ்வளவு?",
            "example": "எ.கா. 35",
        },
        {
            "key": "family_size",
            "text": "குடும்பத்தில் எத்தனை பேர்?",
            "example": "எ.கா. 4",
        },
    ],
    "hindi": [
        {
            "key": "career",
            "text": "आप क्या काम करते हैं?",
            "example": "जैसे शिक्षक, ड्राइवर, दुकानदार, किसान",
        },
        {
            "key": "annual_income",
            "text": "आपकी सालाना कमाई (टैक्स से पहले) कितनी है?",
            "example": "जैसे 6 लाख",
        },
        {
            "key": "monthly_expense",
            "text": "हर महीने लगभग कितना खर्च होता है?",
            "example": "जैसे 25000",
        },
        {
            "key": "liquid_savings",
            "text": "आपातकाल में इस्तेमाल हो सकनी कुल बचत?",
            "example": "जैसे 1 लाख",
        },
        {
            "key": "life_cover",
            "text": "कुल जीवन बीमा कवर?",
            "example": "नहीं तो 0",
        },
        {
            "key": "health_cover",
            "text": "परिवार के लिए कुल स्वास्थ्य बीमा?",
            "example": "जैसे 5 लाख",
        },
        {
            "key": "monthly_emi",
            "text": "कुल मासिक EMI?",
            "example": "जैसे 15000",
        },
        {
            "key": "monthly_sip",
            "text": "मासिक निवेश (SIP आदि)?",
            "example": "जैसे 5000",
        },
        {
            "key": "sec80c_used",
            "text": "इस साल 80C में कितना?",
            "example": "अधिकतम 1.5 लाख",
        },
        {
            "key": "age",
            "text": "उम्र क्या है?",
            "example": "जैसे 35",
        },
        {
            "key": "family_size",
            "text": "परिवार में कितने लोग?",
            "example": "जैसे 4",
        },
    ],
    "telugu": [
        {
            "key": "career",
            "text": "మీరు ఏ పని చేస్తారు?",
            "example": "ఉదా. ఉపాధ్యాయుడు, డ్రైవర్, దుకాణం",
        },
        {
            "key": "annual_income",
            "text": "మీ వార్షిక ఆదాయం (పన్ను ముందు) ఎంత?",
            "example": "ఉదా. 6 లక్షలు",
        },
        {
            "key": "monthly_expense",
            "text": "నెలకు సుమారు ఎంత ఖర్చు అవుతుంది?",
            "example": "ఉదా. 25000",
        },
        {
            "key": "liquid_savings",
            "text": "అత్యవసరానికి వాడగల మొత్తం పొదుపు?",
            "example": "ఉదా. 1 లక్ష",
        },
        {
            "key": "life_cover",
            "text": "మొత్తం జీవిత బీమా కవరేజ్?",
            "example": "లేకపోతే 0",
        },
        {
            "key": "health_cover",
            "text": "కుటుంబానికి మొత్తం ఆరోగ్య బీమా?",
            "example": "ఉదా. 5 లక్షలు",
        },
        {
            "key": "monthly_emi",
            "text": "నెలకు మొత్తం EMI?",
            "example": "ఉదా. 15000",
        },
        {
            "key": "monthly_sip",
            "text": "నెలకు ఎంత పెట్టుబడి (SIP)?",
            "example": "ఉదా. 5000",
        },
        {
            "key": "sec80c_used",
            "text": "ఈ సంవత్సరం 80Cలో ఎంత?",
            "example": "గరిష్ఠం 1.5 లక్షలు",
        },
        {
            "key": "age",
            "text": "వయస్సు ఎంత?",
            "example": "ఉదా. 35",
        },
        {
            "key": "family_size",
            "text": "కుటుంబంలో ఎంత మంది?",
            "example": "ఉదా. 4",
        },
    ],
    "bengali": [
        {
            "key": "career",
            "text": "আপনি কী কাজ করেন?",
            "example": "যেমন শিক্ষক, ড্রাইভার, দোকানদার",
        },
        {
            "key": "annual_income",
            "text": "আপনার বার্ষিক আয় (করের আগে) কত?",
            "example": "যেমন ৬ লাখ",
        },
        {
            "key": "monthly_expense",
            "text": "প্রতি মাসে প্রায় কত খরচ হয়?",
            "example": "যেমন ২৫০০০",
        },
        {
            "key": "liquid_savings",
            "text": "জরুরিতে ব্যবহারযোগ্য মোট সঞ্চয়?",
            "example": "যেমন ১ লাখ",
        },
        {
            "key": "life_cover",
            "text": "মোট জীবন বীমা কভার?",
            "example": "না থাকলে ০",
        },
        {
            "key": "health_cover",
            "text": "পরিবারের জন্য মোট স্বাস্থ্য বীমা?",
            "example": "যেমন ৫ লাখ",
        },
        {
            "key": "monthly_emi",
            "text": "মাসিক মোট EMI?",
            "example": "যেমন ১৫০০০",
        },
        {
            "key": "monthly_sip",
            "text": "মাসিক বিনিয়োগ (SIP)?",
            "example": "যেমন ৫০০০",
        },
        {
            "key": "sec80c_used",
            "text": "এই বছর ৮০C-তে কত?",
            "example": "সর্বোচ্চ ১.৫ লাখ",
        },
        {
            "key": "age",
            "text": "বয়স কত?",
            "example": "যেমন ৩৫",
        },
        {
            "key": "family_size",
            "text": "পরিবারে কজন?",
            "example": "যেমন ৪",
        },
    ],
}


def translate_to_language(text: str, lang: str) -> str:
    if not text or not str(text).strip():
        return text
    code = _LANG_CODE.get(lang, "en")
    if code == "en":
        return text
    try:
        from deep_translator import GoogleTranslator

        return GoogleTranslator(source="auto", target=code).translate(str(text))
    except Exception:
        return text


def get_onboarding_questions(lang: str) -> list[dict[str, Any]]:
    raw = list(_QUESTIONS.get(lang, _QUESTIONS["english"]))
    out: list[dict[str, Any]] = []
    for q in raw:
        d = dict(q)
        d["kind"] = _QUESTION_KIND.get(q["key"], "rupees")
        out.append(d)
    return out


def extract_number_from_answer(text: str) -> float:
    """Pull a rupee amount from free text (handles lakh, crore, k, commas)."""
    if not text:
        return 0.0
    raw = str(text).strip()
    # normalize
    t = raw.replace("₹", " ").replace(",", "")
    t = re.sub(r"\s+", " ", t, flags=re.UNICODE).lower()

    def _scale_number(num: float, mult: float) -> float:
        return num * mult

    # crore / karod
    m = re.search(
        r"([\d.]+)\s*(crore|karod|কোটি|కోట్లు|கோடி)",
        t,
        re.I,
    )
    if m:
        return _scale_number(float(m.group(1)), 1e7)

    # lakh / lac
    m = re.search(
        r"([\d.]+)\s*(lakh|lac|lakhs|lacs|লাখ|లక్ష|லட்சம்)",
        t,
        re.I,
    )
    if m:
        return _scale_number(float(m.group(1)), 1e5)

    # trailing k
    m = re.search(r"([\d.]+)\s*k\b", t)
    if m:
        return _scale_number(float(m.group(1)), 1e3)

    # plain numbers — take the largest (works for age and rupee amounts)
    nums: list[float] = []
    for m in re.finditer(r"\d[\d,]*(?:\.\d+)?", raw.replace("₹", " ")):
        try:
            nums.append(float(m.group(0).replace(",", "")))
        except ValueError:
            continue
    if not nums:
        return 0.0
    return max(nums)
