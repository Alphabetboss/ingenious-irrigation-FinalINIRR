# scripts/build_voice_model.py
import json, os
from pathlib import Path
import numpy as np
import soundfile as sf
import librosa
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

DATA_DIR = Path("data/voice")
MANIFEST = DATA_DIR / "manifest.jsonl"
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

SR = 16000
N_MFCC = 20

def featurize(path: str) -> np.ndarray:
    y, sr = sf.read(path, dtype='float32')
    if y.ndim > 1: y = y.mean(axis=1)
    if sr != SR:
        y = librosa.resample(y, orig_sr=sr, target_sr=SR)
    y = librosa.util.fix_length(y, size=SR*3, mode='edge')
    mfcc = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=N_MFCC)
    return np.concatenate([mfcc.mean(axis=1), mfcc.std(axis=1)], axis=0)

def load_data():
    X, y = [], []
    with open(MANIFEST, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            p = item["path"]
            phrase = item["phrase"].strip().lower()
            if os.path.exists(p):
                X.append(featurize(p))
                y.append(phrase)
    return np.array(X), np.array(y)

def main():
    X, y = load_data()
    if len(y) < 6:
        print("Not enough samples yet. Record more with voice_trainer.py.")
        return
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    Xtr, Xte, ytr, yte = train_test_split(X, y_enc, test_size=0.25, random_state=42, stratify=y_enc)
    clf = LogisticRegression(max_iter=2000)
    clf.fit(Xtr, ytr)
    yhat = clf.predict(Xte)
    print("\nValidation report:\n", classification_report(yte, yhat, target_names=le.classes_))
    joblib.dump({"clf": clf, "labels": le, "sr": SR, "n_mfcc": N_MFCC}, MODEL_DIR / "voice_cmd.pkl")
    print(f"\nSaved model -> {MODEL_DIR / 'voice_cmd.pkl'}")

if __name__ == "__main__":
    main()
