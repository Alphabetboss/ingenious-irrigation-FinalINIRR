"""
Helper CLI to manage Ollama from Python.

Examples:
  python scripts/Ollama.py --install
  python scripts/Ollama.py --pull phi3.5:3.8b-mini-instruct-q4_K_M
  python scripts/Ollama.py --run phi3.5:3.8b-mini-instruct-q4_K_M
"""

import argparse
import shutil
import subprocess
import sys


def run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    try:
        return subprocess.call(cmd)
    except FileNotFoundError:
        print("Command not found:", cmd[0])
        return 127


def ensure_ollama() -> bool:
    if shutil.which("ollama"):
        run(["ollama", "--version"]) 
        return True
    print("Ollama not found in PATH.")
    print("Install on Windows via winget:")
    print("  winget install --id=Ollama.Ollama -e")
    return False


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Ollama helper")
    p.add_argument("--install", action="store_true", help="Print install instructions and verify presence")
    p.add_argument("--pull", metavar="MODEL", help="Pull a model, e.g. phi3.5:3.8b-mini-instruct-q4_K_M")
    p.add_argument("--run", metavar="MODEL", help="Run a model interactively")
    args = p.parse_args(argv)

    if args.install:
        return 0 if ensure_ollama() else 1

    if args.pull:
        if not ensure_ollama():
            return 1
        return run(["ollama", "pull", args.pull])

    if args.run:
        if not ensure_ollama():
            return 1
        return run(["ollama", "run", args.run])

    # Default: helpful summary
    print("Small, good models for low-power PCs:")
    print("  ollama pull phi3.5:3.8b-mini-instruct-q4_K_M")
    print("  ollama pull qwen2.5:1.5b-instruct")
    print("Chat in terminal:")
    print("  ollama run phi3.5:3.8b-mini-instruct-q4_K_M")
    return 0


if __name__ == "__main__":
    sys.exit(main())
