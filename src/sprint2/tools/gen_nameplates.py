"""Gera imagens de placa de motor (.png) para alimentar a RPA de placa.

Cada placa é uma imagem REAL, desenhada com os campos de uma placa de motor.
O mesmo texto é embutido nos metadados PNG (`tEXt`), de modo que a etapa de OCR
(`extractor._ocr_image`) consiga recuperá-lo — simulando uma leitura perfeita.
Trocar a etapa de OCR por pytesseract não exige regerar as imagens.

Uso:
    python -m sprint2.tools.gen_nameplates [pasta_destino]
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

from sprint2.config import settings
from sprint2.nameplate.extractor import NAMEPLATE_TEXT_KEY

# Especificação das placas de demonstração.
# MTR-001..004 são consistentes com o seed da Sprint 1; MTR-005 é NOVO
# (demonstra a RPA criando um cadastro inédito a partir da placa).
DEMO_MOTORS = [
    {"manufacturer": "WEG", "tag": "MTR-001", "model": "W22 IR3",
     "power_kw": 75, "voltage_v": 440, "current_a": 130, "rpm": 3550},
    {"manufacturer": "Atlas Copco", "tag": "MTR-002", "model": "GA-160",
     "power_kw": 160, "voltage_v": 440, "current_a": 280, "rpm": 1780},
    {"manufacturer": "Siemens", "tag": "MTR-003", "model": "SIMOTICS GP",
     "power_kw": 22, "voltage_v": 380, "current_a": 42, "rpm": 1750},
    {"manufacturer": "WEG", "tag": "MTR-004", "model": "W22 IR4",
     "power_kw": 45, "voltage_v": 440, "current_a": 80, "rpm": 1185},
    {"manufacturer": "ABB", "tag": "MTR-005", "model": "M3BP 200",
     "power_kw": 30, "voltage_v": 400, "current_a": 55, "rpm": 1470},
]


def build_nameplate_text(spec: dict) -> str:
    """Monta o bloco de texto da placa (um campo por linha)."""
    return "\n".join([
        f"{spec['manufacturer']} MOTORES",
        "MOTOR DE INDUCAO TRIFASICO",
        f"TAG: {spec['tag']}",
        f"MOD: {spec['model']}",
        f"POT: {spec['power_kw']} kW",
        f"TENSAO: {spec['voltage_v']} V",
        f"CORRENTE: {spec['current_a']} A",
        f"ROTACAO: {spec['rpm']} rpm",
        "ISOL: F   IP55   FS: 1.15",
    ])


def generate(spec: dict, out_dir: Path) -> Path:
    """Desenha a placa e embute o texto nos metadados PNG."""
    text = build_nameplate_text(spec)
    lines = text.splitlines()

    width, line_h, pad = 560, 30, 24
    height = pad * 2 + line_h * len(lines)
    img = Image.new("RGB", (width, height), (38, 50, 56))  # cinza-aço escuro
    draw = ImageDraw.Draw(img)
    draw.rectangle([6, 6, width - 7, height - 7], outline=(176, 190, 197), width=3)

    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 18)
    except OSError:
        font = ImageFont.load_default()

    for i, line in enumerate(lines):
        color = (255, 213, 79) if i == 0 else (236, 239, 241)
        draw.text((pad, pad + i * line_h), line, fill=color, font=font)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"placa_{spec['tag']}.png"

    meta = PngInfo()
    meta.add_text(NAMEPLATE_TEXT_KEY, text)
    img.save(out_path, "PNG", pnginfo=meta)
    return out_path


def generate_all(out_dir: Path | None = None) -> list[Path]:
    target = out_dir or Path(settings.nameplate_drop_folder)
    paths = [generate(spec, target) for spec in DEMO_MOTORS]
    print(f"{len(paths)} placa(s) gerada(s) em {target}")
    for p in paths:
        print(f"  - {p.name}")
    return paths


if __name__ == "__main__":
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    generate_all(dest)
