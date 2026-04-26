# ai_detector.py
# Simple rule-based anomaly detection
def is_anomaly(prev, current):
    if not current:
        return False

    cpu = current.get("cpu")
    bright = current.get("brightness")

    # ---- REALISTIC ANOMALY CHECK ----
    if cpu is not None and cpu > 90:
        return True  # abnormal CPU spike

    if bright is not None and (bright < 0 or bright > 1):
        return True  # impossible brightness

    return False