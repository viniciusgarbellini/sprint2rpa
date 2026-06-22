"""Autenticação simples com papéis para a interface operacional.

Implementação enxuta e sem dependências extras: usuários com senha em hash
SHA-256 (salgado) e dois papéis — `operador` (consulta) e `admin` (consulta +
disparo de RPA). Atende o requisito de "controle no acesso às informações".

Os usuários default existem para a demonstração. Em produção, sobrescreva via
a variável de ambiente AUTH_USERS ("usuario:role:sha256hex,...") e use um cofre
de segredos — nunca senha em código.

Credenciais de demonstração:
    operador / operador123   (papel: operador)
    admin    / admin123      (papel: admin)
"""

import hashlib

from sprint2.config import settings

# Salt de demonstração (fixo). Em produção: salt por usuário + cofre.
_SALT = "sprint2-rpa-cs"

# (papel, senha em texto) apenas para DERIVAR o hash default em tempo de import.
_DEFAULT_CREDENTIALS = {
    "operador": ("operador", "operador123"),
    "admin": ("admin", "admin123"),
}


def hash_password(password: str) -> str:
    return hashlib.sha256(f"{_SALT}:{password}".encode("utf-8")).hexdigest()


def _load_users() -> dict[str, tuple[str, str]]:
    """Retorna {username: (role, password_hash)}.

    Usa AUTH_USERS se definido; senão, os usuários default da demonstração.
    """
    raw = settings.auth_users.strip()
    if raw:
        users: dict[str, tuple[str, str]] = {}
        for entry in raw.split(","):
            parts = entry.split(":")
            if len(parts) == 3:
                username, role, pwd_hash = (p.strip() for p in parts)
                users[username] = (role, pwd_hash)
        if users:
            return users
    return {
        username: (role, hash_password(pwd))
        for username, (role, pwd) in _DEFAULT_CREDENTIALS.items()
    }


def authenticate(username: str, password: str) -> str | None:
    """Valida credenciais. Retorna o papel se OK, senão None."""
    users = _load_users()
    record = users.get((username or "").strip())
    if record is None:
        return None
    role, expected_hash = record
    if hash_password(password) == expected_hash:
        return role
    return None
