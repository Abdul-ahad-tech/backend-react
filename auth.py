"""
auth.py  —  Medical.co  |  Supabase + Flask JWT Auth
Handles: Doctor signup, Patient signup, Login, Token refresh, Protected routes
"""
 
from flask import Blueprint, request, jsonify
from supabase import create_client, Client
from functools import wraps
from dotenv import load_dotenv
import jwt
import datetime
import os
import bcrypt
 
load_dotenv("key.env")
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
 
# ── Supabase client ────────────────────────────────────────────────────────────
SUPABASE_URL: str        = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "")
JWT_SECRET: str          = os.environ.get("JWT_SECRET", "change_this_secret")
 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
 
 
# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
 
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
 
 
def check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
 
 
def generate_token(user_id: str, role: str, email: str, name: str = "") -> str:
    payload = {
        "id":    user_id,
        "sub":   user_id,
        "role":  role,
        "email": email,
        "name":  name,
        "iat":   datetime.datetime.utcnow(),
        "exp":   datetime.datetime.utcnow() + datetime.timedelta(days=7),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
 
 
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        if not token:
            return jsonify({"error": "Token missing"}), 401
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, current_user=data, **kwargs)
    return decorated
 
 
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(*args, current_user=None, **kwargs):
            if current_user.get("role") not in roles:
                return jsonify({"error": "Access denied"}), 403
            return f(*args, current_user=current_user, **kwargs)
        return decorated
    return decorator
 
 
# ─────────────────────────────────────────────────────────────────────────────
# DOCTOR SIGNUP   POST /api/auth/doctor/signup
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/doctor/signup", methods=["POST"])
def doctor_signup():
    data = request.get_json(silent=True) or {}
 
    required = ["name", "email", "password", "age", "experience",
                "speciality", "university", "grad_year"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
 
    email = data["email"].strip().lower()
 
    # Check duplicate
    try:
        existing = supabase.table("doctors").select("id").eq("email", email).execute()
        if existing.data:
            return jsonify({"error": "Email already registered"}), 409
    except Exception as e:
        print("🔴 DUPLICATE CHECK ERROR:", str(e))
        return jsonify({"error": "Database error", "details": str(e)}), 500
 
    hashed_pw = hash_password(data["password"])
 
    insert_data = {
        "name":         data["name"].strip(),
        "email":        email,
        "password":     hashed_pw,
        "age":          int(data["age"]),
        "experience":   int(data["experience"]),
        "speciality":   data["speciality"].strip(),
        "university":   data["university"].strip(),
        "grad_year":    int(data["grad_year"]),
        "is_available": True,
        "is_verified":  False,
    }
 
    print("📝 Inserting doctor:", {k: v for k, v in insert_data.items() if k != "password"})
 
    try:
        result = supabase.table("doctors").insert(insert_data).execute()
        print("✅ Doctor insert result:", result.data)
    except Exception as e:
        print("🔴 DOCTOR INSERT ERROR:", str(e))
        return jsonify({"error": "Database error", "details": str(e)}), 500
 
    doctor = result.data[0]
    token = generate_token(doctor["id"], "doctor", email, doctor["name"])
 
    return jsonify({
        "message": "Doctor registered successfully",
        "token": token,
        "user": {
            "id":         doctor["id"],
            "name":       doctor["name"],
            "email":      doctor["email"],
            "role":       "doctor",
            "speciality": doctor["speciality"],
        }
    }), 201
 
 
# ─────────────────────────────────────────────────────────────────────────────
# PATIENT SIGNUP   POST /api/auth/patient/signup
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/patient/signup", methods=["POST"])
def patient_signup():
    data = request.get_json(silent=True) or {}
 
    required = ["name", "email", "password", "age", "gender"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
 
    email = data["email"].strip().lower()
 
    try:
        existing = supabase.table("patients").select("id").eq("email", email).execute()
        if existing.data:
            return jsonify({"error": "Email already registered"}), 409
    except Exception as e:
        print("🔴 PATIENT DUPLICATE CHECK ERROR:", str(e))
        return jsonify({"error": "Database error", "details": str(e)}), 500
 
    hashed_pw = hash_password(data["password"])
 
    insert_data = {
        "name":     data["name"].strip(),
        "email":    email,
        "password": hashed_pw,
        "age":      int(data["age"]),
        "gender":   data["gender"],
        "weight":   float(data["weight"]) if data.get("weight") else None,
        "height":   float(data["height"]) if data.get("height") else None,
        "diabetic": bool(data.get("diabetic", False)),
        "bp":       bool(data.get("bp", False)),
        "history":  data.get("history", "").strip(),
    }
 
    print("📝 Inserting patient:", {k: v for k, v in insert_data.items() if k != "password"})
 
    try:
        result = supabase.table("patients").insert(insert_data).execute()
        print("✅ Patient insert result:", result.data)
    except Exception as e:
        print("🔴 PATIENT INSERT ERROR:", str(e))
        return jsonify({"error": "Database error", "details": str(e)}), 500
 
    patient = result.data[0]
    token = generate_token(patient["id"], "patient", email, patient["name"])
 
    return jsonify({
        "message": "Patient registered successfully",
        "token": token,
        "user": {
            "id":    patient["id"],
            "name":  patient["name"],
            "email": patient["email"],
            "role":  "patient",
        }
    }), 201
 
 
# ─────────────────────────────────────────────────────────────────────────────
# LOGIN   POST /api/auth/login
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    data     = request.get_json(silent=True) or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role     = data.get("role") or ""
 
    if not all([email, password, role]):
        return jsonify({"error": "email, password, and role are required"}), 400
 
    if role not in ("doctor", "patient"):
        return jsonify({"error": "role must be 'doctor' or 'patient'"}), 400
 
    table = "doctors" if role == "doctor" else "patients"
 
    print(f"🔑 Login attempt: {email} as {role}")
 
    try:
        result = supabase.table(table).select("*").eq("email", email).execute()
    except Exception as e:
        print("🔴 LOGIN DB ERROR:", str(e))
        return jsonify({"error": "Database error", "details": str(e)}), 500
 
    if not result.data:
        return jsonify({"error": "Invalid email or password"}), 401
 
    user = result.data[0]
 
    if not check_password(password, user["password"]):
        return jsonify({"error": "Invalid email or password"}), 401
 
    token = generate_token(user["id"], role, email, user["name"])
 
    user_data = {
        "id":    user["id"],
        "name":  user["name"],
        "email": user["email"],
        "role":  role,
    }
    if role == "doctor":
        user_data["speciality"]   = user.get("speciality")
        user_data["is_available"] = user.get("is_available")
 
    print(f"✅ Login success: {email} as {role}")
 
    return jsonify({
        "message": "Login successful",
        "token":   token,
        "user":    user_data,
    }), 200
 
 
# ─────────────────────────────────────────────────────────────────────────────
# GET CURRENT USER   GET /api/auth/me
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@token_required
def me(current_user):
    role  = current_user["role"]
    uid   = current_user["sub"]
    table = "doctors" if role == "doctor" else "patients"
 
    try:
        result = supabase.table(table).select("*").eq("id", uid).execute()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
 
    if not result.data:
        return jsonify({"error": "User not found"}), 404
 
    user = result.data[0]
    user.pop("password", None)
    user["role"] = role
 
    return jsonify(user), 200
 
 
# ─────────────────────────────────────────────────────────────────────────────
# VERIFY TOKEN   GET /api/auth/verify
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/verify", methods=["GET"])
@token_required
def verify_token(current_user):
    return jsonify({"valid": True, "user": current_user}), 200