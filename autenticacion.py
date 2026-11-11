"""
autenticacion.py
================
Control de acceso del rol "Experto" para el panel de adquisición de
conocimiento.

Las credenciales nunca se guardan en texto plano. Se almacena un hash
PBKDF2-SHA256 con sal aleatoria, con el formato

    pbkdf2_sha256$<iteraciones>$<sal hex>$<hash hex>

Origen de las credenciales (el primero que exista):
  1. Variables de entorno HARDDIAG_EXPERTO_USUARIO y HARDDIAG_EXPERTO_HASH.
  2. El archivo ``config_experto.json`` junto a este módulo.

Cambiar el usuario o la contraseña (pide la contraseña sin mostrarla):

    py autenticacion.py --configurar
"""

from __future__ import annotations

import getpass
import hashlib
import hmac
import json
import os
import secrets
import sys

RUTA_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "config_experto.json")
ITERACIONES = 240_000
ROL_EXPERTO = "experto"


def generar_hash(contrasena: str, iteraciones: int = ITERACIONES) -> str:
    sal = secrets.token_bytes(16)
    derivado = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), sal, iteraciones)
    return f"pbkdf2_sha256${iteraciones}${sal.hex()}${derivado.hex()}"


def verificar_hash(contrasena: str, almacenado: str) -> bool:
    try:
        algoritmo, iteraciones, sal, esperado = almacenado.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        derivado = hashlib.pbkdf2_hmac(
            "sha256", contrasena.encode("utf-8"), bytes.fromhex(sal), int(iteraciones)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derivado.hex(), esperado)


def cargar_credenciales(ruta: str = RUTA_CONFIG) -> tuple[str, str] | None:
    """Devuelve (usuario, hash) o ``None`` si no hay credenciales configuradas."""
    usuario = os.environ.get("HARDDIAG_EXPERTO_USUARIO")
    hash_env = os.environ.get("HARDDIAG_EXPERTO_HASH")
    if usuario and hash_env:
        return usuario, hash_env
    try:
        with open(ruta, encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(datos, dict):
        return None
    usuario, hash_guardado = datos.get("usuario"), datos.get("hash")
    if isinstance(usuario, str) and isinstance(hash_guardado, str):
        return usuario, hash_guardado
    return None


def autenticar(usuario: str, contrasena: str, ruta: str = RUTA_CONFIG) -> str | None:
    """Devuelve el rol del usuario si las credenciales son correctas."""
    credenciales = cargar_credenciales(ruta)
    if credenciales is None:
        return None
    usuario_valido, hash_guardado = credenciales
    usuario_ok = hmac.compare_digest(usuario.strip().encode(), usuario_valido.encode())
    # El hash se verifica siempre, para que el tiempo de respuesta no revele
    # si el usuario existe.
    contrasena_ok = verificar_hash(contrasena, hash_guardado)
    return ROL_EXPERTO if usuario_ok and contrasena_ok else None


def configurar(ruta: str = RUTA_CONFIG) -> None:
    usuario = input("Usuario experto [experto]: ").strip() or "experto"
    contrasena = getpass.getpass("Nueva contraseña: ")
    if len(contrasena) < 8:
        sys.exit("La contraseña debe tener al menos 8 caracteres.")
    if contrasena != getpass.getpass("Repite la contraseña: "):
        sys.exit("Las contraseñas no coinciden.")
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump({"usuario": usuario, "rol": ROL_EXPERTO, "hash": generar_hash(contrasena)},
                  archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")
    print(f"Credenciales guardadas en {ruta}")


if __name__ == "__main__":
    if "--configurar" in sys.argv:
        configurar()
    else:
        print(__doc__)
