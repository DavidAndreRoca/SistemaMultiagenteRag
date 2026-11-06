"""Hash de contraseñas con Argon2id, tokens de sesión y protección CSRF.

* La contraseña nunca se guarda ni se registra: solo su hash Argon2id.
* El token de sesión viaja en una cookie ``HttpOnly``; en la base se guarda su SHA-256.
* El token CSRF es un HMAC del token de sesión con ``SECRETO_SESION`` (doble envío
  firmado): no necesita almacenamiento y no puede fabricarse sin el secreto.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()  # Argon2id con los parámetros recomendados por la biblioteca

# Hash de una contraseña aleatoria descartada: se verifica contra él cuando la cuenta
# no existe, para que el tiempo de respuesta no revele si la cuenta existe.
_HASH_SENUELO = _hasher.hash(secrets.token_urlsafe(32))


def hashear_contrasena(contrasena: str) -> str:
    return _hasher.hash(contrasena)


def verificar_contrasena(hash_guardado: str, contrasena: str) -> bool:
    try:
        return _hasher.verify(hash_guardado, contrasena)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verificar_contra_senuelo(contrasena: str) -> None:
    verificar_contrasena(_HASH_SENUELO, contrasena)


def generar_contrasena_inicial() -> str:
    """Contraseña aleatoria de 16 caracteres URL seguros (96 bits de entropía)."""
    return secrets.token_urlsafe(12)


def generar_token_sesion() -> str:
    return secrets.token_urlsafe(32)


def huella_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def token_csrf(secreto: str, token_sesion: str) -> str:
    return hmac.new(secreto.encode(), token_sesion.encode(), hashlib.sha256).hexdigest()


def csrf_valido(secreto: str, token_sesion: str, recibido: str | None) -> bool:
    if not recibido:
        return False
    return hmac.compare_digest(token_csrf(secreto, token_sesion), recibido)
