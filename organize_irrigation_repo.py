import os
import shutil
from pathlib import Path

# --- CONFIG ---

# Root of your repo ('.' means "where this script lives")
REPO_ROOT = Path(__file__).resolve().parent

# Turn this to False to actually move files
DRY_RUN = True

# Folder mapping inside src/
SRC_ROOT = REPO_ROOT / "src"
STRUCTURE = {
    "core": ["controller", "control", "scheduler", "schedule", "engine", "logic", "irrigation"],
    "sensors": ["sensor", "moisture", "humidity", "weather", "forecast", "env", "telemetry"],
    "actuators": ["valve", "pump", "relay", "actuator", "zone_switch"],
    "ui": ["ui", "dashboard", "flask", "fastapi", "api", "astra", "nova"],
    "utils": ["util", "helper", "common", "config", "logging", "tools"],
}

# Non-src top-level folders
TOP_LEVEL_FOLDERS = [
    "configs",
    "scripts",
    "tests",
    "data",
]

SCRIPT_KEYWORDS = ["migrate", "bootstrap", "oneoff", "maintenance", "demo"]


def ensure_base_structure():
    """Create the base folder structure if it doesn't exist."""
    # src subfolders
    for sub in STRUCTURE.keys():
        target = SRC_ROOT / sub
        if not target.exists():
            print(f"[CREATE] {target}")
            if not DRY_RUN:
                target.mkdir(parents=True, exist_ok=True)

            init_file = target / "__init__.py"
            if not init_file.exists():
                print(f"[CREATE] {init_file}")
                if not DRY_RUN:
                    init_file.touch()

    # src/__init__.py
    if not SRC_ROOT.exists():
        print(f"[CREATE] {SRC_ROOT}")
        if not DRY_RUN:
            SRC_ROOT.mkdir(parents=True, exist_ok=True)
    init_file = SRC_ROOT / "__init__.py"
    if not init_file.exists():
        print(f"[CREATE] {init_file}")
        if not DRY_RUN:
            init_file.touch()

    # top-level folders
    for folder in TOP_LEVEL_FOLDERS:
        target = REPO_ROOT / folder
        if not target.exists():
            print(f"[CREATE] {target}")
            if not DRY_RUN:
                target.mkdir(parents=True, exist_ok=True)


def classify_py_file(path: Path) -> Path | None:
    """
    Decide where a .py file should go.
    Returns the target path (directory) or None to leave it alone.
    """
    name = path.name.lower()

    # Skip this organizer script itself
    if name == "organize_irrigation_repo.py":
        return None

    # Scripts (one-off helpers)
    if any(kw in name for kw in SCRIPT_KEYWORDS):
        return REPO_ROOT / "scripts"

    # src subfolders by keyword
    for subfolder, keywords in STRUCTURE.items():
        if any(kw in name for kw in keywords):
            return SRC_ROOT / subfolder

    # If you want unmatched files to go into core, uncomment:
    # return SRC_ROOT / "core"

    # Otherwise, leave unmatched files where they are
    return None


def move_file(src: Path, dest_dir: Path):
    dest_dir = dest_dir.resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name

    if dest.exists():
        print(f"[SKIP] {src} -> {dest} (already exists)")
        return

    print(f"[MOVE] {src} -> {dest}")
    if not DRY_RUN:
        shutil.move(str(src), str(dest))


def scan_and_organize():
    ensure_base_structure()

    for root, dirs, files in os.walk(REPO_ROOT):
        root_path = Path(root)

        # Skip already-structured folders
        if root_path == SRC_ROOT:
            continue
        if root_path.is_relative_to(SRC_ROOT):
            continue
        if any(root_path.is_relative_to(REPO_ROOT / f) for f in TOP_LEVEL_FOLDERS):
            continue

        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = root_path / file
            target_dir = classify_py_file(file_path)
            if target_dir is None:
                continue

            move_file(file_path, target_dir)


if __name__ == "__main__":
    print(f"Repo root: {REPO_ROOT}")
    print(f"DRY_RUN = {DRY_RUN}")
    scan_and_organize()
    print("Done.")