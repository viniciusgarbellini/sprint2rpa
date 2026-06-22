"""Extração dos dados da placa do motor a partir da imagem.

PIPELINE (imagem da placa → campos estruturados):

    imagem .png  ──►  _ocr_image()  ──►  texto bruto  ──►  parse_nameplate_text()
                       (imagem→texto)                       (texto→campos, regex)
                                                                   │
                                                                   ▼
                                                            NameplateData

DECISÃO DE ESCOPO (ver docs/pipeline-placa-cadastro.md):
  O enunciado pede DEFINIR o pipeline e AUTOMATIZAR o preenchimento do cadastro,
  não construir um motor de OCR de produção. Por isso a etapa imagem→texto é
  *simulada* e isolada numa única função (`_ocr_image`): ela abre a imagem de
  verdade e devolve o texto da placa (gravado nos metadados PNG na geração).

  A etapa texto→campos (`parse_nameplate_text`) é REAL: é exatamente o parser
  por regex que rodaria sobre a saída de um OCR de verdade, com toda a tolerância
  a ruído. Trocar para OCR real é mudar UMA função:

      # import pytesseract
      # from PIL import Image
      # texto = pytesseract.image_to_string(Image.open(path), lang="por")

  O restante do pipeline permanece idêntico.
"""

import re

from PIL import Image

from sprint2.models import NameplateData

# Fabricantes conhecidos (grafia oficial) — desambigua a linha do fabricante.
_KNOWN_MANUFACTURERS = [
    "WEG", "Atlas Copco", "Siemens", "ABB", "Toshiba",
    "General Electric", "Baldor", "Nidec",
]

# Chave usada nos metadados PNG para guardar o texto da placa (simulação do OCR).
NAMEPLATE_TEXT_KEY = "nameplate_ocr_text"


def _ocr_image(image_path: str) -> str:
    """Converte a imagem da placa em texto (etapa SIMULADA do pipeline).

    Abre a imagem de fato (validando que é uma imagem legível) e recupera o
    texto da placa. Numa placa gerada por `tools/gen_nameplates.py`, o texto fica
    embutido nos metadados PNG — emulando uma leitura de OCR perfeita.

    >>> Ponto único de troca para OCR real (pytesseract / easyocr). <<<
    """
    with Image.open(image_path) as img:
        img.load()  # força a leitura dos pixels (é uma imagem de verdade)
        # PIL expõe os metadados de texto do PNG em img.info / img.text.
        text = img.info.get(NAMEPLATE_TEXT_KEY)
        if text is None and hasattr(img, "text"):
            text = img.text.get(NAMEPLATE_TEXT_KEY)  # type: ignore[attr-defined]
    return text or ""


def _to_float(raw: str) -> float | None:
    """Converte número de placa em float, tolerando vírgula decimal."""
    if raw is None:
        return None
    cleaned = raw.strip().replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _search(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None


def parse_nameplate_text(text: str) -> NameplateData:
    """Extrai campos estruturados do texto da placa (parser REAL por regex).

    Tolerante a ruído típico de OCR: dois-pontos opcionais, espaços extras,
    unidades coladas ou separadas. Levanta ValueError se a TAG (campo-chave)
    não for reconhecida.
    """
    upper = text.upper()

    tag = _search(r"TAG[:\s]+([A-Z0-9][A-Z0-9\-_]+)", upper)
    if not tag:
        raise ValueError("TAG não reconhecida na placa")

    # Modelo: do rótulo até o fim da linha (um campo por linha na placa).
    model_raw = _search(r"MOD(?:ELO)?[:\s]+([A-Z0-9][^\n]*)", upper)
    model = model_raw.strip() if model_raw else None

    # Fabricante: tenta lista conhecida; senão, primeira linha não vazia.
    manufacturer: str | None = None
    for known in _KNOWN_MANUFACTURERS:
        if known.upper() in upper:
            manufacturer = known
            break
    if manufacturer is None:
        for line in text.splitlines():
            if line.strip():
                manufacturer = line.strip()
                break

    # Potência: prioriza kW; cai para cv/hp convertendo p/ kW (1 cv ≈ 0,7457 kW).
    power_kw = _to_float(_search(r"([\d.,]+)\s*KW", upper))
    if power_kw is None:
        cv = _to_float(_search(r"([\d.,]+)\s*(?:CV|HP)", upper))
        power_kw = round(cv * 0.7457, 2) if cv is not None else None

    voltage_v = _to_float(_search(r"([\d.,]+)\s*V(?:OLTS?)?\b", upper))
    current_a = _to_float(_search(r"([\d.,]+)\s*A\b", upper))
    rpm_val = _to_float(_search(r"([\d.,]+)\s*RPM", upper))
    rpm = int(rpm_val) if rpm_val is not None else None

    # Confiança = fração dos 6 campos técnicos efetivamente reconhecidos.
    fields = [manufacturer, model, power_kw, voltage_v, current_a, rpm]
    confidence = round(sum(f is not None for f in fields) / len(fields), 2)

    return NameplateData(
        tag=tag,
        name=None,
        manufacturer=manufacturer,
        model=model,
        rated_power_kw=power_kw,
        rated_voltage_v=voltage_v,
        rated_current_a=current_a,
        rated_rpm=rpm,
        ocr_confidence=confidence,
    )


def extract_nameplate(image_path: str) -> tuple[NameplateData, str]:
    """Executa o pipeline completo da imagem da placa.

    Retorna (dados estruturados validados, texto OCR bruto para rastreio).
    """
    ocr_text = _ocr_image(image_path)
    if not ocr_text.strip():
        raise ValueError(f"Nenhum texto extraído da placa: {image_path}")
    data = parse_nameplate_text(ocr_text)
    return data, ocr_text
