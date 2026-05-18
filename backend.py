import os
from dotenv import load_dotenv
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from groq import Groq
from chatbot_routes import chatbot_bp
from analyzer_routes import analyzer_bp
from auth import auth_bp
from chat_routes import chat_bp, register_socket_events

# ─────────────────────────────────────────────
# FLASK SETUP
# ─────────────────────────────────────────────
app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "JWT_SECRET",
    "fallback_secret"
)

# FIXED CORS
from flask_cors import CORS

CORS(
    app,
    resources={r"/*": {"origins": [
        "http://localhost:5173",
        "https://front-end-medical-two.vercel.app"
    ]}},
    supports_credentials=True
)

# FIXED SOCKETIO
# Allow all origins for now (you can restrict later)
socketio = SocketIO(
    app,
    cors_allowed_origins=[
        "http://localhost:5173",
        "https://front-end-medical-two.vercel.app"
    ],
    async_mode="threading"
)


# ─────────────────────────────────────────────
# REGISTER BLUEPRINTS
# ─────────────────────────────────────────────
app.register_blueprint(analyzer_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(chatbot_bp)
# REGISTER SOCKET EVENTS
register_socket_events(socketio)


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "MediAI Backend Running"
    })
 


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok"
    })


# ─────────────────────────────────────────────
# SOCKET TEST ROUTE
# ─────────────────────────────────────────────
@app.route("/socket-test", methods=["GET"])
def socket_test():
    return jsonify({
        "socket": "working"
    })


# ─────────────────────────────────────────────
# RUN SERVER
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False,
        allow_unsafe_werkzueg=True
    )
print(sys.executable)    
