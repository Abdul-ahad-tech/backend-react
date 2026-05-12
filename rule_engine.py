# rule_engine.py — Clinical reference ranges & scoring
# Sources: WHO, AHA, ADA, KDIGO guidelines

REFERENCE = {
    # ── CBC ──────────────────────────────────────────────────────────────────
    "hemoglobin": {
        "display": "Hemoglobin", "unit": "g/dL", "category": "CBC",
        "description": "Oxygen-carrying protein in red blood cells",
        "low_risk": "Anemia, fatigue, weakness, shortness of breath",
        "high_risk": "Polycythemia, cardiovascular strain, blood clots",
        "male":   {"good": [13.5, 17.5], "moderate": [[11.0, 13.5], [17.5, 20.0]]},
        "female": {"good": [12.0, 15.5], "moderate": [[10.0, 12.0], [15.5, 18.0]]},
    },
    "wbc": {
        "display": "WBC (White Blood Cells)", "unit": "×10³/µL", "category": "CBC",
        "description": "Immune system cells that fight infection",
        "low_risk": "Increased infection risk, immune deficiency",
        "high_risk": "Active infection, inflammation, leukemia screening needed",
        "general": {"good": [4.5, 11.0], "moderate": [[3.0, 4.5], [11.0, 20.0]]},
    },
    "platelets": {
        "display": "Platelets", "unit": "×10³/µL", "category": "CBC",
        "description": "Cells responsible for blood clotting",
        "low_risk": "Bleeding risk, bruising, thrombocytopenia",
        "high_risk": "Clotting disorders, thrombocytosis",
        "general": {"good": [150, 400], "moderate": [[100, 150], [400, 600]]},
    },
    "rbc": {
        "display": "RBC (Red Blood Cells)", "unit": "×10⁶/µL", "category": "CBC",
        "description": "Cells that carry oxygen throughout the body",
        "low_risk": "Anemia, fatigue, pale skin",
        "high_risk": "Polycythemia, dehydration, cardiovascular risk",
        "male":   {"good": [4.5, 5.9], "moderate": [[3.5, 4.5], [5.9, 7.0]]},
        "female": {"good": [4.1, 5.1], "moderate": [[3.2, 4.1], [5.1, 6.5]]},
    },

    # ── METABOLIC ────────────────────────────────────────────────────────────
    "glucose": {
        "display": "Blood Glucose (Fasting)", "unit": "mg/dL", "category": "Metabolic",
        "description": "Blood sugar level measured after fasting",
        "low_risk": "Hypoglycemia, dizziness, fainting, confusion",
        "high_risk": "Pre-diabetes (100–125), Diabetes (≥126), organ damage risk",
        "general": {"good": [70, 99], "moderate": [[60, 70], [100, 125]]},
    },
    "hba1c": {
        "display": "HbA1c", "unit": "%", "category": "Metabolic",
        "description": "3-month average blood sugar level indicator",
        "low_risk": "Hypoglycemia risk if on medication",
        "high_risk": "Pre-diabetes (5.7–6.4%), Diabetes (≥6.5%) — organ damage risk",
        "general": {"good": [4.0, 5.6], "moderate": [[3.0, 4.0], [5.7, 6.4]]},
    },

    # ── KIDNEY ───────────────────────────────────────────────────────────────
    "creatinine": {
        "display": "Creatinine", "unit": "mg/dL", "category": "Kidney",
        "description": "Waste product filtered by kidneys — marker of kidney function",
        "low_risk": "Muscle loss, malnutrition, liver disease",
        "high_risk": "Kidney disease, impaired filtration, CKD risk",
        "male":   {"good": [0.74, 1.35], "moderate": [[0.5, 0.74], [1.35, 2.0]]},
        "female": {"good": [0.59, 1.04], "moderate": [[0.4, 0.59], [1.04, 1.8]]},
    },
    "bun": {
        "display": "BUN (Blood Urea Nitrogen)", "unit": "mg/dL", "category": "Kidney",
        "description": "Nitrogen in blood from protein breakdown",
        "low_risk": "Malnutrition, liver disease, overhydration",
        "high_risk": "Kidney dysfunction, dehydration, GI bleeding",
        "general": {"good": [7, 20], "moderate": [[3, 7], [20, 40]]},
    },

    # ── ELECTROLYTES ─────────────────────────────────────────────────────────
    "sodium": {
        "display": "Sodium", "unit": "mEq/L", "category": "Electrolytes",
        "description": "Electrolyte for fluid balance and nerve function",
        "low_risk": "Hyponatremia — nausea, headache, seizures",
        "high_risk": "Hypernatremia — dehydration, neurological issues",
        "general": {"good": [136, 145], "moderate": [[130, 136], [145, 150]]},
    },
    "potassium": {
        "display": "Potassium", "unit": "mEq/L", "category": "Electrolytes",
        "description": "Electrolyte vital for heart and muscle function",
        "low_risk": "Hypokalemia — muscle weakness, arrhythmia",
        "high_risk": "Hyperkalemia — cardiac arrest risk",
        "general": {"good": [3.5, 5.0], "moderate": [[3.0, 3.5], [5.0, 5.5]]},
    },

    # ── LIPIDS ───────────────────────────────────────────────────────────────
    "total_cholesterol": {
        "display": "Total Cholesterol", "unit": "mg/dL", "category": "Lipids",
        "description": "Total fat-like substance in blood",
        "low_risk": "Rarely a concern at low levels",
        "high_risk": "Cardiovascular disease, atherosclerosis, stroke risk",
        "general": {"good": [0, 200], "moderate": [None, [200, 239]]},
    },
    "ldl": {
        "display": "LDL Cholesterol", "unit": "mg/dL", "category": "Lipids",
        "description": "Bad cholesterol — builds up in artery walls",
        "low_risk": "Not typically a health concern",
        "high_risk": "Heart attack, stroke, arterial plaque buildup",
        "general": {"good": [0, 100], "moderate": [None, [100, 159]]},
    },
    "hdl": {
        "display": "HDL Cholesterol", "unit": "mg/dL", "category": "Lipids",
        "description": "Good cholesterol — removes bad cholesterol from blood",
        "low_risk": "Increased cardiovascular disease risk",
        "high_risk": "Rarely a concern at high levels",
        "male":   {"good": [40, 300], "moderate": [[20, 40], None]},
        "female": {"good": [50, 300], "moderate": [[25, 50], None]},
    },
    "triglycerides": {
        "display": "Triglycerides", "unit": "mg/dL", "category": "Lipids",
        "description": "Type of fat in the blood from excess calories",
        "low_risk": "Rarely a concern at low levels",
        "high_risk": "Pancreatitis, cardiovascular disease, metabolic syndrome",
        "general": {"good": [0, 150], "moderate": [None, [150, 199]]},
    },

    # ── LIVER ────────────────────────────────────────────────────────────────
    "alt": {
        "display": "ALT (Liver Enzyme)", "unit": "U/L", "category": "Liver",
        "description": "Enzyme released when liver cells are damaged",
        "low_risk": "Not typically a concern",
        "high_risk": "Liver damage, hepatitis, fatty liver disease",
        "male":   {"good": [7, 56], "moderate": [None, [56, 120]]},
        "female": {"good": [7, 45], "moderate": [None, [45, 100]]},
    },
    "ast": {
        "display": "AST (Liver Enzyme)", "unit": "U/L", "category": "Liver",
        "description": "Enzyme found in liver and heart muscle cells",
        "low_risk": "Not typically a concern",
        "high_risk": "Liver damage, heart disease, muscle disorders",
        "general": {"good": [10, 40], "moderate": [None, [40, 120]]},
    },

    # ── THYROID ──────────────────────────────────────────────────────────────
    "tsh": {
        "display": "TSH (Thyroid Stimulating Hormone)", "unit": "mIU/L", "category": "Thyroid",
        "description": "Hormone that controls thyroid gland activity",
        "low_risk": "Hyperthyroidism — rapid heartbeat, weight loss, anxiety",
        "high_risk": "Hypothyroidism — fatigue, weight gain, depression",
        "general": {"good": [0.4, 4.0], "moderate": [[0.1, 0.4], [4.0, 10.0]]},
    },

    # ── VITAMINS ─────────────────────────────────────────────────────────────
    "vitamin_d": {
        "display": "Vitamin D", "unit": "ng/mL", "category": "Vitamins",
        "description": "Fat-soluble vitamin essential for bone health and immunity",
        "low_risk": "Bone loss, immune deficiency, fatigue, depression",
        "high_risk": "Toxicity (rare) — nausea, weakness, kidney issues",
        "general": {"good": [30, 100], "moderate": [[20, 30], [100, 150]]},
    },
    "vitamin_b12": {
        "display": "Vitamin B12", "unit": "pg/mL", "category": "Vitamins",
        "description": "Vitamin critical for nerve function and red blood cell production",
        "low_risk": "Anemia, nerve damage, cognitive decline",
        "high_risk": "Rarely harmful — may indicate liver/blood disorder",
        "general": {"good": [200, 900], "moderate": [[150, 200], [900, 2000]]},
    },
    "iron": {
        "display": "Serum Iron", "unit": "µg/dL", "category": "Vitamins",
        "description": "Iron stored in blood for oxygen transport",
        "low_risk": "Iron-deficiency anemia, fatigue, poor concentration",
        "high_risk": "Hemochromatosis, organ damage",
        "male":   {"good": [60, 170], "moderate": [[30, 60], [170, 300]]},
        "female": {"good": [37, 145], "moderate": [[20, 37], [145, 300]]},
    },
}

CATEGORY_WEIGHTS = {
    "CBC": 1.2, "Metabolic": 1.3, "Kidney": 1.2,
    "Electrolytes": 1.1, "Lipids": 1.1, "Liver": 1.1,
    "Thyroid": 1.0, "Vitamins": 0.9,
}

def classify_value(test_key, value, gender="general"):
    """
    Returns dict with status, direction, severity_score (0–100), and messages.
    status: 'good' | 'moderate' | 'bad'
    direction: 'low' | 'high' | 'normal'
    """
    ref = REFERENCE.get(test_key)
    if not ref:
        return None

    # Pick ranges: prefer gender-specific, fallback to general
    ranges = ref.get(gender) or ref.get("general")
    if not ranges:
        return None

    good_range = ranges["good"]
    moderate_ranges = ranges.get("moderate", [None, None])
    mod_low  = moderate_ranges[0] if moderate_ranges and len(moderate_ranges) > 0 else None
    mod_high = moderate_ranges[1] if moderate_ranges and len(moderate_ranges) > 1 else None

    # ── Classify ──────────────────────────────────────────────────────────────
    direction = "normal"
    status = "bad"
    severity = 100  # starts bad, improves

    # Good range
    if good_range and good_range[0] <= value <= good_range[1]:
        status = "good"
        direction = "normal"
        # Perfect score: how centered in range (100 at midpoint, 80 at edges)
        mid = (good_range[0] + good_range[1]) / 2
        span = (good_range[1] - good_range[0]) / 2
        severity = 100 - 20 * (abs(value - mid) / span) if span > 0 else 100

    # Moderate low
    elif mod_low and mod_low[0] <= value <= mod_low[1]:
        status = "moderate"
        direction = "low"
        span = mod_low[1] - mod_low[0] if mod_low[1] != mod_low[0] else 1
        severity = 40 + 20 * ((value - mod_low[0]) / span)

    # Moderate high
    elif mod_high and mod_high[0] <= value <= mod_high[1]:
        status = "moderate"
        direction = "high"
        span = mod_high[1] - mod_high[0] if mod_high[1] != mod_high[0] else 1
        severity = 40 + 20 * (1 - (value - mod_high[0]) / span)

    # Bad — too low
    elif good_range and value < good_range[0]:
        status = "bad"
        direction = "low"
        threshold = mod_low[0] if mod_low else good_range[0] * 0.5
        severity = max(0, 30 * (value - threshold) / (good_range[0] - threshold)) if good_range[0] != threshold else 15

    # Bad — too high
    else:
        status = "bad"
        direction = "high"
        threshold = mod_high[1] if mod_high else good_range[1] * 2 if good_range else value * 1.5
        severity = max(0, 30 * (1 - (value - (mod_high[0] if mod_high else good_range[1])) / (threshold - (mod_high[0] if mod_high else good_range[1])))) if threshold != (mod_high[0] if mod_high else good_range[1] if good_range else value) else 15

    return {
        "status": status,
        "direction": direction,
        "severity_score": round(min(100, max(0, severity)), 1),
        "risk_note": ref["low_risk"] if direction == "low" else ref["high_risk"] if direction == "high" else "Values are within healthy range.",
        "description": ref["description"],
        "display": ref["display"],
        "unit": ref["unit"],
        "category": ref["category"],
        "good_range": good_range,
        "value": value,
    }


def calculate_overall_score(results):
    """Weighted health score 0–100 across all tested values."""
    if not results:
        return 0
    total_weight = 0
    weighted_sum = 0
    for r in results:
        cat = r.get("category", "General")
        w = CATEGORY_WEIGHTS.get(cat, 1.0)
        weighted_sum += r["severity_score"] * w
        total_weight += w
    return round(weighted_sum / total_weight, 1) if total_weight > 0 else 0


def get_health_grade(score):
    if score >= 85: return "Excellent", "#4ade80"
    if score >= 70: return "Good",      "#86efac"
    if score >= 55: return "Fair",      "#fbbf24"
    if score >= 40: return "Poor",      "#f97316"
    return "Critical", "#ef4444"


def get_category_scores(results):
    """Per-category breakdown scores."""
    cats = {}
    for r in results:
        cat = r["category"]
        cats.setdefault(cat, []).append(r["severity_score"])
    return {cat: round(sum(scores) / len(scores), 1) for cat, scores in cats.items()}
