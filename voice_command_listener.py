# scripts/voice_command_listener.py
import os, sys, time
from pathlib import Path
import numpy as np

print("[listener] starting up...")

# --- deps ---
try:
    import sounddevice as sd
    import librosa
    import joblib
    import requests
except Exception as e:
    print("[listener] import error:", repr(e))
    sys.exit(1)

MODEL_PATH = Path("models/voice_cmd.pkl")
if not MODEL_PATH.exists():
    print(f"[listener] model not found: {MODEL_PATH}. Run scripts/build_voice_model.py first.")
    sys.exit(1)

BASE = os.getenv("II_API_BASE", "http://127.0.0.1:5000")
API_KEY = os.getenv("II_API_KEY", "super-secret-123")
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

SAMPLE_RATE = 16000
SECONDS = 2.5
CHANNELS = 1
THRESHOLD = float(os.getenv("II_CONF", "0.50"))  # tweakable

def get_device():
    wanted = os.environ.get("II_INPUT_DEVICE", "").strip()
    if not wanted:
        print("[listener] II_INPUT_DEVICE not set -> using system default input device.")
        return None
    try:
        idx = int(wanted)
        print(f"[listener] using device index {idx}")
        return idx
    except ValueError:
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0 and wanted.lower() in d["name"].lower():
                print(f"[listener] using device name match [{i}]: {d['name']}")
                return i
        print(f"[listener] no device matched '{wanted}', falling back to default.")
        return None

def action_post(path, json=None, method="POST"):
    url = f"{BASE}{path}"
    try:
        r = requests.request(method, url, headers=HEADERS, json=json, timeout=5)
        print(f"[action] {method} {path} -> {r.status_code} {r.text}")
    except Exception as e:
        print(f"[action] request failed: {e}")

def action_start():  action_post("/api/irrigation/start")
def action_stop():   action_post("/api/irrigation/stop")
def action_status(): action_post("/api/irrigation/status", method="GET")
def action_skip():   action_post("/api/irrigation/skip")
def action_resume(): action_post("/api/irrigation/resume")
def action_set_zone1_10m(): action_post("/api/irrigation/zone/1/duration", json={"minutes": 10})

ACTIONS = {
    "start watering": action_start,
    "stop watering": action_stop,
    "status": action_status,
    "skip watering": action_skip,
    "resume schedule": action_resume,
    "set zone one ten minutes": action_set_zone1_10m,
}

def record_once(device):
    print("[listener] Recording... speak after the beep.")
    # soft beep (optional)
    try:
        import simpleaudio as sa
        sr_b = 44100
        t = np.linspace(0, 0.08, int(sr_b*0.08), False)
        tone = (0.25*np.sin(2*np.pi*880*t)).astype(np.float32)
        sa.play_buffer((tone*32767).astype(np.int16), 1, 2, sr_b)
    except Exception:
        pass

    try:
        audio = sd.rec(int(SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                       channels=CHANNELS, dtype='float32', device=device)
        sd.wait()
        y = audio.squeeze()
    except Exception as e:
        print("[listener] audio error:", e)
        return None
    # normalize lightly
    peak = float(np.abs(y).max() or 1.0)
    return (y / peak * 0.8).astype(np.float32)

def features(y: np.ndarray, sr: int, n_mfcc: int):
    if y.ndim > 1:
        y = y.mean(axis=1)
    if len(y) < sr * 3:
        y = librosa.util.fix_length(y, size=sr*3, mode="edge")
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    return np.concatenate([mfcc.mean(axis=1), mfcc.std(axis=1)], axis=0).reshape(1, -1)

def main():
    print(f"[listener] loading model from {MODEL_PATH} ...")
    obj = joblib.load(MODEL_PATH)
    clf, le, sr, n_mfcc = obj["clf"], obj["labels"], obj["sr"], obj["n_mfcc"]
    print("[listener] model loaded. labels:", list(le.classes_))
    print(f"[listener] API base: {BASE}; threshold: {THRESHOLD}")

    device = get_device()
    print("[listener] ready. Press Enter to capture each command. Ctrl+C to exit.\n")

    while True:
        try:
            input("Press Enter, then speak...")
        except EOFError:
            print("[listener] stdin closed; exiting.")
            break

        y = record_once(device)
        if y is None:
            continue

        x = features(y, sr, n_mfcc)
        probs = clf.predict_proba(x)[0]
        idx = int(np.argmax(probs))
        conf = float(probs[idx])
        phrase = le.inverse_transform([idx])[0]
        # show top-3 for transparency
        order = np.argsort(-probs)[:3]
        tops = [(le.inverse_transform([i])[0], float(probs[i])) for i in order]
        print("[listener] top3:", ", ".join(f"{p}:{c:.2f}" for p,c in tops))

        if conf >= THRESHOLD:
            print(f"[listener] DETECTED -> {phrase} ({conf:.2f})")
            action = ACTIONS.get(phrase)
            if action: action()
        else:
            print(f"[listener] below threshold ({conf:.2f}<{THRESHOLD:.2f}). Try again or collect more data.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[listener] bye!")
