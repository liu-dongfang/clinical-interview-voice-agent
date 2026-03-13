from datetime import datetime

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO


app = Flask(__name__)
app.config["SECRET_KEY"] = "interruptible-voice-agent"
socketio = SocketIO(app, cors_allowed_origins="*")

EVENT_LIMIT = 200
timeline = []


def append_event(kind, payload):
    event = {
        "kind": kind,
        "payload": payload,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    timeline.append(event)
    del timeline[:-EVENT_LIMIT]
    socketio.emit("event", event)
    return event


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok", "events": len(timeline)})


@app.get("/events")
def get_events():
    return jsonify(timeline)


@app.post("/message")
def publish_message():
    data = request.get_json(force=True) or {}
    event = append_event(
        "message",
        {
            "role": data.get("role", "assistant"),
            "content": data.get("content", ""),
        },
    )
    return jsonify(event), 201


@app.post("/interrupt")
def publish_interrupt():
    data = request.get_json(force=True) or {}
    event = append_event(
        "interrupt",
        {
            "reason": data.get("reason", "manual"),
            "source": data.get("source", "api"),
        },
    )
    return jsonify(event), 201


@app.post("/backend-status")
def publish_backend_status():
    data = request.get_json(force=True) or {}
    event = append_event("backend-status", data)
    return jsonify(event), 201


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000)
