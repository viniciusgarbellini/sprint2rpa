"""Testes da autenticação com papéis (sem banco)."""

from sprint2.app.auth import authenticate, hash_password


def test_login_operador_ok():
    assert authenticate("operador", "operador123") == "operador"


def test_login_admin_ok():
    assert authenticate("admin", "admin123") == "admin"


def test_senha_errada_falha():
    assert authenticate("admin", "errada") is None


def test_usuario_inexistente_falha():
    assert authenticate("ninguem", "x") is None


def test_hash_e_deterministico_e_nao_reversivel():
    h = hash_password("segredo")
    assert h == hash_password("segredo")
    assert "segredo" not in h
    assert len(h) == 64  # sha256 hex
