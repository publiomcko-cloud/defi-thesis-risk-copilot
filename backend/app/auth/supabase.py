from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any

import httpx
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.hashes import SHA256

from app.core.config import Settings


class SupabaseTokenError(ValueError):
    pass


@dataclass(frozen=True)
class SupabaseClaims:
    subject: str
    email: str
    email_verified: bool
    issuer: str
    audience: str | list[str] | None
    expires_at: int
    raw: dict[str, Any]


_JWKS_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_JWKS_TTL_SECONDS = 300


def verify_supabase_jwt(token: str, settings: Settings) -> SupabaseClaims:
    header, payload, signature, signed_payload = _split_jwt(token)
    algorithm = header.get("alg")
    if algorithm != "RS256":
        raise SupabaseTokenError("Unsupported token algorithm")

    key_id = header.get("kid")
    if not key_id:
        raise SupabaseTokenError("Missing token key id")

    jwk = _get_jwk(key_id, settings)
    public_key = _rsa_public_key(jwk)
    try:
        public_key.verify(signature, signed_payload, PKCS1v15(), SHA256())
    except Exception as exc:  # pragma: no cover - cryptography detail varies
        raise SupabaseTokenError("Invalid token signature") from exc

    _validate_claims(payload, settings)
    subject = str(payload.get("sub") or "")
    email = _normalized_email(payload.get("email"))
    if not subject or not email:
        raise SupabaseTokenError("Missing token subject or email")

    return SupabaseClaims(
        subject=subject,
        email=email,
        email_verified=bool(
            payload.get("email_verified")
            or payload.get("email_confirmed_at")
            or payload.get("confirmed_at")
        ),
        issuer=str(payload.get("iss") or ""),
        audience=payload.get("aud"),
        expires_at=int(payload.get("exp")),
        raw=payload,
    )


def _split_jwt(token: str) -> tuple[dict[str, Any], dict[str, Any], bytes, bytes]:
    parts = token.split(".")
    if len(parts) != 3:
        raise SupabaseTokenError("Malformed token")
    try:
        header = json.loads(_b64decode(parts[0]))
        payload = json.loads(_b64decode(parts[1]))
        signature = _b64decode(parts[2])
    except Exception as exc:
        raise SupabaseTokenError("Malformed token") from exc
    return header, payload, signature, f"{parts[0]}.{parts[1]}".encode("ascii")


def _validate_claims(payload: dict[str, Any], settings: Settings) -> None:
    now = int(time.time())
    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at <= now:
        raise SupabaseTokenError("Token expired")
    if settings.supabase_jwt_issuer and payload.get("iss") != settings.supabase_jwt_issuer:
        raise SupabaseTokenError("Invalid token issuer")
    expected_audience = settings.supabase_jwt_audience
    if expected_audience:
        audience = payload.get("aud")
        if isinstance(audience, list):
            valid = expected_audience in audience
        else:
            valid = audience == expected_audience
        if not valid:
            raise SupabaseTokenError("Invalid token audience")


def _get_jwk(key_id: str, settings: Settings) -> dict[str, Any]:
    if not settings.supabase_jwks_url:
        raise SupabaseTokenError("Supabase JWKS URL is not configured")
    now = time.time()
    cached = _JWKS_CACHE.get(settings.supabase_jwks_url)
    if cached and cached[0] > now:
        jwks = cached[1]
    else:
        response = httpx.get(settings.supabase_jwks_url, timeout=5)
        response.raise_for_status()
        jwks = response.json()
        _JWKS_CACHE[settings.supabase_jwks_url] = (now + _JWKS_TTL_SECONDS, jwks)
    for key in jwks.get("keys", []):
        if key.get("kid") == key_id:
            return key
    _JWKS_CACHE.pop(settings.supabase_jwks_url, None)
    raise SupabaseTokenError("Token signing key not found")


def _rsa_public_key(jwk: dict[str, Any]) -> rsa.RSAPublicKey:
    if jwk.get("kty") != "RSA":
        raise SupabaseTokenError("Unsupported token key type")
    n = int.from_bytes(_b64decode(jwk["n"]), "big")
    e = int.from_bytes(_b64decode(jwk["e"]), "big")
    return rsa.RSAPublicNumbers(e=e, n=n).public_key()


def _b64decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _normalized_email(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower()
