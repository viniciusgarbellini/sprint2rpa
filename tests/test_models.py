"""Testes dos modelos Pydantic da Sprint 2."""

import pytest
from pydantic import ValidationError

from sprint2.models import Area, AssetAssociation, NameplateData, Plant


def test_nameplate_tag_valida():
    np = NameplateData(tag="MTR-001")
    assert np.tag == "MTR-001"
    assert np.ocr_confidence == 0.0


def test_nameplate_tag_invalida():
    with pytest.raises(ValidationError):
        NameplateData(tag="mtr 001!")  # minúscula/espaço/símbolo


def test_nameplate_faixas():
    with pytest.raises(ValidationError):
        NameplateData(tag="MTR-001", rated_power_kw=-5)
    with pytest.raises(ValidationError):
        NameplateData(tag="MTR-001", ocr_confidence=1.5)


def test_plant_e_area():
    p = Plant(code="PLT-SP", name="Planta Sao Paulo", city="Sao Paulo")
    assert p.code == "PLT-SP"
    a = Area(plant_code="PLT-SP", code="A-BOMBAS", name="Bombeamento")
    assert a.code == "A-BOMBAS"


def test_associacao_valida():
    assoc = AssetAssociation(tag="MTR-001", plant_code="PLT-SP", area_code="A-BOMBAS")
    assert assoc.tag == "MTR-001"
    assert assoc.plant_name is None
