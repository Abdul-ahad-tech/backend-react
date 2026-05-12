import os
from flask import Blueprint, request, jsonify
from groq import Groq
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# LOAD ENV FILE
# ─────────────────────────────────────────────
ENV_PATH = os.path.join(
    os.path.dirname(__file__),
    "key.env"
)

load_dotenv(ENV_PATH, override=True)

chatbot_bp = Blueprint("chatbot", __name__)

# ─────────────────────────────────────────────
# LOAD API KEY
# ─────────────────────────────────────────────
GROQ_KEY = os.getenv("GROQ_API_KEY")



if not GROQ_KEY:
    raise Exception("GROQ_API_KEY missing")

GROQ_KEY = GROQ_KEY.strip()

# ─────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────
client = Groq(
    api_key=GROQ_KEY
)

# ─────────────────────────────────────────────
# VITALS INTERPRETER
# ─────────────────────────────────────────────
def interpret_vitals(temp, bp):

    results = []

    # Temperature
    if temp not in [None, ""]:

        try:
            temp = float(temp)

            if temp >= 40:
                results.append(f"Temperature {temp}°C — HYPERPYREXIA")

            elif temp >= 39:
                results.append(f"Temperature {temp}°C — HIGH FEVER")

            elif temp >= 37.5:
                results.append(f"Temperature {temp}°C — LOW FEVER")

            elif temp < 35:
                results.append(f"Temperature {temp}°C — LOW BODY TEMPERATURE")

            else:
                results.append(f"Temperature {temp}°C — Normal")

        except Exception as e:
            print("TEMP ERROR:", e)

    # Blood Pressure
    if bp and "/" in str(bp):

        try:
            sys, dia = map(int, bp.split("/"))

            if sys >= 180 or dia >= 120:
                results.append(f"BP {bp} — HYPERTENSIVE CRISIS")

            elif sys >= 140 or dia >= 90:
                results.append(f"BP {bp} — HIGH BLOOD PRESSURE")

            elif sys < 90 or dia < 60:
                results.append(f"BP {bp} — LOW BLOOD PRESSURE")

            else:
                results.append(f"BP {bp} — Normal")

        except Exception as e:
            print("BP ERROR:", e)

    return "\n".join(results) if results else "No vitals provided."

# ─────────────────────────────────────────────
# TEST ROUTE
# ─────────────────────────────────────────────
@chatbot_bp.route("/test-groq", methods=["GET"])
def test_groq():

    try:

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": "Say hello"
                }
            ]
        )

        return jsonify({
            "success": True,
            "reply": response.choices[0].message.content
        })

    except Exception as e:

        print("GROQ TEST ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ─────────────────────────────────────────────
# CHAT ROUTE
# ─────────────────────────────────────────────
@chatbot_bp.route("/predict", methods=["POST"])
def predict():

    try:

        data = request.get_json()

        if not data:
            return jsonify({
                "error": "No data received"
            }), 400

        text = data.get("text", "").strip()
        temp = data.get("temp")
        bp = data.get("bp")

        if not text:
            return jsonify({
                "error": "Symptoms required"
            }), 400

        vitals = interpret_vitals(temp, bp)

        prompt = f"""
{vitals}

User message:
{text}

Respond naturally and appropriately based on the user's condition or message.
"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": """
You are MediAI, an intelligent and empathetic AI medical assistant.

Your behavior rules:

1. Respond naturally to normal conversation:
- greetings
- casual feelings
- stress
- anxiety
- loneliness
- emotional concerns
- mental health concerns

2. Give supportive and calm responses for emotional or mental health prompts.

3. If symptoms appear serious or dangerous such as:
- chest pain
- difficulty breathing
- stroke symptoms
- severe bleeding
- suicidal thoughts
- cancer concerns
- seizures
- unconsciousness
- severe allergic reactions

strongly recommend:
- immediate medical attention
- emergency services if needed
- signing in to consult real doctors on the platform

4. Never claim to be a real doctor.

5. Keep responses concise, caring, and simple.

6. If the user says they feel okay or good, respond conversationally instead of forcing medical analysis.
"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=700
        )

        ai_reply = response.choices[0].message.content

        return jsonify({
            "result": ai_reply
        })

    except Exception as e:

        print("\n========== CHATBOT ERROR ==========")
        print(str(e))
        print("===================================\n")

        # CLEAN ERROR FOR USER
        return jsonify({
            "error": "Could not connect to AI service."
        }), 500
    