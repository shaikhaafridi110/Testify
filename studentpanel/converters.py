"""
URL converter that hides the class id in student URLs.

    /student/8/exams/            ->  /student/mV0k3l9sQ2fXwA/exams/

The token is the class id XOR-masked with a key derived from SECRET_KEY plus a
short HMAC, so it is (a) not guessable/enumerable and (b) tamper-proof — a
changed or made-up token simply doesn't match any URL (404).

Views, middleware and templates keep working with the plain integer id:
    {% url 'studentpanel:exams' class_id=class_obj.id %}   -> encodes automatically
    def exams_list(request, class_id): ...                 -> receives the int 8

Note: this hides the id, it isn't access control. The session check in
StudentAuthMiddleware is still what protects the pages.
"""
import base64
import hashlib
import hmac

from django.conf import settings

_ID_BYTES = 4    # supports ids up to ~4.29 billion
_MAC_BYTES = 6


def _key(label: bytes) -> bytes:
    return hmac.new(settings.SECRET_KEY.encode(), label, hashlib.sha256).digest()


def _mac(plain: bytes) -> bytes:
    return hmac.new(_key(b"class-id-mac"), plain, hashlib.sha256).digest()[:_MAC_BYTES]


def _mask(mac: bytes) -> bytes:
    # mask depends on the MAC, so nearby ids give completely different tokens
    return hmac.new(_key(b"class-id-mask"), mac, hashlib.sha256).digest()[:_ID_BYTES]


def encode_class_id(class_id) -> str:
    plain = int(class_id).to_bytes(_ID_BYTES, "big")
    mac = _mac(plain)
    masked = bytes(a ^ b for a, b in zip(plain, _mask(mac)))
    return base64.urlsafe_b64encode(mac + masked).decode().rstrip("=")


def decode_class_id(token: str) -> int:
    """Return the class id, or raise ValueError if the token is invalid."""
    raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
    if len(raw) != _ID_BYTES + _MAC_BYTES:
        raise ValueError("bad token length")
    mac, masked = raw[:_MAC_BYTES], raw[_MAC_BYTES:]
    plain = bytes(a ^ b for a, b in zip(masked, _mask(mac)))
    if not hmac.compare_digest(mac, _mac(plain)):
        raise ValueError("bad token signature")
    return int.from_bytes(plain, "big")


class ClassTokenConverter:
    regex = r"[A-Za-z0-9_-]{14}"

    def to_python(self, value):
        return decode_class_id(value)   # ValueError => URL doesn't match (404)

    def to_url(self, value):
        return encode_class_id(value)