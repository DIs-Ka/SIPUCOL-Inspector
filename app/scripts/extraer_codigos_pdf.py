import json
import re
from pathlib import Path

import fitz

PDF_PATH = Path("docs/catalogo-danos.pdf")
OUT_PATH = Path("src/data/codigosSIPUCOL.js")

AREA_MAP = {
    "1": "Durabilidad",
    "2": "Estabilidad",
    "3": "Seguridad vial",
    "4": "Daños relevantes",
}

CODIGO_VALIDO = re.compile(r"^(D\d|E\d|S\d|DR\d|D23-8)", re.IGNORECASE)


def limpiar_texto(texto):
    texto = texto.replace("\u00a0", " ")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def extraer_extracto_pagina(doc, pagina, codigo):
    try:
        texto = doc[pagina - 1].get_text("text")
    except Exception:
        return ""

    texto = limpiar_texto(texto)
    idx = texto.upper().find(codigo.upper())

    if idx == -1:
        return texto[:1400]

    return texto[idx:idx + 1600]


def main():
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"No existe el PDF: {PDF_PATH}")

    doc = fitz.open(PDF_PATH)

    # El índice está en las primeras páginas del documento.
    texto_indice = "\n".join(
        doc[i].get_text("text")
        for i in range(1, min(12, len(doc)))
    )

    texto_indice = texto_indice.replace("\u00a0", " ")

    partes = re.split(r"(?=\n\s*\d+\.\d+\s+)", "\n" + texto_indice)

    codigos = []

    for parte in partes:
        match_num = re.match(r"\n\s*(\d+\.\d+)\s+(.+)", parte, flags=re.S)

        if not match_num:
            continue

        numero = match_num.group(1).strip()
        cuerpo = limpiar_texto(match_num.group(2))

        match_pagina = re.search(r"(.+?)\s+(\d+)\s*$", cuerpo)

        if not match_pagina:
            continue

        cuerpo_sin_pagina = re.sub(r"\.{3,}", " ", match_pagina.group(1)).strip()
        pagina = int(match_pagina.group(2))

        tokens = cuerpo_sin_pagina.split()

        if not tokens:
            continue

        codigo = tokens[0].strip()
        nombre = " ".join(tokens[1:]).strip()

        if not CODIGO_VALIDO.match(codigo):
            continue

        area_principal = numero.split(".")[0]
        area = AREA_MAP.get(area_principal, "Sin área")

        extracto = extraer_extracto_pagina(doc, pagina, codigo)

        codigos.append({
            "id": f"{codigo}-{pagina}-{numero}",
            "numero": numero,
            "codigo": codigo,
            "nombre": nombre,
            "area": area,
            "pagina": pagina,
            "extracto": extracto,
            "severidades": {
                "0": "Insignificante / No presenta",
                "1": "Ligero",
                "2": "Leve",
                "3": "Fuerte",
                "4": "Severo",
                "5": "Extremo"
            }
        })

    codigos.sort(key=lambda item: (item["area"], item["pagina"], item["codigo"]))

    contenido = (
        "export const codigosSIPUCOL = "
        + json.dumps(codigos, ensure_ascii=False, indent=2)
        + "\n\n"
        + "export const areasCodigos = ['Todas', 'Durabilidad', 'Estabilidad', 'Seguridad vial', 'Daños relevantes']\n"
    )

    OUT_PATH.write_text(contenido, encoding="utf-8")

    print(f"Listo. Se generaron {len(codigos)} códigos en {OUT_PATH}")


if __name__ == "__main__":
    main()
