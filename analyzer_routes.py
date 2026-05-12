# analyzer_routes.py — Flask Blueprint for Medical Report Analyzer
# Register in backend.py:
#   from analyzer_routes import analyzer_bp
#   app.register_blueprint(analyzer_bp)

import re
import json
from flask import Blueprint, request, jsonify
from rule_engine import (
    REFERENCE, classify_value,
    calculate_overall_score, get_health_grade, get_category_scores
)

analyzer_bp = Blueprint("analyzer", __name__)

# ── PDF text extraction ────────────────────────────────────────────────────────
def extract_text_from_pdf(file_bytes):
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return "\n".join(page.get_text() for page in doc)
    except Exception as e:
        return ""


# ── Smart value parser from PDF text ─────────────────────────────────────────
# Maps common lab report synonyms to our internal keys
SYNONYM_MAP = {
    "haemoglobin": "hemoglobin", "hgb": "hemoglobin", "hb": "hemoglobin",
    "white blood cell": "wbc", "white blood cells": "wbc", "leukocytes": "wbc",
    "platelet": "platelets", "thrombocytes": "platelets", "plt": "platelets",
    "red blood cell": "rbc", "red blood cells": "rbc", "erythrocytes": "rbc",
    "fasting glucose": "glucose", "blood glucose": "glucose", "fbs": "glucose", "rbs": "glucose",
    "glycated hemoglobin": "hba1c", "glycosylated hemoglobin": "hba1c", "a1c": "hba1c",
    "serum creatinine": "creatinine",
    "blood urea nitrogen": "bun", "urea nitrogen": "bun",
    "serum sodium": "sodium", "na": "sodium",
    "serum potassium": "potassium", "k": "potassium",
    "cholesterol": "total_cholesterol", "total cholesterol": "total_cholesterol",
    "ldl cholesterol": "ldl", "low density lipoprotein": "ldl",
    "hdl cholesterol": "hdl", "high density lipoprotein": "hdl",
    "triglyceride": "triglycerides",
    "alanine aminotransferase": "alt", "sgpt": "alt",
    "aspartate aminotransferase": "ast", "sgot": "ast",
    "thyroid stimulating hormone": "tsh", "thyrotropin": "tsh",
    "25-hydroxyvitamin d": "vitamin_d", "vitamin d3": "vitamin_d", "vit d": "vitamin_d",
    "cobalamin": "vitamin_b12", "vit b12": "vitamin_b12",
    "serum iron": "iron", "fe": "iron",
}

def parse_lab_values_from_text(text):
    """
    Extract lab test values from raw PDF text using regex patterns.
    Handles formats like:
      Hemoglobin    14.5 g/dL
      Glucose: 105 mg/dL
      HbA1c = 6.2%
    """
    extracted = {}
    lines = text.lower().split("\n")

    # Number pattern — handles 0.74, 14.5, 105, 6.2
    num_pat = re.compile(r"(\d+\.?\d*)")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Try to match against all known synonyms
        matched_key = None
        for synonym, key in SYNONYM_MAP.items():
            if synonym in line:
                matched_key = key
                break

        if not matched_key:
            # Try direct key match
            for key in REFERENCE:
                if key.replace("_", " ") in line or key in line:
                    matched_key = key
                    break

        if matched_key and matched_key not in extracted:
            nums = num_pat.findall(line)
            if nums:
                # Take first numeric value that's plausibly a lab result
                for n in nums:
                    val = float(n)
                    # Skip suspiciously small/large reference range numbers printed on same line
                    if val > 0:
                        extracted[matched_key] = val
                        break

    return extracted


# ── Routes ────────────────────────────────────────────────────────────────────

@analyzer_bp.route("/api/analyzer/tests", methods=["GET"])
def get_available_tests():
    """Return list of all supported tests for the frontend form."""
    tests = []
    for key, ref in REFERENCE.items():
        tests.append({
            "key": key,
            "display": ref["display"],
            "unit": ref["unit"],
            "category": ref["category"],
            "description": ref["description"],
            "has_gender": "male" in ref,
        })
    return jsonify({"tests": tests})


@analyzer_bp.route("/api/analyzer/analyze", methods=["POST"])
def analyze_manual():
    """
    Analyze manually entered lab values.
    Body: { gender: 'male'|'female', values: { hemoglobin: 14.5, glucose: 105, ... } }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    gender = data.get("gender", "general").lower()
    values = data.get("values", {})

    if not values:
        return jsonify({"error": "No lab values provided"}), 400

    results = []
    for key, val in values.items():
        try:
            val = float(val)
        except (ValueError, TypeError):
            continue

        result = classify_value(key, val, gender)
        if result:
            results.append(result)

    if not results:
        return jsonify({"error": "No recognizable lab values found"}), 400

    overall_score = calculate_overall_score(results)
    grade, grade_color = get_health_grade(overall_score)
    category_scores = get_category_scores(results)

    # Summary flags
    bad_tests    = [r for r in results if r["status"] == "bad"]
    moderate_tests = [r for r in results if r["status"] == "moderate"]
    good_tests   = [r for r in results if r["status"] == "good"]

    return jsonify({
        "results": results,
        "overall_score": overall_score,
        "grade": grade,
        "grade_color": grade_color,
        "category_scores": category_scores,
        "summary": {
            "total": len(results),
            "good": len(good_tests),
            "moderate": len(moderate_tests),
            "bad": len(bad_tests),
            "critical_flags": [r["display"] for r in bad_tests],
        }
    })


@analyzer_bp.route("/api/analyzer/upload-pdf", methods=["POST"])
def analyze_pdf():
    """
    Accept a PDF upload, extract text, parse lab values, then analyze.
    Form fields: file (PDF), gender (optional)
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 400

    gender = request.form.get("gender", "general").lower()

    try:
        file_bytes = file.read()
    except Exception:
        return jsonify({"error": "Failed to read file"}), 500

    # Extract text
    text = extract_text_from_pdf(file_bytes)
    if not text.strip():
        return jsonify({
            "error": "Could not extract text from PDF. Try manual entry instead.",
            "parsed_values": {}
        }), 422

    # Parse lab values
    parsed_values = parse_lab_values_from_text(text)

    if not parsed_values:
        return jsonify({
            "error": "No recognizable lab values found in PDF. Please use manual entry.",
            "raw_text_preview": text[:500],
            "parsed_values": {}
        }), 422

    # Analyze parsed values
    results = []
    for key, val in parsed_values.items():
        result = classify_value(key, float(val), gender)
        if result:
            results.append(result)

    overall_score = calculate_overall_score(results)
    grade, grade_color = get_health_grade(overall_score)
    category_scores = get_category_scores(results)
    bad_tests    = [r for r in results if r["status"] == "bad"]
    moderate_tests = [r for r in results if r["status"] == "moderate"]

    return jsonify({
        "results": results,
        "overall_score": overall_score,
        "grade": grade,
        "grade_color": grade_color,
        "category_scores": category_scores,
        "parsed_values": parsed_values,
        "summary": {
            "total": len(results),
            "good": len([r for r in results if r["status"] == "good"]),
            "moderate": len(moderate_tests),
            "bad": len(bad_tests),
            "critical_flags": [r["display"] for r in bad_tests],
        }
    })


@analyzer_bp.route("/api/analyzer/reference", methods=["GET"])
def get_reference_ranges():
    """Return full reference range data for a specific test."""
    key = request.args.get("test")
    if not key or key not in REFERENCE:
        return jsonify({"error": "Unknown test key"}), 404
    return jsonify(REFERENCE[key])
