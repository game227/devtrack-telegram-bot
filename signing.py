"""A small, dependency-free HMAC signing scheme for the DevTrack <-> bot
handshake — deliberately NOT Django's `django.core.signing` (this service
has no Django dependency), but the same shape: sign a payload with a shared
secret, verify it hasn't been tampered with or expired.

DevTrack backend signs a `user_id` into a /start token; this service verifies
it when the user presses Start in Telegram. Both sides implement this exact
scheme independently against the same TELEGRAM_LINK_SECRET.
"""

import base64
import hashlib
import hmac
import time


def sign_user_id(user_id, secret):
    payload = f"{user_id}:{int(time.time())}"
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    sig = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_token(token, secret, max_age=600):
    try:
        payload_b64, sig = token.split(".", 1)
    except ValueError:
        return None

    expected_sig = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, sig):
        return None

    try:
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = base64.urlsafe_b64decode(padded.encode()).decode()
        user_id_str, issued_at_str = payload.split(":", 1)
        user_id, issued_at = int(user_id_str), int(issued_at_str)
    except (ValueError, UnicodeDecodeError):
        return None

    if time.time() - issued_at > max_age:
        return None
    return user_id
