import uuid
import jwt
import os
import json
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify
from flask_socketio import emit, join_room, leave_room
 
chat_bp = Blueprint("chat", __name__)
 
# ── In-memory store ───────────────────────────────────────────────────────────
DATA_FILE = "conversations.json"

try:
    with open(DATA_FILE, "r") as f:
        conversations = json.load(f)
except:
    conversations = {}
def save_conversations():
    with open(DATA_FILE, "w") as f:
        json.dump(conversations, f, indent=2)    
    
 
# ── Shared socketio reference (set by register_socket_events) ─────────────────
_socketio = None
 


# ── JWT helpers ───────────────────────────────────────────────────────────────
def get_current_user():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.split(" ")[1]
    try:
        secret = os.getenv("JWT_SECRET", "fallback_secret")
        return jwt.decode(token, secret, algorithms=["HS256"])
    except Exception:
        return None
 
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        return f(user, *args, **kwargs)
    return decorated
 
# ── Normalize message to what ChatPage.jsx expects ────────────────────────────
def normalize_msg(msg):
    return {
        "id":          msg.get("id"),
        "content":     msg.get("text", msg.get("content", "")),
        "sender_id":   msg.get("sender_id"),
        "sender_role": msg.get("role", msg.get("sender_role")),
        "sender_name": msg.get("sender_name", ""),
        "created_at":  msg.get("timestamp", msg.get("created_at", "")),
    }
 
# ─────────────────────────────────────────────────────────────────────────────
# PATIENT ROUTES
# ─────────────────────────────────────────────────────────────────────────────
 
@chat_bp.route("/api/chat/start", methods=["POST"])
@login_required
def start_conversation(user):
    """Patient starts a new conversation — emits socket event so doctors see it live."""
    if user.get("role") != "patient":
        return jsonify({"error": "Only patients can start conversations"}), 403
 
    conv_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    data = request.get_json(silent=True) or {}
    preview = data.get("preview", "")
 
    conversations[conv_id] = {
        "id":           conv_id,
        "patient_id":   user["id"],
        "patient_name": user.get("name", "Patient"),
        "doctor_id":    None,
        "doctor_name":  None,
        "status":       "pending",
        "created_at":   now,
        "updated_at":   now,
        "last_message": None,
        "preview":      preview,
        "messages":     [],
    }
 
    # Notify all doctors in real-time
    if _socketio:
        _socketio.emit("new_patient_request", {
            "conversation_id": conv_id,
            "patient_name":    user.get("name", "Patient"),
            "preview":         preview,
        }, room="doctors")
 
    return jsonify({"conversation_id": conv_id}), 201
 
 
# ── Frontend: GET /api/chat/messages/:conversationId ──────────────────────────
@chat_bp.route("/api/chat/messages/<conv_id>", methods=["GET"])
@login_required
def get_messages(user, conv_id):
    conv = conversations.get(conv_id)
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404
    uid = user["id"]
    if uid not in [conv["patient_id"], conv["doctor_id"]]:
        return jsonify({"error": "Access denied"}), 403
    return jsonify({"messages": [normalize_msg(m) for m in conv["messages"]]})
 
 
# ── Frontend: GET /api/chat/conversation/:conversationId ──────────────────────
@chat_bp.route("/api/chat/conversation/<conv_id>", methods=["GET"])
@login_required
def get_conversation(user, conv_id):
    conv = conversations.get(conv_id)
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404
    uid = user["id"]
    if uid not in [conv["patient_id"], conv["doctor_id"]]:
        return jsonify({"error": "Access denied"}), 403
    return jsonify({"conversation": conv})
 
save_conversations()
# ── Frontend: POST /api/chat/message/:conversationId ─────────────────────────
@chat_bp.route("/api/chat/message/<conv_id>", methods=["POST"])
@login_required
def send_message(user, conv_id):
    conv = conversations.get(conv_id)
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404
    uid = user["id"]
    if uid not in [conv["patient_id"], conv["doctor_id"]]:
        return jsonify({"error": "Access denied"}), 403
    if conv["status"] == "closed":
        return jsonify({"error": "Conversation is closed"}), 400
 
    data = request.get_json() or {}
    text = data.get("content", data.get("message", "")).strip()
    if not text:
        return jsonify({"error": "Message cannot be empty"}), 400
 
    msg = {
        "id":          str(uuid.uuid4()),
        "sender_id":   uid,
        "sender_name": user.get("name", "User"),
        "role":        user.get("role"),
        "text":        text,
        "timestamp":   datetime.utcnow().isoformat(),
    }
    conv["messages"].append(msg)
    conv["last_message"] = text
    conv["updated_at"] = msg["timestamp"]
    save_conversations()
    normalized = normalize_msg(msg)
 
    # Broadcast to everyone in the socket room
    if _socketio:
        _socketio.emit("new_message", normalized, room=conv_id)
 
    return jsonify({"message": normalized}), 201
 
 
# ── Frontend: POST /api/chat/close/:conversationId ───────────────────────────
@chat_bp.route("/api/chat/close/<conv_id>", methods=["POST"])
@login_required
def close_conversation(user, conv_id):
    conv = conversations.get(conv_id)
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404
    uid = user["id"]
    if uid not in [conv["patient_id"], conv["doctor_id"]]:
        return jsonify({"error": "Access denied"}), 403
    conv["status"] = "closed"
    conv["updated_at"] = datetime.utcnow().isoformat()
    save_conversations()
    if _socketio:
        _socketio.emit("conversation_closed", {}, room=conv_id)
    return jsonify({"message": "Conversation closed"})
 
 
# ─────────────────────────────────────────────────────────────────────────────
# DOCTOR ROUTES
# ─────────────────────────────────────────────────────────────────────────────
 
@chat_bp.route("/api/chat/pending", methods=["GET"])
@login_required
def get_pending(user):
    """All pending conversations waiting for a doctor."""
    if user.get("role") != "doctor":
        return jsonify({"error": "Doctors only"}), 403
    pending = [c for c in conversations.values() if c["status"] == "pending"]
    pending.sort(key=lambda x: x["created_at"])
    return jsonify({"conversations": pending})
 
@chat_bp.route("/api/chat/conversations", methods=["GET"])
@login_required
def get_all_conversations(user):

    # Patient conversations
    if user.get("role") == "patient":

        mine = [
            c for c in conversations.values()
            if c["patient_id"] == user["id"]
        ]

        mine.sort(
            key=lambda x: x.get("updated_at", ""),
            reverse=True
        )

        return jsonify({
            "conversations": mine
        })

    # Doctor conversations
    elif user.get("role") == "doctor":

        mine = [
            c for c in conversations.values()
            if c["doctor_id"] == user["id"]
        ]

        mine.sort(
            key=lambda x: x.get("updated_at", ""),
            reverse=True
        )

        return jsonify({
            "conversations": mine
        })

    return jsonify({
        "error": "Invalid role"
    }), 403 
@chat_bp.route("/api/chat/my-conversations", methods=["GET"])
@login_required
def my_conversations(user):

    # ── Doctor conversations ─────────────────────
    if user.get("role") == "doctor":

        mine = [
            c for c in conversations.values()
            if c["doctor_id"] == user["id"]
        ]

        mine.sort(
            key=lambda x: x.get("updated_at", ""),
            reverse=True
        )

        return jsonify({"conversations": mine})

    # ── Patient conversations ────────────────────
    elif user.get("role") == "patient":

        mine = [
            c for c in conversations.values()
            if c["patient_id"] == user["id"]
        ]

        mine.sort(
            key=lambda x: x.get("updated_at", ""),
            reverse=True
        )

        return jsonify({"conversations": mine})

    return jsonify({"error": "Invalid role"}), 403
    mine = [
        c for c in conversations.values()
        if c["doctor_id"] == user["id"] and c["status"] == "active"
    ]
    mine.sort(key=lambda x: x["updated_at"], reverse=True)
    return jsonify({"conversations": mine})
 
 
# ── DoctorDashboard calls POST /api/chat/claim/:id ───────────────────────────
@chat_bp.route("/api/chat/claim/<conv_id>", methods=["POST"])
@login_required
def claim_conversation(user, conv_id):
    """Doctor claims a pending conversation."""
    if user.get("role") != "doctor":
        return jsonify({"error": "Doctors only"}), 403
 
    conv = conversations.get(conv_id)
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404
    if conv["status"] != "pending":
        return jsonify({"error": "Already claimed by another doctor"}), 400
 
    conv["doctor_id"]   = user["id"]
    conv["doctor_name"] = user.get("name", "Doctor")
    conv["status"]      = "active"
    conv["updated_at"]  = datetime.utcnow().isoformat()
    save_conversations()
    if _socketio:
        # Remove from all doctors' pending lists
        _socketio.emit("conversation_claimed", {"conversation_id": conv_id}, room="doctors")
        # Tell the patient their doctor joined
        _socketio.emit("doctor_joined", {"doctor_name": conv["doctor_name"]}, room=conv_id)
 
    return jsonify({"message": "Conversation claimed", "conversation_id": conv_id})
 
 
# Keep /accept as alias
@chat_bp.route("/api/chat/<conv_id>/accept", methods=["POST"])
@login_required
def accept_conversation(user, conv_id):
    return claim_conversation(user, conv_id)
 
 
# ─────────────────────────────────────────────────────────────────────────────
# SOCKETIO EVENTS
# ─────────────────────────────────────────────────────────────────────────────
 
def register_socket_events(socketio):
    global _socketio
    _socketio = socketio  # store so REST routes can also emit
 
    @socketio.on("connect")
    def on_connect():
        print(f"[Socket] Connected: {request.sid}")
        emit("connected", {"status": "ok"})
 
    @socketio.on("disconnect")
    def on_disconnect():
        print(f"[Socket] Disconnected: {request.sid}")
 
    # Doctors call this on dashboard load so they receive new_patient_request events
    @socketio.on("join_as_doctor")
    def on_join_as_doctor(data):
        join_room("doctors")
        print(f"[Socket] Doctor {request.sid} joined doctors broadcast room")
 
    @socketio.on("join_conversation")
    def on_join(data):
        conv_id = data.get("conversation_id")
        if conv_id:
            join_room(conv_id)
            print(f"[Socket] {request.sid} joined room {conv_id}")
 
    @socketio.on("leave_conversation")
    def on_leave(data):
        conv_id = data.get("conversation_id")
        if conv_id:
            leave_room(conv_id)
 
    @socketio.on("close_conversation")
    def on_close_socket(data):
        conv_id = data.get("conversation_id")
        if conv_id:
            conv = conversations.get(conv_id)
            if conv:
                conv["status"] = "closed"
            emit("conversation_closed", {}, room=conv_id)
 
    @socketio.on("doctor_typing")
    def on_doctor_typing(data):
        conv_id = data.get("conversation_id")
        if conv_id:
            emit("typing", {"role": "doctor"}, room=conv_id, include_self=False)
 
    @socketio.on("patient_typing")
    def on_patient_typing(data):
        conv_id = data.get("conversation_id")
        if conv_id:
            emit("typing", {"role": "patient"}, room=conv_id, include_self=False)
            