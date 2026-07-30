import json
import re
import shutil
from pathlib import Path

import fitz
from PIL import Image

PDF_PATH = Path("docs/catalogo-danos.pdf")
OUT_DATA = Path("src/data/codigosSIPUCOL.js")
OUT_IMG_DIR = Path("public/catalogo-codigos")
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


def nombre_archivo_seguro(texto):
    return re.sub(r"[^A-Za-z0-9_-]+", "-", texto).strip("-")


def obtener_lineas_pagina(page):
    lineas = []

    data = page.get_text("dict")

    for block in data.get("blocks", []):
        for line in block.get("lines", []):
            textos = []

            for span in line.get("spans", []):
                textos.append(span.get("text", ""))

            texto = limpiar_texto(" ".join(textos))

            if not texto:
                continue

            bbox = line.get("bbox", None)

            if not bbox:
                continue

            lineas.append({
                "texto": texto,
                "compacto": compactar(texto),
                "bbox": bbox,
                "y": bbox[1]
            })

    return sorted(lineas, key=lambda item: item["y"])


def buscar_pagina_real(doc, numero, codigo, fallback):
    objetivo = compactar(numero + codigo)

    for i in range(12, len(doc)):
        texto = doc[i].get_text("text")
        if objetivo in compactar(texto[:3000]):
            return i + 1

    codigo_objetivo = compactar(codigo)

    for i in range(12, len(doc)):
        lineas = obtener_lineas_pagina(doc[i])
        primeras = lineas[:20]

        for linea in primeras:
            if codigo_objetivo in linea["compacto"]:
                return i + 1

    return fallback


def buscar_y_titulo(page, numero, codigo):
    lineas = obtener_lineas_pagina(page)

    objetivo_numero_codigo = compactar(numero + codigo)
    objetivo_codigo = compactar(codigo)

    # Mejor caso: la línea tiene numeral + código.
    for linea in lineas:
        if objetivo_numero_codigo in linea["compacto"]:
            return max(0, linea["y"] - 14)

    # Segundo caso: línea de título con el código.
    for linea in lineas:
        texto = linea["compacto"]

        if objetivo_codigo in texto and re.match(r"^\d+\.\d+", linea["texto"]):
            return max(0, linea["y"] - 14)

    # Tercer caso: cualquier aparición alta del código.
    candidatos = [
        linea for linea in lineas
        if objetivo_codigo in linea["compacto"]
    ]

    if candidatos:
        return max(0, candidatos[0]["y"] - 18)

    return 0


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
            "yInicio": buscar_y_titulo(doc[pagina_real - 1], numero, codigo),
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

    return codigos


def renderizar_recorte(page, top, bottom, scale=1.75):
    rect = page.rect

    top = max(0, top)
    bottom = min(rect.height, bottom)

    if bottom <= top + 40:
        bottom = rect.height

    clip = fitz.Rect(
        max(0, rect.x0 + 18),
        top,
        min(rect.width, rect.x1 - 18),
        bottom
    )

    pix = page.get_pixmap(
        matrix=fitz.Matrix(scale, scale),
        clip=clip,
        alpha=False
    )

    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def unir_vertical(imagenes):
    if len(imagenes) == 1:
        return imagenes[0]

    ancho = max(img.width for img in imagenes)
    alto = sum(img.height for img in imagenes) + (len(imagenes) - 1) * 16

    salida = Image.new("RGB", (ancho, alto), "white")

    y = 0

    for img in imagenes:
        x = (ancho - img.width) // 2
        salida.paste(img, (x, y))
        y += img.height + 16

    return salida


def generar_recortes_por_codigo(doc, codigos):
    OUT_IMG_DIR.mkdir(parents=True, exist_ok=True)

    for index, item in enumerate(codigos):
        pagina_inicio = item["pagina"]
        top_inicio = item["yInicio"]

        siguiente = codigos[index + 1] if index + 1 < len(codigos) else None

        if siguiente:
            pagina_fin = siguiente["pagina"]
            y_siguiente = siguiente["yInicio"]
        else:
            pagina_fin = pagina_inicio
            y_siguiente = doc[pagina_inicio - 1].rect.height

        imagenes = []

        if pagina_fin < pagina_inicio:
            pagina_fin = pagina_inicio

        for pagina in range(pagina_inicio, pagina_fin + 1):
            page = doc[pagina - 1]
            rect = page.rect

            if pagina == pagina_inicio:
                top = top_inicio
            else:
                top = 0

            if pagina == pagina_fin and pagina_fin == siguiente.get("pagina", None) if siguiente else False:
                bottom = max(top + 80, y_siguiente - 12)
            elif pagina == pagina_fin and siguiente and pagina_fin == siguiente["pagina"]:
                bottom = max(top + 80, y_siguiente - 12)
            else:
                bottom = rect.height - 24

            if pagina == pagina_inicio and siguiente and pagina_inicio == siguiente["pagina"]:
                bottom = max(top + 80, y_siguiente - 12)

            imagenes.append(renderizar_recorte(page, top, bottom))

        imagen_codigo = unir_vertical(imagenes)

        archivo = f"{nombre_archivo_seguro(item['codigo'])}-{nombre_archivo_seguro(item['numero'])}.jpg"
        salida = OUT_IMG_DIR / archivo

        imagen_codigo.save(salida, "JPEG", quality=82, optimize=True)

        item["imagenCodigo"] = f"/catalogo-codigos/{archivo}"
        item["imagenPagina"] = f"/catalogo-pages/page-{item['pagina']:03}.jpg"

        item.pop("yInicio", None)

        print(f"OK {item['codigo']} -> {salida}")


def generar_imagenes_paginas_base(doc, paginas):
    out_dir = Path("public/catalogo-pages")
    out_dir.mkdir(parents=True, exist_ok=True)

    for pagina in sorted(paginas):
        salida = out_dir / f"page-{pagina:03}.jpg"

        if salida.exists():
            continue

        page = doc[pagina - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.35, 1.35), alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        img.save(salida, "JPEG", quality=74, optimize=True)


def validar(codigos):
    errores = []

    for item in codigos:
        path = Path("public") / item["imagenCodigo"].lstrip("/")

        if not path.exists():
            errores.append(f"No existe imagen: {item['codigo']} {path}")

    ids = [item["id"] for item in codigos]

    if len(ids) != len(set(ids)):
        errores.append("Hay IDs repetidos.")

    if errores:
        print("")
        print("ERRORES:")
        for error in errores:
            print("-", error)
        raise SystemExit(1)

    print("")
    print("Validación OK:")
    print(f"- {len(codigos)} códigos")
    print("- Cada código tiene imagen individual")
    print("- Todas las imágenes existen")


def guardar_data(codigos):
    codigos_ordenados = sorted(
        codigos,
        key=lambda item: (
            ["Durabilidad", "Estabilidad", "Seguridad vial", "Daños relevantes"].index(item["area"])
            if item["area"] in ["Durabilidad", "Estabilidad", "Seguridad vial", "Daños relevantes"]
            else 99,
            item["pagina"],
            item["numero"]
        )
    )

    contenido = (
        "export const codigosSIPUCOL = "
        + json.dumps(codigos_ordenados, ensure_ascii=False, indent=2)
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

    generar_recortes_por_codigo(doc, codigos)
    generar_imagenes_paginas_base(doc, {item["pagina"] for item in codigos})

    validar(codigos)
    guardar_data(codigos)
    copiar_pdf_publico()

    print("")
    print("LISTO")
    print(f"Códigos procesados: {len(codigos)}")
    print(f"Data actualizada: {OUT_DATA}")
    print(f"Recortes: {OUT_IMG_DIR}")


if __name__ == "__main__":
    main()
