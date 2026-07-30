import json
import re
import shutil
from pathlib import Path

import fitz
from PIL import Image

PDF_PATH = Path("docs/catalogo-danos.pdf")
OUT_DATA = Path("src/data/codigosSIPUCOL.js")
OUT_IMG_DIR = Path("public/catalogo-pages")
OUT_PUBLIC_PDF = Path("public/manuals/catalogo-danos.pdf")

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


def compactar(texto):
    return re.sub(r"\s+", "", texto).upper()


def buscar_pagina_real(doc, numero, codigo, fallback):
    objetivo = compactar(numero + codigo)

    for i in range(12, len(doc)):
        texto = doc[i].get_text("text")
        if objetivo in compactar(texto[:2500]):
            return i + 1

    codigo_objetivo = codigo.upper()

    for i in range(12, len(doc)):
        texto = doc[i].get_text("text").upper()
        primeras_lineas = "\n".join(texto.splitlines()[:18])
        if codigo_objetivo in primeras_lineas:
            return i + 1

    return fallback


def extraer_extracto_pagina(doc, pagina, codigo):
    try:
        texto = doc[pagina - 1].get_text("text")
    except Exception:
        return ""

    texto = limpiar_texto(texto)
    idx = texto.upper().find(codigo.upper())

    if idx == -1:
        return texto[:1700]

    return texto[idx:idx + 1900]


def extraer_codigos_desde_indice(doc):
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
        cuerpo = re.sub(r"\.{3,}", " ", cuerpo)

        match_pagina = re.search(r"(.+?)\s+(\d+)\s*$", cuerpo)

        if not match_pagina:
            continue

        texto_codigo_nombre = match_pagina.group(1).strip()
        pagina_indice = int(match_pagina.group(2))

        tokens = texto_codigo_nombre.split()

        if not tokens:
            continue

        codigo = tokens[0].strip()
        nombre = " ".join(tokens[1:]).strip()

        if not CODIGO_VALIDO.match(codigo):
            continue

        area_principal = numero.split(".")[0]
        area = AREA_MAP.get(area_principal, "Sin área")

        pagina_real = buscar_pagina_real(doc, numero, codigo, pagina_indice)

        codigos.append({
            "id": f"{codigo}-{pagina_real}-{numero}",
            "numero": numero,
            "codigo": codigo,
            "nombre": nombre,
            "area": area,
            "pagina": pagina_real,
            "imagenPagina": f"/catalogo-pages/page-{pagina_real:03}.jpg",
            "extracto": extraer_extracto_pagina(doc, pagina_real, codigo),
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
    return codigos


def generar_imagenes_paginas(doc, paginas):
    OUT_IMG_DIR.mkdir(parents=True, exist_ok=True)

    for pagina in sorted(paginas):
        salida = OUT_IMG_DIR / f"page-{pagina:03}.jpg"

        if salida.exists():
            continue

        page = doc[pagina - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.35, 1.35), alpha=False)

        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        img.save(salida, "JPEG", quality=74, optimize=True)

        print(f"Imagen generada: {salida}")


def guardar_data(codigos):
    OUT_DATA.parent.mkdir(parents=True, exist_ok=True)

    contenido = (
        "export const codigosSIPUCOL = "
        + json.dumps(codigos, ensure_ascii=False, indent=2)
        + "\n\n"
        + "export const areasCodigos = ['Todas', 'Durabilidad', 'Estabilidad', 'Seguridad vial', 'Daños relevantes']\n"
    )

    OUT_DATA.write_text(contenido, encoding="utf-8")


def copiar_pdf_publico():
    OUT_PUBLIC_PDF.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PDF_PATH, OUT_PUBLIC_PDF)


def main():
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"No existe el PDF: {PDF_PATH}")

    doc = fitz.open(PDF_PATH)

    codigos = extraer_codigos_desde_indice(doc)
    paginas = {item["pagina"] for item in codigos}

    generar_imagenes_paginas(doc, paginas)
    guardar_data(codigos)
    copiar_pdf_publico()

    print("")
    print(f"Listo. Códigos generados: {len(codigos)}")
    print(f"Páginas visuales generadas/verificadas: {len(paginas)}")
    print(f"Data: {OUT_DATA}")
    print(f"PDF público: {OUT_PUBLIC_PDF}")


if __name__ == "__main__":
    main()
