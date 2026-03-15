import base64
import json


def encode_share_link(config: dict) -> str:
    """
    Encode a quiz config dict into a URL-safe base64 string.
    Example: {"topic":"Python","difficulty":"easy",...} → "eyJ0b3BpY..."
    """
    raw = json.dumps(config, separators=(",", ":"))
    token = base64.urlsafe_b64encode(raw.encode()).decode()
    return token


def decode_share_link(token: str) -> dict:
    """
    Decode a base64 token back into a quiz config dict.
    Raises ValueError if the token is invalid.
    """
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        return json.loads(raw)
    except Exception:
        raise ValueError("Invalid share token")


def generate_share_url(config: dict, base_url: str) -> str:
    """
    Build a full shareable URL.
    Example: http://localhost:8000?quiz=eyJ0b3BpY...
    """
    token = encode_share_link(config)
    return f"{base_url}?quiz={token}"