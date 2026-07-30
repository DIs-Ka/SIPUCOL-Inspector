import argparse
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageOps


BASE_DIR = Path(__file__).resolve().parents[1]
MANUALS_DIR = BASE_DIR / "manuals"
OUTPUT_DIR = BASE_DIR / "outputs"

TEMPLATE = MANUALS_DIR / "04. FORMATO INSPECCION NIVEL 2 CON CALCULO DE IC SIN BLOQUEO (1).xlsm"

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_DRAWING = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"

NS = {
    "main": NS_MAIN,
    "rel": NS_REL,
    "pkg": NS_PKG_REL,
    "xdr": NS_DRAWING,
    "a": NS_A,
    "ct": NS_CT,
}

ET.register_namespace("", NS_MAIN)
ET.register_namespace("r", NS_REL)


SEVERIDAD_COLS = {
    "0": "G",
    "1": "H",
    "2": "I",
    "3": "J",
    "4": "K",
    "5": "L",
}

COL_FOTOS = "M"
COL_UBICACION = "O"

EVAL_SLOTS = [
    {"titulo": 13, "desc_label": 37, "desc": 38, "cal_label": 40, "cal": 41},
    {"titulo": 43, "desc_label": 72, "desc": 73, "cal_label": 76, "cal": 77},
    {"titulo": 79, "desc_label": 108, "desc": 109, "cal_label": 110, "cal": 111},
    {"titulo": 113, "desc_label": 138, "desc": 139, "cal_label": 144, "cal": 145},
    {"titulo": 147, "desc_label": 172, "desc": 173, "cal_label": 179, "cal": 180},
    {"titulo": 181, "desc_label": 203, "desc": 204, "cal_label": 208, "cal": 209},
    {"titulo": 211, "desc_label": 232, "desc": 233, "cal_label": 238, "cal": 239},
    {"titulo": 241, "desc_label": 262, "desc": 263, "cal_label": 267, "cal": 268},
    {"titulo": 270, "desc_label": 291, "desc": 292, "cal_label": 297, "cal": 298},
    {"titulo": 300, "desc_label": 321, "desc": 322, "cal_label": 325, "cal": 326},
    {"titulo": 328, "desc_label": 350, "desc": 351, "cal_label": 357, "cal": 358},
]


def limpiar(valor):
    return str(valor or "").replace("\xa0", " ").strip()


def col_a_num(col):
    total = 0

    for char in col:
        total = total * 26 + ord(char.upper()) - 64

    return total


def separar_ref(ref):
    m = re.match(r"([A-Z]+)(\d+)", ref or "")

    if not m:
        return None, None

    return m.group(1), int(m.group(2))


def buscar_excel_modelo_evaluacion():
    posibles = list(MANUALS_DIR.glob("*CUEVA*MORGAN*.xlsm"))

    posibles = [
        p for p in posibles
        if "SIN BLOQUEO" not in p.name.upper()
        and not p.name.upper().startswith("PRUEBA")
    ]

    if not posibles:
        raise FileNotFoundError(
            "No encontré el Excel lleno de ejemplo en manuals. "
            "Pon ahí el archivo: FORMATO INSPECCION NIVEL 2 - CAL IC PTE CUEVA DE MORGAN.xlsm"
        )

    return posibles[0]


def leer_shared_strings(z):
    if "xl/sharedStrings.xml" not in z.namelist():
        return []

    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    strings = []

    for si in root.findall("main:si", NS):
        textos = []

        for t in si.iter(f"{{{NS_MAIN}}}t"):
            textos.append(t.text or "")

        strings.append("".join(textos))

    return strings


def leer_valor_celda(cell, shared):
    if cell is None:
        return ""

    tipo = cell.attrib.get("t")

    if tipo == "s":
        v = cell.find("main:v", NS)

        if v is None or v.text is None:
            return ""

        idx = int(v.text)

        if idx >= len(shared):
            return ""

        return limpiar(shared[idx])

    if tipo == "inlineStr":
        textos = []

        for t in cell.iter(f"{{{NS_MAIN}}}t"):
            textos.append(t.text or "")

        return limpiar("".join(textos))

    v = cell.find("main:v", NS)

    if v is not None and v.text is not None:
        return limpiar(v.text)

    return ""


def convertir_celda_a_inline(cell, valor):
    ref = cell.attrib.get("r")
    estilo = cell.attrib.get("s")

    cell.clear()
    cell.attrib["r"] = ref

    if estilo is not None:
        cell.attrib["s"] = estilo

    cell.attrib["t"] = "inlineStr"

    is_el = ET.SubElement(cell, f"{{{NS_MAIN}}}is")
    t_el = ET.SubElement(is_el, f"{{{NS_MAIN}}}t")
    t_el.text = str(valor or "")


def obtener_sheet_data(root):
    sheet_data = root.find("main:sheetData", NS)

    if sheet_data is None:
        sheet_data = ET.SubElement(root, f"{{{NS_MAIN}}}sheetData")

    return sheet_data


def obtener_o_crear_row(root, fila):
    sheet_data = obtener_sheet_data(root)

    for row in sheet_data.findall("main:row", NS):
        if int(row.attrib.get("r", "0")) == fila:
            return row

    row = ET.Element(f"{{{NS_MAIN}}}row", {"r": str(fila)})
    sheet_data.append(row)
    return row


def obtener_o_crear_cell(root, ref):
    col, fila = separar_ref(ref)

    if not col or fila is None:
        raise ValueError(f"Referencia inválida: {ref}")

    row = obtener_o_crear_row(root, fila)

    for cell in row.findall("main:c", NS):
        if cell.attrib.get("r") == ref:
            return cell

    cell = ET.Element(f"{{{NS_MAIN}}}c", {"r": ref})
    row.append(cell)
    return cell


def escribir_celda(root, ref, valor):
    cell = obtener_o_crear_cell(root, ref)
    convertir_celda_a_inline(cell, valor)


def convertir_todas_las_celdas_a_inline(root, shared):
    for cell in root.findall(".//main:c", NS):
        valor = leer_valor_celda(cell, shared)
        convertir_celda_a_inline(cell, valor)


def leer_mapa_hojas(z):
    workbook = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))

    rel_map = {
        rel.attrib["Id"]: "xl/" + rel.attrib["Target"].lstrip("/")
        for rel in rels
    }

    hojas = {}

    for sheet in workbook.find("main:sheets", NS):
        nombre = sheet.attrib["name"].strip()
        rel_id = sheet.attrib[f"{{{NS_REL}}}id"]
        hojas[nombre.lower()] = rel_map[rel_id]

    return hojas


def buscar_path_hoja_por_nombre(hojas, nombre):
    nombre = limpiar(nombre).lower()

    if nombre in hojas:
        return hojas[nombre]

    for hoja_nombre, path in hojas.items():
        if hoja_nombre.strip().lower() == nombre.strip().lower():
            return path

    return None


def fila_tiene_codigo(row, shared, codigo):
    codigo = codigo.upper().strip()

    for cell in row.findall("main:c", NS):
        ref = cell.attrib.get("r", "")
        col, _ = separar_ref(ref)

        if not col:
            continue

        if col_a_num(col) > col_a_num("F"):
            continue

        valor = leer_valor_celda(cell, shared).upper().strip()

        if valor == codigo:
            return True

    return False


def buscar_fila_codigo(root, shared, codigo, fila_sugerida=None):
    codigo = limpiar(codigo).upper()

    if fila_sugerida:
        try:
            fila_sugerida = int(fila_sugerida)

            for row in root.findall(".//main:row", NS):
                if int(row.attrib.get("r", "0")) == fila_sugerida:
                    if fila_tiene_codigo(row, shared, codigo):
                        return fila_sugerida
        except Exception:
            pass

    for row in root.findall(".//main:row", NS):
        fila = int(row.attrib.get("r", "0"))

        if fila_tiene_codigo(row, shared, codigo):
            return fila

    return None


def escribir_item_tabla(root, shared, item):
    codigo = limpiar(item.get("codigo"))

    if not codigo:
        return False

    fila = buscar_fila_codigo(root, shared, codigo, item.get("filaExcel"))

    if not fila:
        print(f"No encontré código en tabla: {codigo}")
        return False

    for col in SEVERIDAD_COLS.values():
        escribir_celda(root, f"{col}{fila}", "")

    severidad = limpiar(item.get("severidad"))

    if severidad in SEVERIDAD_COLS:
        escribir_celda(root, f"{SEVERIDAD_COLS[severidad]}{fila}", "x")

    fotos = limpiar(item.get("fotos"))
    ubicacion = limpiar(item.get("ubicacion"))

    if fotos:
        escribir_celda(root, f"{COL_FOTOS}{fila}", fotos)

    if ubicacion:
        escribir_celda(root, f"{COL_UBICACION}{fila}", ubicacion)

    return True




def texto_celda_por_ref(root, shared, ref):
    for cell in root.findall(".//main:c", NS):
        if cell.attrib.get("r") == ref:
            return leer_valor_celda(cell, shared)
    return ""


def buscar_celda_por_texto(root, shared, palabras):
    palabras = [limpiar(p).lower() for p in palabras if limpiar(p)]

    for cell in root.findall(".//main:c", NS):
        valor = limpiar(leer_valor_celda(cell, shared)).lower()

        if not valor:
            continue

        if all(p in valor for p in palabras):
            return cell.attrib.get("r")

    return None


def escribir_observacion_por_label(root, shared, palabras_label, texto):
    texto = limpiar(texto)

    if not texto:
        return False

    ref_label = buscar_celda_por_texto(root, shared, palabras_label)

    if not ref_label:
        return False

    col, fila = separar_ref(ref_label)

    if not col or fila is None:
        return False

    # Normalmente el área editable está debajo del título.
    destinos = [
        f"{col}{fila + 1}",
        f"{col}{fila + 2}",
        f"B{fila + 1}",
        f"B{fila + 2}",
        f"C{fila + 1}",
        f"C{fila + 2}",
    ]

    for destino in destinos:
        actual = limpiar(texto_celda_por_ref(root, shared, destino))

        if not actual or actual == "0":
            escribir_celda(root, destino, texto)
            return True

    escribir_celda(root, destinos[0], texto)
    return True


def escribir_observaciones_componente(root, shared, componente):
    levantamiento = (
        componente.get("observacionesLevantamiento")
        or componente.get("observacionLevantamiento")
        or componente.get("observaciones_levantamiento")
        or ""
    )

    revisor = (
        componente.get("observacionesRevisor")
        or componente.get("observacionRevisor")
        or componente.get("observaciones_revisor")
        or ""
    )

    ok1 = escribir_observacion_por_label(
        root,
        shared,
        ["observaciones", "levantamiento"],
        levantamiento,
    )

    ok2 = escribir_observacion_por_label(
        root,
        shared,
        ["observaciones", "revisor"],
        revisor,
    )

    return ok1 or ok2


def escribir_identificacion_en_tablas(root, identificacion):
    datos = {
        "C13": identificacion.get("nombrePuente", ""),
        "C15": identificacion.get("administradorVial", identificacion.get("administrador", "")),
        "C17": identificacion.get("entidadAdministradora", ""),
        "C19": identificacion.get("responsableDiligenciamiento", ""),
        "F19": identificacion.get("cargoDiligenciamiento", ""),
        "Q19": identificacion.get("tarjetaDiligenciamiento", ""),
        "C21": identificacion.get("responsableRevision", ""),
        "F21": identificacion.get("cargoRevision", ""),
        "Q21": identificacion.get("tarjetaRevision", ""),
    }

    for ref, valor in datos.items():
        if valor:
            escribir_celda(root, ref, valor)

    id_puente = limpiar(identificacion.get("idPuente", ""))

    if id_puente:
        solo = re.sub(r"[^A-Za-z0-9]", "", id_puente)

        celdas_id = ["G13", "H13", "J13", "K13", "L13", "M13", "N13", "O13", "P13", "Q13", "S13", "T13", "V13", "W13", "X13", "Y13"]

        for celda, char in zip(celdas_id, solo):
            escribir_celda(root, celda, char)


def preparar_imagen_compuesta(imagenes, salida):
    salida = Path(salida)

    canvas_w = 1280
    canvas_h = 720
    bg = Image.new("RGB", (canvas_w, canvas_h), "white")

    imagenes = [Path(p) for p in imagenes if p and Path(p).exists()]
    imagenes = imagenes[:4]

    if not imagenes:
        bg.save(salida, "JPEG", quality=90)
        return salida

    if len(imagenes) == 1:
        cajas = [(0, 0, canvas_w, canvas_h)]
    elif len(imagenes) == 2:
        cajas = [(0, 0, canvas_w // 2, canvas_h), (canvas_w // 2, 0, canvas_w, canvas_h)]
    else:
        cajas = [
            (0, 0, canvas_w // 2, canvas_h // 2),
            (canvas_w // 2, 0, canvas_w, canvas_h // 2),
            (0, canvas_h // 2, canvas_w // 2, canvas_h),
            (canvas_w // 2, canvas_h // 2, canvas_w, canvas_h),
        ]

    for img_path, box in zip(imagenes, cajas):
        with Image.open(img_path) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")

            box_w = box[2] - box[0]
            box_h = box[3] - box[1]

            im.thumbnail((box_w - 16, box_h - 16), Image.Resampling.LANCZOS)

            x = box[0] + (box_w - im.width) // 2
            y = box[1] + (box_h - im.height) // 2

            bg.paste(im, (x, y))

    bg.save(salida, "JPEG", quality=90, optimize=True)

    return salida


def extraer_imagenes_del_modelo(modelo):
    out = OUTPUT_DIR / "_imagenes_extraidas_modelo"
    out.mkdir(parents=True, exist_ok=True)

    rutas = []

    with zipfile.ZipFile(modelo, "r") as z:
        for nombre in z.namelist():
            if not nombre.startswith("xl/media/"):
                continue

            ext = Path(nombre).suffix.lower()

            if ext not in [".png", ".jpg", ".jpeg"]:
                continue

            destino = out / Path(nombre).name
            destino.write_bytes(z.read(nombre))
            rutas.append(str(destino))

    return rutas


def data_demo_cueva():
    modelo = buscar_excel_modelo_evaluacion()
    imgs = extraer_imagenes_del_modelo(modelo)

    def foto(i):
        if not imgs:
            return []
        return [imgs[i % len(imgs)]]

    return {
        "nombreArchivo": "SALIDA_FINAL_CON_IMAGENES_CUEVA_MORGAN.xlsm",
        "identificacion": {
            "nombrePuente": "PUENTE CUEVA DE MORGAN",
            "idPuente": "12-5607-00-0100",
            "administradorVial": "CONCESIÓN TRANSVERSAL DEL SISGA",
            "entidadAdministradora": "ANI",
            "responsableDiligenciamiento": "PEDELTA",
            "fecha": "05/04/2026",
            "carretera": "5607",
            "pr": "23 + 014",
            "inspector": "PEDELTA",
            "administrador": "CONCESIÓN TRANSVERSAL DEL SISGA"
        },
        "tablas": [
            {
                "nombre": "Superficie del tablero ",
                "items": [
                    {"codigo": "D1EP29", "severidad": "4", "fotos": "1", "ubicacion": "Superficie de rodadura; IMG_5708"},
                    {"codigo": "S1DI11", "severidad": "4", "fotos": "1", "ubicacion": "Superficie de rodadura: IMG_20260404_132216"}
                ]
            },
            {
                "nombre": "Superficie de accesos",
                "items": [
                    {"codigo": "E1DF5", "severidad": "3", "fotos": "2", "ubicacion": "AC1 y AC2: IMG_5700, IMG_5706"},
                    {"codigo": "E1AH31", "severidad": "3", "fotos": "1", "ubicacion": "AC2: IMG_20260404_131808"}
                ]
            },
            {
                "nombre": "Juntas de dilatación",
                "items": [
                    {"codigo": "D1NS36", "severidad": "4", "fotos": "2", "ubicacion": "EST1 y EST2: IMG_5734, IMG_5742"}
                ]
            },
            {
                "nombre": "Barandas",
                "items": [
                    {"codigo": "S1MA58", "severidad": "5", "fotos": "2", "ubicacion": "AC2 Baranda AG AB: IMG_5703, IMG_5701"}
                ]
            },
            {
                "nombre": "Estribos",
                "items": [
                    {"codigo": "D2IN65", "severidad": "4", "fotos": "5", "ubicacion": "EST1 y EST2: IMG_5734, IMG_20260404_132854"},
                    {"codigo": "D6AB49", "severidad": "4", "fotos": "1", "ubicacion": "EST1: IMG_5733"},
                    {"codigo": "E2AS67", "severidad": "4", "fotos": "1", "ubicacion": "EST1 y EST2: IMG_5723"}
                ]
            },
            {
                "nombre": "Losa",
                "items": [
                    {"codigo": "D6DC44", "severidad": "3", "fotos": "1", "ubicacion": "V1 y V2: IMG_5730"},
                    {"codigo": "D6DC45", "severidad": "3", "fotos": "2", "ubicacion": "V3 y V4: IMG_5729"},
                    {"codigo": "D6EF46", "severidad": "3", "fotos": "1", "ubicacion": "V1 y V4: IMG_20260404_133055"},
                    {"codigo": "D6MS47", "severidad": "3", "fotos": "1", "ubicacion": "V3 y V4: IMG_5730"},
                    {"codigo": "E3DE91", "severidad": "3", "fotos": "2", "ubicacion": "V3 y V4: IMG_5729, IMG_20260404_133055"}
                ]
            },
            {
                "nombre": "Vigas",
                "items": [
                    {"codigo": "E3DE94", "severidad": "3", "fotos": "2", "ubicacion": "Parte media VG1: IMG_20260404_133051"}
                ]
            },
            {
                "nombre": "Señalización",
                "items": [
                    {"codigo": "S5FL129", "severidad": "5", "fotos": "", "ubicacion": "No cuenta con esta señal"},
                    {"codigo": "S5FL130", "severidad": "5", "fotos": "", "ubicacion": "No cuenta con esta señal"},
                    {"codigo": "S5FL139", "severidad": "5", "fotos": "3", "ubicacion": "No se evidencia infraestructura"}
                ]
            }
        ],
        "evaluacion": [
            {
                "nombre": "Superficie del Puente",
                "descripcion": "La superficie de rodadura presenta desgaste superficial, así como ahuellamientos y hundimientos localizados, principalmente en las proximidades de las juntas de dilatación.",
                "calificacion": "1.77",
                "imagenes": foto(0)
            },
            {
                "nombre": "Juntas de dilatación",
                "descripcion": "Se evidencia un desplazamiento de pequeña magnitud en las juntas de dilatación, asociado al hundimiento localizado de la superficie de rodadura. Adicionalmente, se observaron infiltraciones de agua a través de esta zona hacia los estribos.",
                "calificacion": "0.92",
                "imagenes": foto(1)
            },
            {
                "nombre": "Bordillo",
                "descripcion": "En el bordillo se evidenció una fisura cerca al acceso de salida, costado Guateque AG AB.",
                "calificacion": "0.68",
                "imagenes": foto(2)
            },
            {
                "nombre": "Barandas",
                "descripcion": "Las barandas del puente se encuentran en buen estado y cumplen su función de seguridad vial; sin embargo, se evidencia la ausencia de una abrazadera de sujeción.",
                "calificacion": "0.09",
                "imagenes": foto(3)
            },
            {
                "nombre": "Aletas",
                "descripcion": "En las aletas del costado Guateque se evidencia infiltración de agua proveniente de las cunetas de la superficie de rodadura.",
                "calificacion": "1.75",
                "imagenes": foto(4)
            },
            {
                "nombre": "Estribos",
                "descripcion": "En los estribos se evidencian procesos de segregación del concreto, fisuración transversal e infiltraciones de agua a través de las juntas de dilatación.",
                "calificacion": "1.75",
                "imagenes": foto(5)
            },
            {
                "nombre": "Apoyos",
                "descripcion": "Los apoyos del puente son de tipo neopreno, en los cuales se evidencia infiltración de agua. En un apoyo se observa un aplastamiento de pequeña magnitud.",
                "calificacion": "1.00",
                "imagenes": foto(6)
            },
            {
                "nombre": "Losa",
                "descripcion": "En la losa se observa presencia de eflorescencias, manchas amarillentas asociadas a procesos de oxidación, fisuración transversal y exposición del acero de refuerzo.",
                "calificacion": "1.25",
                "imagenes": foto(7)
            },
            {
                "nombre": "Vigas",
                "descripcion": "El puente cuenta con cuatro vigas rectangulares. Se evidenció una fisura asociada a esfuerzos de flexión en el centro de luz de la viga 1.",
                "calificacion": "2.04",
                "imagenes": foto(8)
            },
            {
                "nombre": "Señalización",
                "descripcion": "El puente no cuenta con señalización vial reglamentaria de velocidad máxima ni de restricción de peso máximo permitido.",
                "calificacion": "5.00",
                "imagenes": foto(9)
            },
            {
                "nombre": "Puente en General",
                "descripcion": "Se recomienda realizar labores de mantenimiento y limpieza general de la estructura. También se recomienda mejorar el manejo de la escorrentía superficial.",
                "calificacion": "1.57",
                "imagenes": foto(10)
            }
        ]
    }


def buscar_eval_sheet_en_modelo(z_modelo):
    hojas = leer_mapa_hojas(z_modelo)
    path = buscar_path_hoja_por_nombre(hojas, "Evaluación")

    if not path:
        raise FileNotFoundError("El Excel modelo no tiene hoja Evaluación.")

    return path


def obtener_rel_path_sheet(sheet_path):
    base = Path(sheet_path).name
    parent = str(Path(sheet_path).parent).replace("\\", "/")
    return f"{parent}/_rels/{base}.rels"


def obtener_drawing_desde_sheet(z, sheet_path):
    rel_path = obtener_rel_path_sheet(sheet_path)
    rels = ET.fromstring(z.read(rel_path))

    drawing_target = None
    printer_target = None

    for rel in rels:
        tipo = rel.attrib.get("Type", "")

        if tipo.endswith("/drawing"):
            drawing_target = rel.attrib["Target"]

        if tipo.endswith("/printerSettings"):
            printer_target = rel.attrib["Target"]

    sheet_dir = str(Path(sheet_path).parent).replace("\\", "/")

    drawing_path = str(Path(sheet_dir) / drawing_target).replace("\\", "/")
    drawing_path = drawing_path.replace("xl/worksheets/../", "xl/")

    printer_path = None

    if printer_target:
        printer_path = str(Path(sheet_dir) / printer_target).replace("\\", "/")
        printer_path = printer_path.replace("xl/worksheets/../", "xl/")

    return drawing_path, printer_path


def reemplazar_datos_evaluacion(sheet_root, data):
    identificacion = data.get("identificacion", {})

    escribir_celda(sheet_root, "D5", identificacion.get("nombrePuente", ""))
    escribir_celda(sheet_root, "D7", identificacion.get("carretera", ""))
    escribir_celda(sheet_root, "J7", identificacion.get("pr", ""))
    escribir_celda(sheet_root, "F9", identificacion.get("inspector", identificacion.get("responsableDiligenciamiento", "")))
    escribir_celda(sheet_root, "K9", identificacion.get("administrador", identificacion.get("administradorVial", "")))

    fecha = limpiar(identificacion.get("fecha", ""))

    if fecha:
        partes = re.split(r"[/-]", fecha)

        if len(partes) >= 3:
            escribir_celda(sheet_root, "X9", partes[0])
            escribir_celda(sheet_root, "Y9", partes[1])
            escribir_celda(sheet_root, "Z9", partes[2])

    id_puente = limpiar(identificacion.get("idPuente", ""))

    if id_puente:
        partes = re.split(r"[- ]+", id_puente)

        if len(partes) >= 4:
            escribir_celda(sheet_root, "L5", partes[0])
            escribir_celda(sheet_root, "O5", partes[1])
            escribir_celda(sheet_root, "V5", partes[2])
            escribir_celda(sheet_root, "Y5", partes[3])
        else:
            escribir_celda(sheet_root, "L5", id_puente)

    componentes = data.get("evaluacion", [])[:len(EVAL_SLOTS)]

    for idx, slot in enumerate(EVAL_SLOTS):
        comp = componentes[idx] if idx < len(componentes) else None

        if comp:
            escribir_celda(sheet_root, f"C{slot['titulo']}", comp.get("nombre", ""))
            escribir_celda(sheet_root, f"X{slot['titulo']}", comp.get("estado", "Diligenciado"))
            escribir_celda(sheet_root, f"AA{slot['titulo']}", "1")
            escribir_celda(sheet_root, f"C{slot['desc_label']}", "DESCRIPCIÓN")
            escribir_celda(sheet_root, f"C{slot['desc']}", "1. " + limpiar(comp.get("descripcion", "")))
            escribir_celda(sheet_root, f"C{slot['cal_label']}", "CALIFICACIÓN")
            escribir_celda(sheet_root, f"C{slot['cal']}", comp.get("calificacion", ""))
        else:
            escribir_celda(sheet_root, f"C{slot['titulo']}", "")
            escribir_celda(sheet_root, f"X{slot['titulo']}", "")
            escribir_celda(sheet_root, f"AA{slot['titulo']}", "")
            escribir_celda(sheet_root, f"C{slot['desc_label']}", "")
            escribir_celda(sheet_root, f"C{slot['desc']}", "")
            escribir_celda(sheet_root, f"C{slot['cal_label']}", "")
            escribir_celda(sheet_root, f"C{slot['cal']}", "")


def obtener_blip_ids(drawing_root):
    ids = []

    for blip in drawing_root.findall(".//a:blip", NS):
        rid = blip.attrib.get(f"{{{NS_REL}}}embed")

        if rid and rid not in ids:
            ids.append(rid)

    return ids


def crear_rels_drawing(blip_ids, image_names):
    root = ET.Element(f"{{{NS_PKG_REL}}}Relationships")

    for rid, image_name in zip(blip_ids, image_names):
        ET.SubElement(
            root,
            f"{{{NS_PKG_REL}}}Relationship",
            {
                "Id": rid,
                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                "Target": f"../media/{image_name}",
            }
        )

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def actualizar_content_types(xml_bytes, sheet_path, drawing_path):
    root = ET.fromstring(xml_bytes)

    def existe_default(ext):
        for el in root.findall(f"{{{NS_CT}}}Default"):
            if el.attrib.get("Extension") == ext:
                return True
        return False

    def existe_override(part_name):
        for el in root.findall(f"{{{NS_CT}}}Override"):
            if el.attrib.get("PartName") == part_name:
                return True
        return False

    if not existe_default("jpeg"):
        ET.SubElement(
            root,
            f"{{{NS_CT}}}Default",
            {
                "Extension": "jpeg",
                "ContentType": "image/jpeg",
            }
        )

    if not existe_default("jpg"):
        ET.SubElement(
            root,
            f"{{{NS_CT}}}Default",
            {
                "Extension": "jpg",
                "ContentType": "image/jpeg",
            }
        )

    sheet_part = "/" + sheet_path
    drawing_part = "/" + drawing_path

    if not existe_override(sheet_part):
        ET.SubElement(
            root,
            f"{{{NS_CT}}}Override",
            {
                "PartName": sheet_part,
                "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
            }
        )

    if not existe_override(drawing_part):
        ET.SubElement(
            root,
            f"{{{NS_CT}}}Override",
            {
                "PartName": drawing_part,
                "ContentType": "application/vnd.openxmlformats-officedocument.drawing+xml",
            }
        )

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def agregar_hoja_evaluacion_a_workbook(workbook_bytes, rels_bytes, sheet_path):
    workbook = ET.fromstring(workbook_bytes)
    rels = ET.fromstring(rels_bytes)

    sheets_el = workbook.find("main:sheets", NS)

    for sheet in sheets_el:
        if sheet.attrib.get("name", "").strip().lower() == "evaluación":
            return workbook_bytes, rels_bytes

    max_sheet_id = 0

    for sheet in sheets_el:
        max_sheet_id = max(max_sheet_id, int(sheet.attrib.get("sheetId", "0")))

    usados = set()

    for rel in rels:
        usados.add(rel.attrib.get("Id"))

    n = 1

    while f"rIdEval{n}" in usados:
        n += 1

    rid = f"rIdEval{n}"

    ET.SubElement(
        sheets_el,
        f"{{{NS_MAIN}}}sheet",
        {
            "name": "Evaluación",
            "sheetId": str(max_sheet_id + 1),
            f"{{{NS_REL}}}id": rid,
        }
    )

    ET.SubElement(
        rels,
        f"{{{NS_PKG_REL}}}Relationship",
        {
            "Id": rid,
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
            "Target": sheet_path.replace("xl/", ""),
        }
    )

    return (
        ET.tostring(workbook, encoding="utf-8", xml_declaration=True),
        ET.tostring(rels, encoding="utf-8", xml_declaration=True),
    )


def rels_sheet_evaluacion(drawing_path, printer_path):
    root = ET.Element(f"{{{NS_PKG_REL}}}Relationships")

    if printer_path:
        ET.SubElement(
            root,
            f"{{{NS_PKG_REL}}}Relationship",
            {
                "Id": "rId1",
                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/printerSettings",
                "Target": "../printerSettings/printerSettingsEval.bin",
            }
        )

    ET.SubElement(
        root,
        f"{{{NS_PKG_REL}}}Relationship",
        {
            "Id": "rId2",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing",
            "Target": "../drawings/" + Path(drawing_path).name,
        }
    )

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def convertir_excel_a_pdf(excel_path):
    excel_path = Path(excel_path).resolve()

    posibles = [
        "soffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]

    soffice = None

    for exe in posibles:
        try:
            result = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                soffice = exe
                break
        except Exception:
            pass

    if not soffice:
        raise FileNotFoundError("No encontré LibreOffice / soffice para exportar PDF.")

    subprocess.run(
        [
            soffice,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(OUTPUT_DIR.resolve()),
            str(excel_path),
        ],
        check=True
    )

    return OUTPUT_DIR / f"{excel_path.stem}.pdf"


def exportar(data, crear_pdf=False):
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"No existe la plantilla: {TEMPLATE}")

    modelo_eval = buscar_excel_modelo_evaluacion()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    nombre = limpiar(data.get("nombreArchivo"))

    if not nombre:
        nombre = f"INSPECCION_SIPUCOL_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsm"

    if not nombre.lower().endswith(".xlsm"):
        nombre += ".xlsm"

    salida = OUTPUT_DIR / nombre

    sheet_eval_path = "xl/worksheets/sheet32.xml"
    drawing_eval_path = "xl/drawings/drawing32.xml"
    rels_eval_path = "xl/worksheets/_rels/sheet32.xml.rels"
    rels_drawing_eval_path = "xl/drawings/_rels/drawing32.xml.rels"
    printer_eval_path = "xl/printerSettings/printerSettingsEval.bin"

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        nuevo_zip = tmp / "nuevo.xlsm"
        img_tmp = tmp / "imagenes_eval"
        img_tmp.mkdir()

        with zipfile.ZipFile(TEMPLATE, "r") as z_tpl, zipfile.ZipFile(modelo_eval, "r") as z_modelo:
            shared_tpl = leer_shared_strings(z_tpl)
            shared_modelo = leer_shared_strings(z_modelo)

            hojas_tpl = leer_mapa_hojas(z_tpl)

            eval_model_sheet_path = buscar_eval_sheet_en_modelo(z_modelo)
            eval_model_drawing_path, eval_model_printer_path = obtener_drawing_desde_sheet(z_modelo, eval_model_sheet_path)

            eval_sheet_root = ET.fromstring(z_modelo.read(eval_model_sheet_path))
            convertir_todas_las_celdas_a_inline(eval_sheet_root, shared_modelo)
            reemplazar_datos_evaluacion(eval_sheet_root, data)
            eval_sheet_bytes = ET.tostring(eval_sheet_root, encoding="utf-8", xml_declaration=True)

            drawing_root = ET.fromstring(z_modelo.read(eval_model_drawing_path))
            blip_ids = obtener_blip_ids(drawing_root)

            componentes_eval = data.get("evaluacion", [])

            image_names = []

            for i, rid in enumerate(blip_ids):
                comp = componentes_eval[i] if i < len(componentes_eval) else {}
                imagenes = comp.get("imagenes", [])

                image_name = f"sipucol_eval_{i + 1:02d}.jpeg"
                salida_img = img_tmp / image_name
                preparar_imagen_compuesta(imagenes, salida_img)

                image_names.append(image_name)

            drawing_bytes = ET.tostring(drawing_root, encoding="utf-8", xml_declaration=True)
            drawing_rels_bytes = crear_rels_drawing(blip_ids, image_names)

            escritos_tabla = 0

            with zipfile.ZipFile(nuevo_zip, "w", zipfile.ZIP_DEFLATED) as z_out:
                for item in z_tpl.infolist():
                    nombre_zip = item.filename

                    if nombre_zip in [
                        "xl/workbook.xml",
                        "xl/_rels/workbook.xml.rels",
                        "[Content_Types].xml",
                    ]:
                        continue

                    if nombre_zip in [
                        sheet_eval_path,
                        drawing_eval_path,
                        rels_eval_path,
                        rels_drawing_eval_path,
                        printer_eval_path,
                    ]:
                        continue

                    contenido = z_tpl.read(nombre_zip)

                    path_hoja = None
                    nombre_hoja = None

                    for hoja_nombre, hoja_path in hojas_tpl.items():
                        if hoja_path == nombre_zip:
                            path_hoja = hoja_path
                            nombre_hoja = hoja_nombre
                            break

                    if path_hoja and nombre_hoja:
                        root = ET.fromstring(contenido)

                        escribir_identificacion_en_tablas(root, data.get("identificacion", {}))

                        for componente in data.get("tablas", []):
                            comp_nombre = limpiar(componente.get("nombre")).lower()

                            if comp_nombre != nombre_hoja.strip().lower():
                                continue

                            for fila_item in componente.get("items", []):
                                if escribir_item_tabla(root, shared_tpl, fila_item):
                                    escritos_tabla += 1

                            escribir_observaciones_componente(root, shared_tpl, componente)

                        contenido = ET.tostring(root, encoding="utf-8", xml_declaration=True)

                    z_out.writestr(item, contenido)

                workbook_bytes, rels_bytes = agregar_hoja_evaluacion_a_workbook(
                    z_tpl.read("xl/workbook.xml"),
                    z_tpl.read("xl/_rels/workbook.xml.rels"),
                    sheet_eval_path,
                )

                z_out.writestr("xl/workbook.xml", workbook_bytes)
                z_out.writestr("xl/_rels/workbook.xml.rels", rels_bytes)

                content_types = actualizar_content_types(
                    z_tpl.read("[Content_Types].xml"),
                    sheet_eval_path,
                    drawing_eval_path,
                )

                z_out.writestr("[Content_Types].xml", content_types)
                z_out.writestr(sheet_eval_path, eval_sheet_bytes)
                z_out.writestr(drawing_eval_path, drawing_bytes)
                z_out.writestr(rels_eval_path, rels_sheet_evaluacion(drawing_eval_path, eval_model_printer_path))
                z_out.writestr(rels_drawing_eval_path, drawing_rels_bytes)

                if eval_model_printer_path and eval_model_printer_path in z_modelo.namelist():
                    z_out.writestr(printer_eval_path, z_modelo.read(eval_model_printer_path))

                for image_name in image_names:
                    z_out.writestr(f"xl/media/{image_name}", (img_tmp / image_name).read_bytes())

        shutil.move(nuevo_zip, salida)

    print("EXCEL FINAL LISTO")
    print(f"Archivo creado: {salida}")
    print(f"Filas de tabla escritas: {escritos_tabla}")
    print(f"Bloques de Evaluación: {len(data.get('evaluacion', []))}")

    if crear_pdf:
        pdf = convertir_excel_a_pdf(salida)
        print("PDF FINAL LISTO")
        print(f"Archivo creado: {pdf}")

    return salida


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=str)
    parser.add_argument("--demo-cueva", action="store_true")
    parser.add_argument("--pdf", action="store_true")

    args = parser.parse_args()

    if args.demo_cueva:
        data = data_demo_cueva()
    elif args.json:
        data = json.loads(Path(args.json).read_text(encoding="utf-8"))
    else:
        raise SystemExit("Usa --demo-cueva o --json archivo.json")

    exportar(data, crear_pdf=args.pdf)


if __name__ == "__main__":
    main()
