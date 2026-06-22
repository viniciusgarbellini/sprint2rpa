"""Testes do pipeline de extração da placa (parser real, sem banco)."""

import pytest

from sprint2.nameplate.extractor import extract_nameplate, parse_nameplate_text
from sprint2.tools.gen_nameplates import build_nameplate_text, generate

SPEC = {
    "manufacturer": "WEG", "tag": "MTR-001", "model": "W22 IR3",
    "power_kw": 75, "voltage_v": 440, "current_a": 130, "rpm": 3550,
}


def test_parse_extrai_todos_os_campos():
    np = parse_nameplate_text(build_nameplate_text(SPEC))
    assert np.tag == "MTR-001"
    assert np.manufacturer == "WEG"
    assert np.model == "W22 IR3"
    assert np.rated_power_kw == 75
    assert np.rated_voltage_v == 440
    assert np.rated_current_a == 130
    assert np.rated_rpm == 3550
    assert np.ocr_confidence == 1.0


def test_parse_sem_tag_falha():
    with pytest.raises(ValueError):
        parse_nameplate_text("FABRICANTE QUALQUER\nPOT: 10 kW")


def test_parse_tolera_ruido_e_unidades_coladas():
    texto = "siemens\nTAG MTR-099\nMOD SIMOTICS GP\nPOT 22kW\nTENSAO 380V\nCORRENTE 42A\n3550 RPM"
    np = parse_nameplate_text(texto)
    assert np.tag == "MTR-099"
    assert np.manufacturer == "Siemens"
    assert np.rated_power_kw == 22
    assert np.rated_voltage_v == 380
    assert np.rated_current_a == 42
    assert np.rated_rpm == 3550


def test_parse_converte_cv_para_kw():
    np = parse_nameplate_text("TAG: MTR-CV\nPOT: 100 cv\nTENSAO: 440 V")
    # 100 cv * 0.7457 ≈ 74.57 kW
    assert np.rated_power_kw == pytest.approx(74.57, abs=0.01)


def test_confianca_parcial_quando_faltam_campos():
    np = parse_nameplate_text("WEG\nTAG: MTR-X\nPOT: 75 kW")
    assert 0 < np.ocr_confidence < 1


def test_roundtrip_gera_imagem_e_extrai(tmp_path):
    path = generate(SPEC, tmp_path)
    assert path.exists()
    np, ocr_text = extract_nameplate(str(path))
    assert np.tag == "MTR-001"
    assert "TAG: MTR-001" in ocr_text
    assert np.rated_power_kw == 75
