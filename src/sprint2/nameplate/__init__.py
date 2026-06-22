"""Pipeline de extração da placa do motor → cadastro do ativo."""

from sprint2.nameplate.extractor import extract_nameplate, parse_nameplate_text

__all__ = ["extract_nameplate", "parse_nameplate_text"]
