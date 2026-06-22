"""Modelos Pydantic da Sprint 2 — contratos de dados validados na fronteira.

Cobrem as entidades NOVAS desta sprint (planta, área, placa do motor e o
vínculo de localização). O cadastro do ativo (Asset) e as leituras continuam
governados pela Sprint 1.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

TAG_PATTERN = r"^[A-Z0-9\-_]+$"


class Plant(BaseModel):
    """Planta industrial — topo da hierarquia de navegação."""

    model_config = ConfigDict(str_strip_whitespace=True)

    code: str = Field(min_length=2, max_length=30, pattern=r"^[A-Z0-9\-_]+$")
    name: str = Field(min_length=2, max_length=200)
    city: str | None = None


class Area(BaseModel):
    """Área/setor dentro de uma planta."""

    model_config = ConfigDict(str_strip_whitespace=True)

    plant_code: str = Field(min_length=2, max_length=30)
    code: str = Field(min_length=2, max_length=30, pattern=r"^[A-Z0-9\-_]+$")
    name: str = Field(min_length=2, max_length=200)


class NameplateData(BaseModel):
    """Dados extraídos da placa do motor (resultado do pipeline imagem→cadastro).

    Todos os campos técnicos são opcionais: a placa real pode estar amassada,
    suja ou parcialmente ilegível — o parser preenche o que conseguir e a
    `ocr_confidence` reflete a fração de campos reconhecidos.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    tag: str = Field(min_length=3, max_length=50, pattern=TAG_PATTERN)
    name: str | None = Field(default=None, max_length=200)
    manufacturer: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    rated_power_kw: float | None = Field(default=None, ge=0, le=10_000)
    rated_voltage_v: float | None = Field(default=None, ge=0, le=100_000)
    rated_current_a: float | None = Field(default=None, ge=0, le=10_000)
    rated_rpm: int | None = Field(default=None, ge=0, le=100_000)
    ocr_confidence: float = Field(default=0.0, ge=0, le=1)


class AssetAssociation(BaseModel):
    """Linha do layout da planta: vincula uma TAG à sua localização."""

    model_config = ConfigDict(str_strip_whitespace=True)

    tag: str = Field(min_length=3, max_length=50, pattern=TAG_PATTERN)
    plant_code: str = Field(min_length=2, max_length=30)
    area_code: str = Field(min_length=2, max_length=30)
    plant_name: str | None = None
    area_name: str | None = None


class AccessEvent(BaseModel):
    """Evento de auditoria de acesso/consulta na interface."""

    username: str
    role: str
    action: str
    target: str | None = None
    at: datetime | None = None
