import requests

def local_chat(prompt: str, model="phi3.5:3.8b-mini-instruct-q4_K_M") -> str:
    r = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["response"]

if __name__ == "__main__":
    print(local_chat("You are a helpful sprinkler tech. Say hi briefly."))
