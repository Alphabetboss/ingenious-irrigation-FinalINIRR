import os, glob
from collections import Counter

root = r"C:\Users\alpha\OneDrive\Desktop\IngeniousIrrigation\dataset_raw\dataset\Merged_Dataset"

# Show which split folders exist
for part in ("train","val","test"):
    for sub in ("images","labels"):
        p = os.path.join(root, sub, part)
        if os.path.isdir(p):
            print("OK:", p)

counts = Counter()
missing = 0

for part in ("train","val","test"):
    img_dir = os.path.join(root, "images", part)
    if not os.path.isdir(img_dir):
        continue
    for img in glob.glob(os.path.join(img_dir, "*.*")):
        base = os.path.splitext(os.path.basename(img))[0]
        lbl = os.path.join(root, "labels", part, base + ".txt")
        if not os.path.exists(lbl):
            missing += 1
            continue
        with open(lbl, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip().split()
                if not s: 
                    continue
                try:
                    cid = int(s[0])
                    counts[cid] += 1
                except Exception:
                    pass

print("Class IDs present and counts:", dict(counts))
print("Missing label files:", missing)
