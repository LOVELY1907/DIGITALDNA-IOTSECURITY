# app.py
import os, time, base64
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from blockchain import Blockchain
from ai_detector import is_anomaly
from device_manager import register_device, update_telemetry, mark_compromised, is_quarantined, DEVICES, start_checker

APP_DIR = os.path.dirname(__file__)
FRAMES_DIR = os.path.join(APP_DIR, "frames")
os.makedirs(FRAMES_DIR, exist_ok=True)

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

blockchain = Blockchain()

# Broadcast to dashboard
def emit_update(node_id):
    data = DEVICES.get(node_id, {}).copy()
    data["node_id"] = node_id
    # attach frame URL
    data["frame_url"] = f"/frames/{node_id}.jpg"
    socketio.emit("node_update", {"node_id": node_id, "data": data})

# callback when heartbeat checker finds compromised
def on_compromised(node_id):
    blockchain.add_block(node_id, "COMPROMISED", telemetry=DEVICES[node_id].get("telemetry"), dna=DEVICES[node_id].get("dna"))
    emit_update(node_id)

# start checker
start_checker(on_compromised)

@app.route("/register", methods=["POST"])
def register():
    j = request.get_json(force=True)
    node_id = j.get("id") or j.get("device_id")
    dna = j.get("dna") or j.get("digital_dna") or j.get("dna_hex")
    if not node_id:
        return jsonify({"error":"missing id"}), 400
    register_device(node_id, dna)
    blockchain.add_block(node_id, "REGISTERED", dna=dna)
    emit_update(node_id)
    return jsonify({"registered": node_id}), 200

@app.route("/telemetry", methods=["POST"])
def telemetry():
    j = request.get_json(force=True)
    node_id = j.get("id") or j.get("device_id")
    if not node_id:
        return jsonify({"error":"missing id"}), 400

   

    telemetry = j.get("telemetry") or {
        "cpu": j.get("cpu"),
        "brightness": j.get("brightness"),
        "timestamp": j.get("timestamp", time.time())
    }

    prev = DEVICES.get(node_id, {}).get("telemetry")
    # check AI anomaly
    # --- FORCE COMPROMISE CHECK (Instant Detection) ---
    if telemetry.get("cpu", 0) > 85 or telemetry.get("brightness", 0) > 1.3:
        mark_compromised(node_id)
        blockchain.add_block(node_id, "FORCED_COMPROMISE", telemetry=telemetry, dna=DEVICES[node_id]["dna"])
        emit_update(node_id)
        return jsonify({"alert":"forced", "status":"COMPROMISED"}), 200
    # --- END INSTANT CHECK ---
    if is_anomaly(prev, telemetry):
        mark_compromised(node_id)
        blockchain.add_block(node_id, "ANOMALY_DETECTED", telemetry=telemetry, dna=DEVICES.get(node_id,{}).get("dna"))
        emit_update(node_id)
        return jsonify({"alert":"anomaly","status":"COMPROMISED"}), 200

    update_telemetry(node_id, telemetry)
    blockchain.add_block(node_id, "TELEMETRY", telemetry=telemetry, dna=DEVICES.get(node_id,{}).get("dna"))
    emit_update(node_id)
    return jsonify({"status":"OK"}), 200

@app.route("/frame", methods=["POST"])
def frame():
    # expects multipart form 'id' and file 'frame'
    node_id = request.form.get("id") or request.form.get("device_id")
    if not node_id:
        return jsonify({"error":"missing id"}), 400
    if is_quarantined(node_id):
        return jsonify({"blocked": True}), 200

    if "frame" in request.files:
        file = request.files["frame"]
        path = os.path.join(FRAMES_DIR, f"{node_id}.jpg")
        file.save(path)
        emit_update(node_id)
        return jsonify({"ok": True}), 200
    else:
        return jsonify({"error":"no frame"}), 400

@app.route("/frames/<node_id>.jpg")
def serve_frame(node_id):
    path = os.path.join(FRAMES_DIR, f"{node_id}.jpg")
    if os.path.exists(path):
        # send file
        return send_from_directory(FRAMES_DIR, f"{node_id}.jpg")
    return ("", 404)

@app.route("/devices", methods=["GET"])
def devices():
    # return all devices dict
    return jsonify(DEVICES)

@app.route("/chain", methods=["GET"])
def chain():
    # return blockchain for display
    from blockchain import CHAIN_FILE
    import json
    try:
        with open(CHAIN_FILE,"r") as f:
            return jsonify(json.load(f))
    except:
        return jsonify([])
    
@app.route("/quarantine", methods=["POST"])
def quarantine():
    j = request.get_json(force=True)
    node_id = j.get("id")

    if not node_id:
        return jsonify({"error": "missing id"}), 400

    # Mark in device manager
    mark_compromised(node_id)

    # Add quarantine flag
    DEVICES[node_id]["status"] = "COMPROMISED"
    DEVICES[node_id]["quarantined"] = True

    # Broadcast update to dashboard
    emit_update(node_id)

    return jsonify({"quarantined": node_id})
@app.route("/ai_query", methods=["POST"])
def ai_query():
    j = request.get_json(force=True)
    q = j.get("query", "").strip()

    # micro AI model simulation (local logic)
    if "compromised" in q.lower():
        bad = [n for n, d in DEVICES.items() if d.get("status") == "COMPROMISED"]
        if not bad:
            return jsonify({"response": "No nodes are compromised."})
        return jsonify({"response": f"Compromised nodes: {', '.join(bad)}"})

    if "status" in q.lower():
        out = []
        for k, v in DEVICES.items():
            out.append(f"{k}: {v.get('status','SAFE')}")
        return jsonify({"response": "\n".join(out)})

    if "dna" in q.lower():
        return jsonify({"response": f"Digital DNA:\n" + str({k: v.get('dna') for k,v in DEVICES.items()})})

    return jsonify({"response": "Ask about: status, compromised nodes, DNA, last activity."})
@app.route("/compromise", methods=["POST"])
def force_compromise():
    j = request.get_json(force=True)
    node_id = j.get("id")

    if not node_id:
        return jsonify({"error": "missing id"}), 400

    mark_compromised(node_id)
    blockchain.add_block(node_id, "FORCED_COMPROMISE")
    emit_update(node_id)

    return jsonify({"status": "COMPROMISED"}), 200

if __name__ == "__main__":
    print("Starting Flask+SocketIO on 0.0.0.0:5001")
    socketio.run(app, host="0.0.0.0", port=5001)
