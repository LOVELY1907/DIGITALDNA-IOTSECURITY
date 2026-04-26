# blockchain.py
import hashlib, json, time, os
CHAIN_FILE = os.path.join(os.path.dirname(__file__), "chain.json")

class Blockchain:
    def __init__(self):
        self.chain = []
        if os.path.exists(CHAIN_FILE):
            try:
                with open(CHAIN_FILE, "r") as f:
                    self.chain = json.load(f)
            except:
                self.create_genesis()
        else:
            self.create_genesis()

    def create_genesis(self):
        block = {
            "index": 0,
            "timestamp": time.time(),
            "device_id": "SYSTEM",
            "event": "GENESIS",
            "telemetry": None,
            "prev_hash": "0"
        }
        block["hash"] = self.hash(block)
        self.chain = [block]
        self._persist()

    def hash(self, block):
        b = dict(block)
        # remove hash if exists
        b.pop("hash", None)
        encoded = json.dumps(b, sort_keys=True).encode()
        return hashlib.sha256(encoded).hexdigest()

    def add_block(self, device_id, event, telemetry=None, dna=None):
        prev = self.chain[-1]
        block = {
            "index": len(self.chain),
            "timestamp": time.time(),
            "device_id": device_id,
            "event": event,
            "digital_dna": dna,
            "telemetry": telemetry,
            "prev_hash": prev["hash"]
        }
        block["hash"] = self.hash(block)
        self.chain.append(block)
        self._persist()
        return block

    def _persist(self):
        with open(CHAIN_FILE, "w") as f:
            json.dump(self.chain, f, indent=2)
