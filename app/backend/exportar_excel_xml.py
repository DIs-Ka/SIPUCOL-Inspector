import argparse
import json
import re
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET


BASE_DIR = Path(__file__).resolve().parents[1]

TEMPLATE = BASE_DIR / "manuals" / "04. FORMATO INSPECCION NIVEL 2 CON CALCULO DE IC SIN BLOQUEO (1).xlsm"
OUTPUT_DIR = BASE_DIR / "outputs"

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships"
}

ET.register_namespace("", NS["main"])

COLUMNAS_SEVERIDAD = {
    "0": "F",
    "1": "G",
    "2": "H",
    "3": "I",
    "4": "J",
    "5": "K",
}

COLUMNA_FOTOS = "L"
COLUMNA_UBICACION = "M"


def col_a_num(col):
    total = 0
    for char in col:
        total = total * 26 + ord(char.upper()) - 64
    return total


def separar_ref(ref):
    m = re.match(r"([A-Z]+)(\d+)", ref)
    if not m:
        return None, None
    return m.group(1), int(m.group(2))


def limpiar(texto):
    return str(texto or "").replace("\xa0", " ").strip()


def leer_shared_strings(z):
    if "xl/sharedStrings.xml" not in z.namelist():
        return []

    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    strings = []

    for si in root.findall("main:si", NS):
        textos = []
        for t in si.iter(f"{{{NS['main']}}}t"):
            textos.append(t.text or "")
        strings.append("".join(textos))

    return strings


def leer_mapa_hojas(z):
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))

    rel_map = {}

    for rel in rels:
        rel_id = rel.attrib["Id"]
        target = rel.attrib["Target"]
        rel_map[rel_id] = "xl/" + target.lstrip("/")

    hojas = {}

    for sheet in wb.find("main:sheets", NS):
        nombre = sheet.attrib["name"].strip()
        rel_id = sheet.attrib[f"{{{NS['rel']}}}id"]
        hojas[nombre.lower()] = rel_map[rel_id]

    return hojas


def valor_celda(cell, shared):
    if cell is None:
        return ""

    tipo = cell.attrib.get("t")

    if tipo == "s":
        v = cell.find("main:v", NS)
        if v is not None and v.text is not None:
            idx = int(v.text)
            if idx < len(shared):
                return limpiar(shared[idx])
        return ""

    if tipo == "inlineStr":
        textos = []
        for t in cell.iter(f"{{{NS['main']}}}t"):
            textos.append(t.text or "")
        return limpiar("".join(textos))

    v = cell.find("main:v", NS)
    if v is not None:
        return limpiar(v.text)

    return ""


def set_texto_celda(cell, valor):
    estilo = cell.attrib.get("s")
    ref = cell.attrib.get("r")

    cell.clear()
    cell.attrib["r"] = ref

    if estilo is not None:
        cell.attrib["s"] = estilo

    cell.attrib["t"] = "inlineStr"

    is_el = ET.SubElement(cell, f"{{{NS['main']}}}is")
    t_el = ET.SubElement(is_el, f"{{{NS['main']}}}t")
    t_el.text = str(valor)


def obtener_o_crear_celda(row, ref):
    for cell in row.findall("main:c", NS):
        if cell.attrib.get("r") == ref:
            return cell

    cell = ET.Element(f"{{{NS['main']}}}c", {"r": ref})
    row.append(cell)
    return cell


def buscar_fila_codigo(root, shared, codigo):
    codigo = codigo.upper().strip()

    for row in root.findall(".//main:row", NS):
        fila = int(row.attrib.get("r", "0"))

        for cell in row.findall("main:c", NS):
            ref = cell.attrib.get("r", "")
            col, _ = separar_ref(ref)

            if not col:
                continue

            if col_a_num(col) > 7:
                continue

            if valor_celda(cell, shared).upper().strip() == codigo:
                return row, fila

    return None, None


def limpiar_severidad(row, fila):
    for col in COLUMNAS_SEVERIDAD.values():
        ref = f"{col}{fila}"
        cell = obtener_o_crear_celda(row, ref)
        set_texto_celda(cell, "")


def escribir_item(root, shared, item):
    codigo = limpiar(item.get("codigo"))

    if not codigo:
        return False

    row, fila = buscar_fila_codigo(root, shared, codigo)

    if row is None:
        return False

    severidad = limpiar(item.get("severidad"))

    if severidad in COLUMNAS_SEVERIDAD:
        limpiar_severidad(row, fila)
        cell = obtener_o_crear_celda(row, f"{COLUMNAS_SEVERIDAD[severidad]}{fila}")
        set_texto_celda(cell, "x")

    fotos = limpiar(item.get("fotos"))
    ubicacion = limpiar(item.get("ubicacion"))

    if fotos:
        cell = obtener_o_crear_celda(row, f"{COLUMNA_FOTOS}{fila}")
        set_texto_celda(cell, fotos)

    if ubicacion:
        cell = obtener_o_crear_celda(row, f"{COLUMNA_UBICACION}{fila}")
        set_texto_celda(cell, ubicacion)

    return True


def escribir_celdas_identificacion(root, shared, identificacion):
    cambios = {
        "Nombre del puente": identificacion.get("nombrePuente"),
        "Administrador vial": identificacion.get("administradorVial"),
        "Entidad adminitradora": identificacion.get("entidadAdministradora"),
        "Entidad administradora": identificacion.get("entidadAdministradora"),
    }

    escritos = 0

    for row in root.findall(".//main:row", NS):
        fila = int(row.attrib.get("r", "0"))

        if fila > 20:
            continue

        cells = row.findall("main:c", NS)

        for cell in cells:
            texto = valor_celda(cell, shared)

            for label, valor in cambios.items():
                if not valor:
                    continue

                if label.lower() in texto.lower():
                    ref = cell.attrib.get("r")
                    col, _ = separar_ref(ref)
                    next_col_num = col_a_num(col) + 1

                    for destino in cells:
                        col_destino, _ = separar_ref(destino.attrib.get("r", ""))
                        if col_destino and col_a_num(col_destino) == next_col_num:
                            set_texto_celda(destino, valor)
                            escritos += 1
                            break

    return escritos


def crear_data_prueba():
    return {
        "nombreArchivo": "PRUEBA_XML_CUEVA_MORGAN.xlsm",
        "identificacion": {
            "nombrePuente": "PUENTE CUEVA DE MORGAN",
            "administradorVial": "CONCESIÓN TRANSVERSAL DEL SISGA",
            "entidadAdministradora": "ANI"
        },
        "componentes": [
            {
                "nombre": "Superficie del tablero ",
                "items": [
                    {
                        "codigo": "D1EP29",
                        "severidad": "4",
                        "fotos": "1",
                        "ubicacion": "Superficie de rodadura; IMG_5708"
                    },
                    {
                        "codigo": "S1DI11",
                        "severidad": "4",
                        "fotos": "1",
                        "ubicacion": "Superficie de rodadura: IMG_20260404_132216"
                    }
                ]
            },
            {
                "nombre": "Superficie de accesos",
                "items": [
                    {
                        "codigo": "E1DF5",
                        "severidad": "3",
                        "fotos": "2",
                        "ubicacion": "AC1 y AC2: IMG_5700, IMG_5706"
                    },
                    {
                        "codigo": "E1AH31",
                        "severidad": "3",
                        "fotos": "1",
                        "ubicacion": "AC2: IMG_20260404_131808"
                    }
                ]
            },
            {
                "nombre": "Juntas de dilatación",
                "items": [
                    {
                        "codigo": "D1NS36",
                        "severidad": "4",
                        "fotos": "2",
                        "ubicacion": "EST1 y EST2: IMG_5734, IMG_5742"
                    }
                ]
            },
            {
                "nombre": "Bordillo",
                "items": [
                    {
                        "codigo": "E1DE52",
                        "severidad": "4",
                        "fotos": "1",
                        "ubicacion": "Parte post AG AB cerca ALD2: IMG_5720"
                    }
                ]
            },
            {
                "nombre": "Barandas",
                "items": [
                    {
                        "codigo": "S1MA58",
                        "severidad": "5",
                        "fotos": "2",
                        "ubicacion": "AC2 Baranda AG AB: IMG_5703, IMG_5701"
                    }
                ]
            },
            {
                "nombre": "Aletas ",
                "items": [
                    {
                        "codigo": "D2IN63",
                        "severidad": "4",
                        "fotos": "1",
                        "ubicacion": "ALD2 CD AG AB: IMG_5705"
                    },
                    {
                        "codigo": "E2DE66",
                        "severidad": "4",
                        "fotos": "1",
                        "ubicacion": "ALD2 CD AG AR: IMG_5715"
                    }
                ]
            },
            {
                "nombre": "Estribos",
                "items": [
                    {
                        "codigo": "D2IN65",
                        "severidad": "4",
                        "fotos": "5",
                        "ubicacion": "EST1 y EST2: IMG_5734,IMG_20260404_132854"
                    },
                    {
                        "codigo": "D6AB49",
                        "severidad": "4",
                        "fotos": "1",
                        "ubicacion": "EST1: IMG_5733"
                    },
                    {
                        "codigo": "E2AS67",
                        "severidad": "4",
                        "fotos": "1",
                        "ubicacion": "EST1 y EST2: IMG_5723"
                    }
                ]
            },
            {
                "nombre": "Apoyos",
                "items": [
                    {
                        "codigo": "D3IN80",
                        "severidad": "3",
                        "fotos": "3",
                        "ubicacion": "Ambos costados"
                    },
                    {
                        "codigo": "E3DE81",
                        "severidad": "4",
                        "fotos": "1",
                        "ubicacion": "EST2 VIG3: IMG_5736"
                    }
                ]
            },
            {
                "nombre": "Losa",
                "items": [
                    {
                        "codigo": "D6DC44",
                        "severidad": "3",
                        "fotos": "1",
                        "ubicacion": "V1 y V2: IMG_5730"
                    },
                    {
                        "codigo": "D6DC45",
                        "severidad": "3",
                        "fotos": "2",
                        "ubicacion": "V3 y V4: IMG_5729"
                    },
                    {
                        "codigo": "D6EF46",
                        "severidad": "3",
                        "fotos": "1",
                        "ubicacion": "V1 y V4: IMG_20260404_133055"
                    },
                    {
                        "codigo": "D6MS47",
                        "severidad": "3",
                        "fotos": "1",
                        "ubicacion": "V3 y V4: IMG_5730"
                    },
                    {
                        "codigo": "E3DE91",
                        "severidad": "3",
                        "fotos": "2",
                        "ubicacion": "V3 y V4: IMG_5729,IMG_20260404_133055"
                    }
                ]
            },
            {
                "nombre": "Vigas",
                "items": [
                    {
                        "codigo": "E3DE94",
                        "severidad": "3",
                        "fotos": "2",
                        "ubicacion": "Parte media VG1: IMG_20260404_133051"
                    }
                ]
            },
            {
                "nombre": "Taludes y accesos",
                "items": [
                    {
                        "codigo": "E2ER61",
                        "severidad": "3",
                        "fotos": "",
                        "ubicacion": ""
                    }
                ]
            },
            {
                "nombre": "Señalización",
                "items": [
                    {
                        "codigo": "S5FL129",
                        "severidad": "5",
                        "fotos": "",
                        "ubicacion": "No cuenta con esta señal"
                    },
                    {
                        "codigo": "S5FL130",
                        "severidad": "5",
                        "fotos": "",
                        "ubicacion": "No cuenta con esta señal"
                    },
                    {
                        "codigo": "S5FL139",
                        "severidad": "5",
                        "fotos": "3",
                        "ubicacion": "No se evidencia infraestructura"
                    }
                ]
            }
        ]
    }


def exportar(data):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    nombre = data.get("nombreArchivo") or f"inspeccion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsm"
    salida = OUTPUT_DIR / nombre

    shutil.copy2(TEMPLATE, salida)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        temp_zip = tmp / "nuevo.xlsm"

        with zipfile.ZipFile(salida, "r") as zin, zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zout:
            shared = leer_shared_strings(zin)
            hojas = leer_mapa_hojas(zin)

            hojas_a_modificar = {}

            for componente in data.get("componentes", []):
                nombre_hoja = limpiar(componente.get("nombre")).lower()
                if nombre_hoja in hojas:
                    hojas_a_modificar.setdefault(hojas[nombre_hoja], []).extend(componente.get("items", []))
                else:
                    print(f"No encontré hoja: {componente.get('nombre')}")

            escritos = 0

            for item in zin.infolist():
                contenido = zin.read(item.filename)

                if item.filename in hojas_a_modificar:
                    root = ET.fromstring(contenido)

                    escribir_celdas_identificacion(root, shared, data.get("identificacion", {}))

                    for fila_item in hojas_a_modificar[item.filename]:
                        if escribir_item(root, shared, fila_item):
                            escritos += 1
                        else:
                            print(f"No escribí código: {fila_item.get('codigo')} en {item.filename}")

                    contenido = ET.tostring(root, encoding="utf-8", xml_declaration=True)

                zout.writestr(item, contenido)

        shutil.move(temp_zip, salida)

    print("EXPORTACIÓN XML LISTA")
    print(f"Archivo creado: {salida}")
    print(f"Filas escritas: {escritos}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--json", type=str)

    args = parser.parse_args()

    if args.test:
        data = crear_data_prueba()
    elif args.json:
        data = json.loads(Path(args.json).read_text(encoding="utf-8"))
    else:
        raise SystemExit("Usa --test o --json archivo.json")

    exportar(data)


if __name__ == "__main__":
    main()
