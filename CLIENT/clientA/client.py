import requests, time, random, psutil

SERVER_URL = "http://127.0.0.1:5001"   # Change to your server IP later
DEVICE_IDS = ["clientA_1", "clientA_2"]  # two virtual devices on one laptop

def register_devices():
    for device in DEVICE_IDS:
        try:
            requests.post(f"{SERVER_URL}/register", json={"id": device})
            print(f"[+] Registered {device}")
        except Exception as e:
            print("Register error:", e)

def send_telemetry():
    while True:
        for device in DEVICE_IDS:
            data = {
                "id": device,
                "cpu": psutil.cpu_percent(),
                "ram": psutil.virtual_memory().percent,
                "temp": random.uniform(30, 80),
                "net": random.uniform(0, 10)
            }

            # Simulate attack: clientA_2 acts abnormal sometimes
            if device == "clientA_2" and random.random() > 0.8:
                data["temp"] = random.uniform(90, 120)

            try:
                r = requests.post(f"{SERVER_URL}/telemetry", json=data)
                print(device, "→", r.json()["status"])
            except Exception as e:
                print("Telemetry error:", e)

        time.sleep(3)

if __name__ == "__main__":
    register_devices()
    send_telemetry()
