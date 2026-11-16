"""Deterministic, standard-library-only source demonstration."""
import hashlib
import json


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def changed_files(before, after):
    return [name for name, body in after.items() if digest(before.get(name, "")) != digest(body)]


if __name__ == "__main__":
    previous = {"readme.txt": "version one", "settings.json": "{}"}
    current = {"readme.txt": "version two", "settings.json": "{}", "notes.txt": "new file"}
    result = changed_files(previous, current)
    assert result == ["readme.txt", "notes.txt"]
    print(json.dumps({"changed": result, "unchanged": ["settings.json"], "verified": True}, indent=2))

