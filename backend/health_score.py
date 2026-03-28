# backend/health_score.py
#
# WHAT THIS FILE DOES:
# Takes the user's financial data (income, savings, insurance, etc.)
# and calculates a score out of 100 across 6 dimensions.
# Also calculates the "missed money" — how much they're losing per year.
#
# THE 6 DIMENSIONS:
# 1. Emergency fund (20 points) — do they have 6 months of expenses saved?
# 2. Insurance (20 points) — enough life and health cover?
# 3. Investments (20 points) — are they diversified?
# 4. Debt (15 points) — is their EMI-to-income ratio healthy?
# 5. Tax efficiency (15 points) — are they using all deductions?
# 6. Retirement (10 points) — are they on track?


def calculate_health_score(user_data: dict) -> dict:
    """
    Calculate the complete Money Health Score.
    
    user_data: dictionary with these keys:
        monthly_expense: how much they spend per month (rupees)
        liquid_savings: savings account + liquid fund balance
        annual_income: yearly income before tax
        life_cover: total life insurance cover amount
        health_cover: total health insurance cover amount
        monthly_emi: total monthly loan EMI payments
        sec80c_used: amount invested in 80C instruments this year
        monthly_sip: monthly mutual fund investment
        age: user's age
        has_equity: True if they have any equity mutual funds
        has_debt: True if they have any debt funds
        has_gold: True if they have any gold investment
        only_fd: True if all savings are in FD
        family_size: number of family members
        has_nps: True if they invest in NPS
        has_hra: True if they claim HRA
        current_corpus: total invested amount so far
    
    Returns:
        score: total score out of 100
        breakdown: score for each dimension
        missed_money: how much they're losing per year (rupees)
        actions: list of specific things to fix
        insights: language for showing to user
    """
    
    # ── Dimension 1: Emergency Fund (max 20 points) ──────────────────────
    
    monthly_expense = user_data.get('monthly_expense', 20000)
    liquid_savings = user_data.get('liquid_savings', 0)
    
    # target is 6 months of expenses
    emergency_target = 6 * monthly_expense
    
    # score = (months_covered / 6) × 20, but max is 20
    months_covered = liquid_savings / monthly_expense if monthly_expense > 0 else 0
    emergency_score = min(months_covered / 6, 1.0) * 20
    
    # how much more they need
    emergency_gap = max(0, emergency_target - liquid_savings)
    
    # ── Dimension 2: Insurance (max 20 points) ──────────────────────────
    
    annual_income = user_data.get('annual_income', 600000)
    life_cover = user_data.get('life_cover', 0)
    health_cover = user_data.get('health_cover', 0)
    family_size = user_data.get('family_size', 2)
    
    # life insurance target = 10 times annual income
    life_target = 10 * annual_income
    life_score = min(life_cover / life_target, 1.0) * 10 if life_target > 0 else 0
    
    # health insurance target = 10 lakh per family member
    health_target = 1000000 * family_size
    health_score = min(health_cover / health_target, 1.0) * 10 if health_target > 0 else 0
    
    insurance_score = life_score + health_score
    
    # cost of missing insurance (risk exposure)
    missing_health_cover = max(0, health_target - health_cover)
    
    # ── Dimension 3: Investment Diversification (max 20 points) ─────────
    
    has_equity = user_data.get('has_equity', False)
    has_debt = user_data.get('has_debt', False)
    has_gold = user_data.get('has_gold', False)
    only_fd = user_data.get('only_fd', True)
    monthly_sip = user_data.get('monthly_sip', 0)
    
    diversification_score = 0
    
    if only_fd:
        diversification_score = 4  # only FD is very undiversified
    else:
        if has_equity:
            diversification_score += 10
        if has_debt:
            diversification_score += 6
        if has_gold:
            diversification_score += 4
    
    # FD returns ~6.5%, liquid fund returns ~7.5%, equity returns ~12%
    # if they have 1 lakh in FD instead of balanced portfolio, they lose roughly:
    fd_corpus = liquid_savings if only_fd else 0
    fd_opportunity_cost = fd_corpus * (0.12 - 0.065)  # 5.5% difference per year
    
    # ── Dimension 4: Debt Health (max 15 points) ─────────────────────────
    
    monthly_emi = user_data.get('monthly_emi', 0)
    monthly_income = annual_income / 12
    
    # EMI-to-income ratio
    emi_ratio = monthly_emi / monthly_income if monthly_income > 0 else 0
    
    # below 30% = full score, above 50% = 0, linear between
    if emi_ratio <= 0.30:
        debt_score = 15
    elif emi_ratio >= 0.50:
        debt_score = 0
    else:
        # linear interpolation between 30% and 50%
        # at 30% → 15 points, at 50% → 0 points
        debt_score = 15 * (1 - (emi_ratio - 0.30) / 0.20)
    
    # ── Dimension 5: Tax Efficiency (max 15 points) ──────────────────────
    
    sec80c_used = user_data.get('sec80c_used', 0)
    has_nps = user_data.get('has_nps', False)
    has_hra = user_data.get('has_hra', False)
    
    # 80C limit is 1.5 lakh
    sec80c_limit = 150000
    sec80c_gap = max(0, sec80c_limit - sec80c_used)
    
    # tax rate depends on income bracket
    if annual_income <= 700000:
        tax_rate = 0.05
    elif annual_income <= 1000000:
        tax_rate = 0.10
    elif annual_income <= 1200000:
        tax_rate = 0.15
    elif annual_income <= 1500000:
        tax_rate = 0.20
    else:
        tax_rate = 0.30
    
    # tax saved if they use full 80C
    tax_saved_80c = sec80c_gap * tax_rate
    
    # NPS gives additional 50,000 deduction
    tax_saved_nps = 0 if has_nps else 50000 * tax_rate
    
    # score: 10 points for 80C, 5 points for NPS/HRA
    tax_score_80c = min(sec80c_used / sec80c_limit, 1.0) * 10
    tax_score_nps = 3 if has_nps else 0
    tax_score_hra = 2 if has_hra else 0
    tax_score = tax_score_80c + tax_score_nps + tax_score_hra
    
    # total missed tax savings
    missed_tax = tax_saved_80c + tax_saved_nps
    
    # ── Dimension 6: Retirement Readiness (max 10 points) ────────────────
    
    age = user_data.get('age', 35)
    current_corpus = user_data.get('current_corpus', 0)
    
    # how many years until retirement (assume 60)
    years_to_retire = max(1, 60 - age)
    
    # future value formula: FV = corpus*(1+r)^n + SIP*((1+r)^n - 1)/r
    r = 0.10 / 12  # 10% annual return, monthly
    n = years_to_retire * 12  # months
    
    corpus_fv = current_corpus * ((1 + r) ** n)
    
    sip_monthly = monthly_sip
    if sip_monthly > 0:
        sip_fv = sip_monthly * (((1 + r) ** n - 1) / r)
    else:
        sip_fv = 0
    
    projected_corpus = corpus_fv + sip_fv
    
    # FIRE number = 25 times annual expenses (standard retirement planning rule)
    annual_expense = monthly_expense * 12
    fire_number = 25 * annual_expense
    
    retirement_ratio = projected_corpus / fire_number if fire_number > 0 else 0
    retirement_score = min(retirement_ratio, 1.0) * 10
    
    # ── Totals ────────────────────────────────────────────────────────────
    
    total_score = (
        emergency_score +
        insurance_score +
        diversification_score +
        debt_score +
        tax_score +
        retirement_score
    )
    
    # total money being lost/missed per year
    missed_money = missed_tax + fd_opportunity_cost
    
    # ── Build action list (most important first) ──────────────────────────
    
    actions = []
    
    if emergency_gap > 0:
        months_needed = emergency_gap / monthly_expense if monthly_expense > 0 else 0
        actions.append({
            'priority': 1,
            'title': f'Build emergency fund',
            'detail': f'You have {months_covered:.1f} months saved. Target is 6 months. Need ₹{emergency_gap:,.0f} more.',
            'amount': emergency_gap,
            'timeline': 'Next 6 months'
        })
    
    if missed_tax > 0:
        actions.append({
            'priority': 2,
            'title': f'Save ₹{missed_tax:,.0f} in tax',
            'detail': f'You have used ₹{sec80c_used:,.0f} of ₹1,50,000 80C limit. Invest ₹{sec80c_gap:,.0f} more in ELSS or PPF to save ₹{tax_saved_80c:,.0f} in tax.',
            'amount': tax_saved_80c,
            'timeline': 'Before 31st March'
        })
    
    if health_cover < health_target:
        actions.append({
            'priority': 3,
            'title': 'Get health insurance',
            'detail': f'You have ₹{health_cover:,.0f} cover. Target is ₹{health_target:,.0f} for your family. One hospitalisation could cost ₹2–5 lakh.',
            'amount': 0,
            'timeline': 'This week'
        })
    
    if only_fd and liquid_savings > 50000:
        actions.append({
            'priority': 4,
            'title': f'Move FD to liquid fund — earn ₹{fd_opportunity_cost:,.0f} more/year',
            'detail': f'FD earns ~6.5%. Liquid funds earn ~7.5%. On ₹{liquid_savings:,.0f}, difference is ₹{fd_opportunity_cost:,.0f} per year.',
            'amount': fd_opportunity_cost,
            'timeline': 'This month'
        })
    
    # sort by priority
    actions.sort(key=lambda x: x['priority'])
    
    return {
        'score': round(total_score, 1),
        'max_score': 100,
        'breakdown': {
            'emergency_fund': round(emergency_score, 1),
            'insurance': round(insurance_score, 1),
            'investments': round(diversification_score, 1),
            'debt': round(debt_score, 1),
            'tax': round(tax_score, 1),
            'retirement': round(retirement_score, 1),
        },
        'missed_money': round(missed_money, 0),
        'missed_tax': round(missed_tax, 0),
        'actions': actions,
        'months_emergency': round(months_covered, 1),
        'fire_number': round(fire_number, 0),
        'projected_corpus': round(projected_corpus, 0),
        'tax_rate': tax_rate,
    }