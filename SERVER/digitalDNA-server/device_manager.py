# device_manager.py
import time, threading
DEVICES = {}   # node_id -> {last_seen, status, telemetry, dna}
QUARANTINED = set()
HEARTBEAT_TIMEOUT = 1 # seconds; reduce for demo
CHECK_INTERVAL = 0.5

def register_device(node_id, dna):
    DEVICES.setdefault(node_id, {
        "last_seen": time.time(),
        "status": "SAFE",
        "telemetry": {},
        "dna": dna
    })
    DEVICES[node_id]["dna"] = dna
    DEVICES[node_id]["last_seen"] = time.time()
    DEVICES[node_id]["status"] = "SAFE"

def update_telemetry(node_id, telemetry):
    if node_id not in DEVICES:
        DEVICES[node_id] = {"last_seen": time.time(), "status": "SAFE", "telemetry": {}, "dna": None}
    DEVICES[node_id]["telemetry"] = telemetry
    DEVICES[node_id]["last_seen"] = time.time()
    if DEVICES[node_id]["status"] == "COMPROMISED":
        # if device resumes sending, mark SAFE again
        DEVICES[node_id]["status"] = "SAFE"
        if node_id in QUARANTINED:
            QUARANTINED.remove(node_id)

def mark_compromised(node_id):
    DEVICES.setdefault(node_id, {"last_seen": time.time(), "status": "SAFE", "telemetry": {}, "dna": None})
    DEVICES[node_id]["status"] = "COMPROMISED"
    QUARANTINED.add(node_id)

def is_quarantined(node_id):
    return node_id in QUARANTINED

def heartbeat_checker(on_compromised_callback):
    import time
    while True:
        now = time.time()
        for node_id, info in list(DEVICES.items()):
            if info.get("status") != "COMPROMISED" and (now - info.get("last_seen",0)) > HEARTBEAT_TIMEOUT:
                # mark compromised
                mark_compromised(node_id)
                on_compromised_callback(node_id)
        time.sleep(CHECK_INTERVAL)

def start_checker(on_compromised_callback):
    t = threading.Thread(target=heartbeat_checker, args=(on_compromised_callback,), daemon=True)
    t.start()
