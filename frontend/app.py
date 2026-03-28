# frontend/app.py
#
# WHAT THIS FILE DOES:
# This is the entire user interface of the app.
# Built with Streamlit — a Python library that creates web apps.
# 
# HOW STREAMLIT WORKS:
# Every time the user clicks something, the entire script re-runs from top to bottom.
# st.session_state stores data between re-runs (like a memory for the app).
# st.write() / st.markdown() puts text on screen.
# st.button() creates a clickable button.
# When a button is clicked, the variable it returns becomes True for that run.

import streamlit as st
import sys
import os

# add the backend folder to Python's path so we can import from it
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

# import our backend functions
from health_score import calculate_health_score
from llm_advisor import (
    generate_health_score_advice,
    generate_personalized_investment_plan,
    generate_xray_advice,
)
from translator import translate_to_language, get_onboarding_questions, extract_number_from_answer

# ── Page Configuration ──────────────────────────────────────────────────────
# This must be the very first Streamlit command in the file

st.set_page_config(
    page_title="Artha — Your Money Guide",
    page_icon="₹",
    layout="centered",  # "centered" looks good on mobile
    initial_sidebar_state="collapsed",
)

# ── Custom CSS for Mobile-First Design ───────────────────────────────────────
# This makes the app look like a mobile app, not a desktop website

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .artha-hero {
        background: linear-gradient(135deg, #0f3d2e 0%, #1a7a4a 50%, #2d8f5f 100%);
        color: white;
        padding: 1.25rem 1rem;
        border-radius: 20px;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px rgba(26, 122, 74, 0.35);
    }
    .artha-chip {
        display: inline-block;
        background: rgba(255,255,255,0.15);
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.75rem;
        margin-bottom: 0.5rem;
    }
    .stButton > button {
        width: 100%;
        height: 56px;
        font-size: 16px;
        font-weight: 600;
        border-radius: 14px;
        background: linear-gradient(180deg, #ff7a45 0%, #ff6b35 100%);
        color: white;
        border: none;
        margin-bottom: 8px;
        box-shadow: 0 4px 14px rgba(255, 107, 53, 0.35);
        transition: transform 0.15s ease;
    }
    .stButton > button:hover { transform: translateY(-1px); }
    div[data-testid="stTabs"] button { font-size: 15px !important; }
    .voice-btn > button {
        background: linear-gradient(180deg, #ff7a45 0%, #e85d2a 100%) !important;
        font-size: 17px !important;
        height: 64px !important;
    }
    .score-display {
        background-color: #1a7a4a;
        color: white;
        padding: 20px;
        border-radius: 16px;
        text-align: center;
        margin: 10px 0;
    }
    .missed-money-hero {
        background: linear-gradient(135deg, #1a7a4a, #0d5c3d);
        color: white;
        padding: 22px;
        border-radius: 18px;
        text-align: center;
        margin-bottom: 16px;
        box-shadow: 0 6px 24px rgba(13, 92, 61, 0.25);
    }
    .action-card {
        background: linear-gradient(90deg, #f8faf9 0%, #f0f4f2 100%);
        border-left: 4px solid #1a7a4a;
        padding: 16px;
        border-radius: 12px;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .plan-step {
        background: #fff;
        border: 1px solid #e8ece9;
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 520px;
    }
    .lang-selected {
        background-color: #1a7a4a;
        color: white;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 14px;
    }
    .quick-pick button {
        min-height: 88px !important;
        font-size: 14px !important;
        background: #fff !important;
        color: #1a1a1a !important;
        border: 2px solid #e0e4e1 !important;
        box-shadow: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Initialize Session State ──────────────────────────────────────────────────
# session_state is like a dictionary that remembers values between re-runs

if 'language' not in st.session_state:
    st.session_state.language = 'english'

if 'screen' not in st.session_state:
    st.session_state.screen = 'home'  # which screen to show

if 'user_data' not in st.session_state:
    st.session_state.user_data = {}  # stores answers to questions

if 'score_result' not in st.session_state:
    st.session_state.score_result = None

if 'question_index' not in st.session_state:
    st.session_state.question_index = 0

if 'income_level' not in st.session_state:
    st.session_state.income_level = None

# ── Language Selector ─────────────────────────────────────────────────────────

LANGUAGE_OPTIONS = {
    "English": "english",
    "தமிழ் (Tamil)": "tamil",
    "हिन्दी (Hindi)": "hindi",
    "తెలుగు (Telugu)": "telugu",
    "বাংলা (Bengali)": "bengali",
}

# language labels for UI text
UI_TEXT = {
    "english": {
        "app_name": "Artha — Your Money Guide",
        "tagline": "Free financial advice in your language",
        "missed_label": "Money you're missing this year",
        "start_btn": "Speak — Tell me about your money",
        "or_text": "or answer step by step",
        "income_question": "What is your monthly income?",
        "calculate_btn": "Show my money health score",
        "score_title": "Your Money Health Score",
        "share_btn": "Share on WhatsApp",
        "back_btn": "← Back",
        "next_btn": "Next →",
        "income_levels": ["Small shop / daily wage\n₹5k – ₹15k", "Teacher / Govt job\n₹15k – ₹40k", "Office job\n₹40k – ₹1 lakh", "Own business\n₹1 lakh+"],
    },
    "tamil": {
        "app_name": "அர்த்தா — உங்கள் பண வழிகாட்டி",
        "tagline": "உங்கள் மொழியில் இலவச நிதி ஆலோசனை",
        "missed_label": "இந்த ஆண்டு நீங்கள் இழக்கும் பணம்",
        "start_btn": "பேசுங்கள் — உங்கள் பணம் பற்றி சொல்லுங்கள்",
        "or_text": "அல்லது படிப்படியாக பதில் சொல்லுங்கள்",
        "income_question": "உங்கள் மாத வருமானம் எவ்வளவு?",
        "calculate_btn": "என் பண ஆரோக்கிய மதிப்பெண் காட்டு",
        "score_title": "உங்கள் பண ஆரோக்கிய மதிப்பெண்",
        "share_btn": "WhatsApp-ல் பகிர்",
        "back_btn": "← திரும்பு",
        "next_btn": "அடுத்தது →",
        "income_levels": ["சிறு கடை / தினசரி\n₹5k – ₹15k", "ஆசிரியர் / அரசு\n₹15k – ₹40k", "அலுவலக வேலை\n₹40k – ₹1L", "சொந்த தொழில்\n₹1L+"],
    },
    "hindi": {
        "app_name": "अर्था — आपका पैसा मार्गदर्शक",
        "tagline": "अपनी भाषा में मुफ़्त वित्तीय सलाह",
        "missed_label": "इस साल आपका गया हुआ पैसा",
        "start_btn": "बोलिए — अपने पैसे के बारे में बताइए",
        "or_text": "या कदम दर कदम जवाब दें",
        "income_question": "आपकी मासिक कमाई कितनी है?",
        "calculate_btn": "मेरा पैसा स्वास्थ्य स्कोर दिखाएं",
        "score_title": "आपका पैसा स्वास्थ्य स्कोर",
        "share_btn": "WhatsApp पर शेयर करें",
        "back_btn": "← वापस",
        "next_btn": "अगला →",
        "income_levels": ["छोटी दुकान / दिहाड़ी\n₹5k – ₹15k", "टीचर / सरकारी\n₹15k – ₹40k", "ऑफिस जॉब\n₹40k – ₹1L", "खुद का काम\n₹1L+"],
    },
}


def get_ui_text(key: str) -> str:
    """Get UI text in the current language."""
    lang = st.session_state.language
    texts = UI_TEXT.get(lang, UI_TEXT["english"])
    return texts.get(key, UI_TEXT["english"].get(key, key))


def _transcribe_uploaded(audio_obj) -> str | None:
    if audio_obj is None:
        return None
    try:
        from voice import transcribe_audio

        ext = "webm"
        name = getattr(audio_obj, "name", None) or ""
        if "." in name:
            ext = name.rsplit(".", 1)[-1].lower()
        r = transcribe_audio(audio_obj.getvalue(), file_extension=ext)
        if r.get("success") and r.get("text"):
            return str(r["text"]).strip()
    except Exception:
        return None
    return None


def _optional_voice_row(widget_prefix: str):
    """Optional voice: native recorder if Streamlit supports it, else upload-only."""
    audio_rec = None
    if hasattr(st, "audio_input"):
        audio_rec = st.audio_input(
            "🎤 Optional — record a short answer",
            key=f"rec_{widget_prefix}",
        )
    audio_up = None
    with st.expander("🎤 Optional — upload voice note instead", expanded=False):
        st.caption("You can skip this. Typing or number entry is enough.")
        audio_up = st.file_uploader(
            "Audio file",
            type=["wav", "mp3", "webm", "m4a", "ogg", "flac"],
            key=f"fu_{widget_prefix}",
            label_visibility="collapsed",
        )
    return audio_rec, audio_up


def _apply_voice_to_question_inputs(qkey: str, kind: str, voice_text: str | None):
    if not voice_text:
        return
    if kind == "text":
        st.session_state[f"txt_{qkey}"] = voice_text
    elif kind in ("rupees", "age_int", "count_int"):
        n = extract_number_from_answer(voice_text)
        if n > 0:
            st.session_state[f"num_{qkey}"] = int(n) if kind != "rupees" else float(n)


# ── Screen: Home ──────────────────────────────────────────────────────────────

def show_home_screen():
    """Language, hero, optional voice shortcut, typed income + career, quick-pick shortcuts."""

    # Quick-pick must apply BEFORE st.number_input(..., key="home_monthly") runs (Streamlit rule).
    if "_pending_quick_monthly" in st.session_state:
        m = int(st.session_state.pop("_pending_quick_monthly"))
        st.session_state.home_monthly = m
        st.session_state.home_spend = int(m * 0.7)

    if "home_monthly" not in st.session_state:
        st.session_state.home_monthly = 0
    if "home_spend" not in st.session_state:
        st.session_state.home_spend = 0

    st.markdown(
        '<div class="artha-hero"><span class="artha-chip">🇮🇳 Made for Indian families</span>'
        f"<h2 style='margin:0 0 4px 0;'>{get_ui_text('app_name')}</h2>"
        f"<p style='margin:0; opacity:0.92;'>{get_ui_text('tagline')}</p></div>",
        unsafe_allow_html=True,
    )

    st.markdown("##### 🌐 Language")
    lang_col1, lang_col2, lang_col3, lang_col4, lang_col5 = st.columns(5)
    with lang_col1:
        if st.button("EN", key="lang_en"):
            st.session_state.language = "english"
            st.rerun()
    with lang_col2:
        if st.button("தமிழ்", key="lang_ta"):
            st.session_state.language = "tamil"
            st.rerun()
    with lang_col3:
        if st.button("हिन्दी", key="lang_hi"):
            st.session_state.language = "hindi"
            st.rerun()
    with lang_col4:
        if st.button("తెలుగు", key="lang_te"):
            st.session_state.language = "telugu"
            st.rerun()
    with lang_col5:
        if st.button("বাংলা", key="lang_bn"):
            st.session_state.language = "bengali"
            st.rerun()

    if st.session_state.score_result:
        missed = st.session_state.score_result.get("missed_money", 0)
        label = get_ui_text("missed_label")
        st.markdown(
            f"""
        <div class="missed-money-hero">
            <div style="font-size: 14px; opacity: 0.9;">{label}</div>
            <div style="font-size: 40px; font-weight: bold;">₹{missed:,.0f}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("##### 🎙️ Optional: voice intro")
    if st.button(f"🎤 {get_ui_text('start_btn')}", key="voice_start_btn", type="secondary"):
        st.session_state.screen = "voice"
        st.rerun()

    st.markdown("---")
    st.markdown("##### 💼 Tell us about you (typed — most accurate)")
    career_ph = {
        "english": "e.g. school teacher, auto driver, runs a kirana shop",
        "tamil": "எ.கா. ஆசிரியர், ஓட்டுநர்",
        "hindi": "जैसे शिक्षक, ड्राइवर, दुकान",
        "telugu": "ఉదా. ఉపాధ్యాయుడు, వ్యాపారం",
        "bengali": "যেমন শিক্ষক, ব্যবসা",
    }
    career = st.text_input(
        "💼 What do you do for work?",
        key="home_career",
        placeholder=career_ph.get(st.session_state.language, career_ph["english"]),
    )
    c1, c2 = st.columns(2)
    with c1:
        st.number_input(
            "💰 Monthly take-home (₹)",
            min_value=0,
            step=500,
            key="home_monthly",
            help="Salary or business income after tax, per month",
        )
    with c2:
        st.number_input(
            "💸 Monthly spending (₹)",
            min_value=0,
            step=500,
            key="home_spend",
            help="Rough total household spend per month",
        )

    st.caption("⚡ Or tap a **quick range** to fill income & spending for you")
    income_levels = get_ui_text("income_levels")
    st.markdown('<div class="quick-pick">', unsafe_allow_html=True)
    q1, q2 = st.columns(2)
    with q1:
        if st.button(f"🏪\n{income_levels[0]}", key="income_0"):
            st.session_state._pending_quick_monthly = 10000
            st.rerun()
        if st.button(f"🏢\n{income_levels[2]}", key="income_2"):
            st.session_state._pending_quick_monthly = 70000
            st.rerun()
    with q2:
        if st.button(f"🏫\n{income_levels[1]}", key="income_1"):
            st.session_state._pending_quick_monthly = 25000
            st.rerun()
        if st.button(f"🚗\n{income_levels[3]}", key="income_3"):
            st.session_state._pending_quick_monthly = 150000
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button(f"➡️ {get_ui_text('calculate_btn')}", key="go_to_questions", type="primary"):
        monthly = int(st.session_state.home_monthly or 0)
        spend = int(st.session_state.home_spend or 0)
        if monthly <= 0:
            st.error("Please enter your monthly take-home (₹), or use a quick range.")
            return
        st.session_state.user_data["career"] = (career or "").strip() or "Not specified"
        st.session_state.user_data["annual_income"] = float(monthly) * 12
        st.session_state.user_data["monthly_expense"] = float(spend) if spend > 0 else float(monthly) * 0.7
        st.session_state.income_level = str(monthly)
        st.session_state.screen = "questions"
        st.rerun()


# ── Screen: Voice ──────────────────────────────────────────────────────────────

def show_voice_screen():
    """Optional voice intro — typing always works."""

    if st.button(get_ui_text("back_btn"), key="voice_back"):
        st.session_state.screen = "home"
        st.rerun()

    lang = st.session_state.language
    voice_prompts = {
        "english": "Tell me about your money. What do you do for work? How much do you earn? Do you have any savings? Speak naturally — I understand many Indian languages.",
        "tamil": "உங்கள் பணம் பற்றி சொல்லுங்கள். என்ன வேலை? சம்பளம்? சேமிப்பு?",
        "hindi": "अपने पैसे के बारे में बताइए। क्या काम करते हैं? कितना कमाते हैं?",
        "telugu": "మీ డబ్బు గురించి చెప్పండి. ఏ పని? ఎంత సంపాదిస్తారు?",
        "bengali": "আপনার টাকা সম্পর্কে বলুন। কী কাজ? কত আয়?",
    }

    st.markdown(f"### 🎙️ {voice_prompts.get(lang, voice_prompts['english'])}")
    st.info("Voice is **optional**. You can skip straight to typing below.")

    audio_rec, audio_up = _optional_voice_row("voice_intro")
    blob = audio_rec if audio_rec is not None else audio_up

    if blob is not None:
        with st.spinner("Understanding your answer..."):
            vt = _transcribe_uploaded(blob)
            if vt:
                st.success(f"✅ Heard ({lang}): {vt[:400]}{'…' if len(vt) > 400 else ''}")
                text = vt.lower()
                if any(
                    w in text
                    for w in (
                        "salary",
                        "earn",
                        "income",
                        "tanka",
                        "சம்பளம்",
                        "वेतन",
                        "ఆదాయం",
                    )
                ):
                    amount = extract_number_from_answer(vt)
                    if amount > 0:
                        if amount < 200000:
                            st.session_state.user_data["annual_income"] = amount * 12
                            st.session_state.user_data["monthly_expense"] = amount * 0.7
                        else:
                            st.session_state.user_data["annual_income"] = amount
                        st.session_state.user_data.setdefault(
                            "career", "From voice — add details later in the form"
                        )
                        st.balloons()
            else:
                st.warning("Could not transcribe. Please type below — that works great too.")

    st.markdown("---")
    st.markdown("##### ✍️ Type here (recommended)")
    typed_answer = st.text_area(
        "Your answer in any language:",
        height=110,
        key="voice_typed",
        placeholder="Job + monthly income + any savings you have",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("➡️ Continue to questions", key="submit_typed", type="primary"):
            if typed_answer and typed_answer.strip():
                amount = extract_number_from_answer(typed_answer)
                if amount > 0:
                    if amount < 200000:
                        st.session_state.user_data["annual_income"] = amount * 12
                        st.session_state.user_data["monthly_expense"] = amount * 0.7
                    else:
                        st.session_state.user_data["annual_income"] = amount
                line = typed_answer.strip()[:200]
                st.session_state.user_data.setdefault("career", line or "Not specified")
            st.session_state.screen = "questions"
            st.rerun()
    with col_b:
        if st.button("🏠 Skip voice — back home", key="voice_skip_home"):
            st.session_state.screen = "home"
            st.rerun()


# ── Screen: Questions (Conversational Onboarding) ────────────────────────────

def show_questions_screen():
    """One question at a time — numbers where possible; voice is optional."""

    lang = st.session_state.language
    questions = get_onboarding_questions(lang)
    answered_keys = set(st.session_state.user_data.keys())
    remaining = [q for q in questions if q["key"] not in answered_keys]

    if not remaining:
        st.session_state.screen = "calculating"
        st.rerun()
        return

    total = len(questions)
    answered = total - len(remaining)
    st.progress(answered / total)
    st.caption(f"📋 Question {answered + 1} of {total}")

    current_q = remaining[0]
    qkey = current_q["key"]
    kind = current_q.get("kind", "rupees")

    if st.button(get_ui_text("back_btn"), key="q_back"):
        st.session_state.screen = "home"
        st.rerun()

    st.markdown(f"## {current_q['text']}")
    st.caption(f"💡 {current_q['example']}")

    st.markdown("##### 🎤 Optional voice (skip if you prefer typing)")
    ar, au = _optional_voice_row(qkey)
    blob = ar if ar is not None else au
    if blob is not None:
        with st.spinner("Transcribing…"):
            vt = _transcribe_uploaded(blob)
        if vt:
            st.success(f"📝 Heard: {vt[:280]}{'…' if len(vt) > 280 else ''}")
            _apply_voice_to_question_inputs(qkey, kind, vt)
        else:
            st.caption("Could not use voice for this clip — use the fields below.")

    st.markdown("##### ✍️ Your answer")

    if kind == "text":
        st.text_input(
            "Type your answer",
            key=f"txt_{qkey}",
            placeholder=current_q["example"],
            label_visibility="collapsed",
        )
    elif kind == "rupees":
        st.number_input(
            "Amount (₹)",
            min_value=0.0,
            step=1000.0,
            format="%.0f",
            key=f"num_{qkey}",
            help="Enter your best estimate in rupees",
        )
    elif kind == "age_int":
        st.number_input(
            "Age (years)",
            min_value=18,
            max_value=100,
            step=1,
            key=f"num_{qkey}",
        )
    elif kind == "count_int":
        st.number_input(
            "Number of people",
            min_value=1,
            max_value=25,
            step=1,
            key=f"num_{qkey}",
        )

    if st.button(get_ui_text("next_btn"), key="q_next", type="primary"):
        if kind == "text":
            raw = (st.session_state.get(f"txt_{qkey}") or "").strip()
            if not raw:
                st.warning("Please type something, or use Skip.")
            else:
                st.session_state.user_data[qkey] = raw
                st.rerun()
        else:
            n = st.session_state.get(f"num_{qkey}")
            if n is None:
                st.warning("Please enter a value.")
            else:
                st.session_state.user_data[qkey] = float(n) if kind == "rupees" else int(n)
                st.rerun()

    if st.button("⏭️ Skip (use 0 for numbers)", key="q_skip"):
        if kind == "text":
            st.session_state.user_data[qkey] = "Not specified"
        else:
            st.session_state.user_data[qkey] = 0
        st.rerun()


# ── Screen: Calculating ────────────────────────────────────────────────────────

def show_calculating_screen():
    """Shows a loading screen while calculating the score."""
    
    with st.spinner("Calculating your money health score..."):
        
        # fill in any missing data with reasonable defaults
        data = st.session_state.user_data
        data.setdefault('monthly_expense', 20000)
        data.setdefault('liquid_savings', 0)
        data.setdefault('annual_income', 360000)
        data.setdefault('life_cover', 0)
        data.setdefault('health_cover', 0)
        data.setdefault('monthly_emi', 0)
        data.setdefault('sec80c_used', 0)
        data.setdefault('monthly_sip', 0)
        data.setdefault('age', 35)
        data.setdefault('has_equity', data.get('monthly_sip', 0) > 0)
        data.setdefault('has_debt', True)
        data.setdefault('has_gold', False)
        data.setdefault('only_fd', data.get('liquid_savings', 0) > 0 and data.get('monthly_sip', 0) == 0)
        data.setdefault('family_size', 2)
        data.setdefault('has_nps', False)
        data.setdefault('has_hra', False)
        data.setdefault('current_corpus', data.get('monthly_sip', 0) * 12 * 3)

        if data.get("family_size", 0) < 1:
            data["family_size"] = 2
        if data.get("age", 0) < 18:
            data["age"] = 35

        # calculate the score
        result = calculate_health_score(data)
        st.session_state.score_result = result

        lang = st.session_state.language
        try:
            advice = generate_health_score_advice(result, lang)
            st.session_state.ai_advice = translate_to_language(advice, lang)
        except Exception:
            st.session_state.ai_advice = None

        try:
            plan = generate_personalized_investment_plan(dict(data), result, lang)
            st.session_state.ai_plan = plan
        except Exception:
            st.session_state.ai_plan = None

        st.session_state.screen = 'results'
        st.rerun()


# ── Screen: Results ────────────────────────────────────────────────────────────

def show_results_screen():
    """Show the Money Health Score and action plan."""
    
    result = st.session_state.score_result
    lang = st.session_state.language
    
    if not result:
        st.session_state.screen = 'home'
        st.rerun()
        return
    
    # Score hero display
    score = result['score']
    missed = result['missed_money']
    
    score_color = "#1a7a4a" if score >= 60 else ("#f59e0b" if score >= 40 else "#dc2626")
    
    st.markdown(f"""
    <div style="background:{score_color}; color:white; padding:24px; border-radius:16px; text-align:center; margin-bottom:16px;">
        <div style="font-size:13px; opacity:0.85;">{get_ui_text('score_title')}</div>
        <div style="font-size:56px; font-weight:bold;">{score:.0f}</div>
        <div style="font-size:16px; opacity:0.9;">/ 100</div>
        <div style="margin-top:12px; font-size:13px; opacity:0.85;">{get_ui_text('missed_label')}</div>
        <div style="font-size:32px; font-weight:bold;">₹{missed:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Score breakdown radar chart
    import plotly.graph_objects as go
    
    breakdown = result['breakdown']
    categories = ['Emergency\nFund', 'Insurance', 'Investments', 'Debt\nHealth', 'Tax\nEfficiency', 'Retirement']
    values = [
        breakdown['emergency_fund'] / 20 * 100,
        breakdown['insurance'] / 20 * 100,
        breakdown['investments'] / 20 * 100,
        breakdown['debt'] / 15 * 100,
        breakdown['tax'] / 15 * 100,
        breakdown['retirement'] / 10 * 100,
    ]
    
    fig = go.Figure(data=go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(26, 122, 74, 0.2)',
        line=dict(color='#1a7a4a', width=2),
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False),
            bgcolor='rgba(0,0,0,0)',
        ),
        showlegend=False,
        margin=dict(l=40, r=40, t=20, b=20),
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Short AI summary
    if getattr(st.session_state, "ai_advice", None):
        st.markdown("### 💬 Your summary")
        st.info(st.session_state.ai_advice)

    # Personalized step-by-step plan (LLM or data-driven fallback)
    plan_md = getattr(st.session_state, "ai_plan", None)
    if plan_md:
        st.markdown("### 📒 Your personalized investment roadmap")
        st.caption("General education only — not a substitute for a licensed advisor.")
        st.markdown(plan_md)

    # Action items
    st.markdown("### ✅ Priority actions")
    
    action_icons = {1: "🔴", 2: "🟡", 3: "🟠", 4: "🟢"}
    
    for i, action in enumerate(result['actions'][:3]):  # show top 3
        icon = action_icons.get(action['priority'], "📌")
        
        translated_title = translate_to_language(action['title'], lang)
        translated_detail = translate_to_language(action['detail'], lang)
        
        st.markdown(f"""
        <div class="action-card">
            <strong>{icon} {translated_title}</strong><br>
            <span style="font-size:14px; color:#555;">{translated_detail}</span><br>
            <span style="font-size:12px; color:#888;">{action['timeline']}</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Share button (WhatsApp)
    score_text = f"My money health score: {score:.0f}/100. Missing ₹{missed:,.0f}/year. Check yours at artha.app"
    whatsapp_url = f"https://wa.me/?text={score_text.replace(' ', '%20')}"
    
    st.markdown(f"""
    <a href="{whatsapp_url}" target="_blank">
        <div style="background:#25D366; color:white; padding:16px; border-radius:14px; text-align:center; font-size:16px; font-weight:bold; margin:16px 0;">
            📲 {get_ui_text('share_btn')}
        </div>
    </a>
    """, unsafe_allow_html=True)
    
    # CAMS Upload section
    st.markdown("---")
    st.markdown("### Upload your investment statement (optional)")
    st.caption("Have mutual funds? Upload your CAMS statement for a detailed analysis.")
    
    uploaded_file = st.file_uploader("Choose your CAMS PDF", type=['pdf'], key="cams_upload")
    
    if uploaded_file:
        with st.spinner("Reading your investments..."):
            try:
                # save uploaded file temporarily
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name
                
                from parser import parse_cams_statement
                cams_data = parse_cams_statement(tmp_path)
                os.remove(tmp_path)
                
                if cams_data.get('error'):
                    st.error(cams_data['error'])
                else:
                    st.success(f"Found {cams_data['summary']['fund_count']} funds, {cams_data['summary']['transaction_count']} transactions")
                    
                    # show xray advice
                    xray_data = {
                        'total_invested': cams_data['summary']['total_invested'],
                        'fund_count': cams_data['summary']['fund_count'],
                        'xirr': 11.2,  # placeholder — real XIRR needs more calculation
                        'benchmark_xirr': 14.8,
                        'overlap_score': 45,
                        'expense_drag_rupees': cams_data['summary']['total_invested'] * 0.018,
                    }
                    
                    xray_advice = generate_xray_advice(xray_data, lang)
                    st.info(xray_advice)
                    
            except Exception as e:
                st.error(f"Could not read file: {e}")
    
    # Back button
    if st.button(get_ui_text('back_btn') + " Home", key="results_back"):
        st.session_state.screen = 'home'
        st.rerun()


# ── CAMS X-Ray Tab ─────────────────────────────────────────────────────────────

def show_xray_screen():
    """Standalone CAMS X-Ray analysis page."""
    
    st.markdown("## Portfolio X-Ray")
    st.caption("Upload your CAMS statement to see how your investments are really performing")
    
    uploaded_file = st.file_uploader("Choose CAMS PDF", type=['pdf'])
    
    if uploaded_file:
        with st.spinner("Analysing your investments (10 seconds)..."):
            
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name
            
            try:
                from parser import parse_cams_statement
                data = parse_cams_statement(tmp_path)
                os.remove(tmp_path)
                
                if data.get('error'):
                    st.error(data['error'])
                    return
                
                summary = data['summary']
                
                # Display results
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Invested", f"₹{summary['total_invested']:,.0f}")
                with col2:
                    st.metric("Number of Funds", summary['fund_count'])
                with col3:
                    st.metric("Transactions", summary['transaction_count'])
                
                # Funds list
                st.markdown("### Your funds:")
                for fund in data['funds']:
                    st.markdown(f"• {fund}")
                
                # AI advice
                xray_data = {
                    'total_invested': summary['total_invested'],
                    'fund_count': summary['fund_count'],
                    'xirr': 11.2,
                    'benchmark_xirr': 14.8,
                    'overlap_score': 45,
                    'expense_drag_rupees': summary['total_invested'] * 0.018,
                }
                
                with st.spinner("Getting personalized advice..."):
                    advice = generate_xray_advice(xray_data, st.session_state.language)
                    translated = translate_to_language(advice, st.session_state.language)
                    st.info(translated)
                    
            except Exception as e:
                st.error(f"Analysis failed: {e}")


# ── Main App Router ───────────────────────────────────────────────────────────
# This section decides which screen to show

def main():
    """Main app entry point."""
    
    # Navigation tabs at the top
    tab1, tab2, tab3 = st.tabs(["🏠 Home", "📊 X-Ray", "👨‍👩‍👧 Family"])
    
    with tab1:
        # route to correct screen
        screen = st.session_state.screen
        
        if screen == 'home':
            show_home_screen()
        elif screen == 'voice':
            show_voice_screen()
        elif screen == 'questions':
            show_questions_screen()
        elif screen == 'calculating':
            show_calculating_screen()
        elif screen == 'results':
            show_results_screen()
    
    with tab2:
        show_xray_screen()
    
    with tab3:
        st.markdown("## Help a family member")
        st.caption("Help your parents or relatives check their money health")
        
        family_name = st.text_input("Family member's name:")
        
        if family_name:
            st.markdown(f"Answering questions on behalf of **{family_name}**")
            
            # reset and go to questions for family member
            if st.button(f"Start for {family_name}"):
                st.session_state.user_data = {}
                st.session_state.screen = 'questions'
                st.session_state.question_index = 0
                st.rerun()


# Run the app (Streamlit executes this file as __main__)
if __name__ == "__main__":
    main()