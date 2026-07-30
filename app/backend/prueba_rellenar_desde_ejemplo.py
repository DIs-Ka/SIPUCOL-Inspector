import re
import shutil
import tempfile
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET


BASE_DIR = Path(__file__).resolve().parents[1]

TEMPLATE = BASE_DIR / "manuals" / "04. FORMATO INSPECCION NIVEL 2 CON CALCULO DE IC SIN BLOQUEO (1).xlsm"
OUTPUT_DIR = BASE_DIR / "outputs"

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

NS = {
    "main": NS_MAIN,
    "rel": NS_REL,
}

ET.register_namespace("", NS_MAIN)


def buscar_referencia():
    candidatos = list((BASE_DIR / "manuals").glob("*CUEVA*MORGAN*.xlsm"))

    candidatos = [
        archivo for archivo in candidatos
        if "SIN BLOQUEO" not in archivo.name.upper()
    ]

    if not candidatos:
        raise FileNotFoundError(
            "No encontré el Excel lleno de Cueva de Morgan en manuals. "
            "Copia el archivo lleno a la carpeta manuals."
        )

    return candidatos[0]


def limpiar(valor):
    return str(valor or "").replace("\xa0", " ").strip()


def col_a_num(col):
    total = 0

    for char in col:
        total = total * 26 + ord(char.upper()) - 64

    return total


def separar_ref(ref):
    match = re.match(r"([A-Z]+)(\d+)", ref)

    if not match:
        return None, None

    return match.group(1), int(match.group(2))


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


def leer_valor(cell, shared):
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


def escribir_inline(cell, valor):
    ref = cell.attrib.get("r")
    estilo = cell.attrib.get("s")

    cell.clear()
    cell.attrib["r"] = ref

    if estilo is not None:
        cell.attrib["s"] = estilo

    cell.attrib["t"] = "inlineStr"

    is_el = ET.SubElement(cell, f"{{{NS_MAIN}}}is")
    t_el = ET.SubElement(is_el, f"{{{NS_MAIN}}}t")
    t_el.text = str(valor)


def obtener_o_crear_row(root, fila):
    sheet_data = root.find("main:sheetData", NS)

    for row in sheet_data.findall("main:row", NS):
        if int(row.attrib.get("r", "0")) == fila:
            return row

    row = ET.Element(f"{{{NS_MAIN}}}row", {"r": str(fila)})
    sheet_data.append(row)
    return row


def obtener_o_crear_cell(row, ref):
    for cell in row.findall("main:c", NS):
        if cell.attrib.get("r") == ref:
            return cell

    cell = ET.Element(f"{{{NS_MAIN}}}c", {"r": ref})
    row.append(cell)
    return cell


def mapa_hojas(z):
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


def copiar_celdas_visibles(source_root, target_root, shared_source):
    copiadas = 0

    for row_source in source_root.findall(".//main:row", NS):
        fila = int(row_source.attrib.get("r", "0"))

        if fila > 220:
            continue

        for cell_source in row_source.findall("main:c", NS):
            ref = cell_source.attrib.get("r", "")
            col, row_num = separar_ref(ref)

            if not col or row_num is None:
                continue

            col_num = col_a_num(col)

            if col_num < col_a_num("B") or col_num > col_a_num("O"):
                continue

            valor = leer_valor(cell_source, shared_source)

            if valor == "":
                continue

            row_target = obtener_o_crear_row(target_root, fila)
            cell_target = obtener_o_crear_cell(row_target, ref)

            escribir_inline(cell_target, valor)
            copiadas += 1

    return copiadas


def partes_extra_de_referencia(nombre):
    if nombre == "[Content_Types].xml":
        return True

    if nombre.startswith("xl/media/"):
        return True

    if nombre.startswith("xl/drawings/"):
        return True

    if nombre.startswith("xl/worksheets/_rels/"):
        return True

    return False


def main():
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"No existe la plantilla: {TEMPLATE}")

    referencia = buscar_referencia()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    salida = OUTPUT_DIR / "PRUEBA_RELLENADA_DESDE_EJEMPLO_CUEVA_MORGAN.xlsm"

    shutil.copy2(TEMPLATE, salida)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        nuevo_zip = tmpdir / "nuevo.xlsm"

        with zipfile.ZipFile(referencia, "r") as z_ref, zipfile.ZipFile(salida, "r") as z_tpl:
            shared_ref = leer_shared_strings(z_ref)
            hojas_ref = mapa_hojas(z_ref)
            hojas_tpl = mapa_hojas(z_tpl)

            evaluacion_ref = hojas_ref.get("evaluación") or hojas_ref.get("evaluacion")
            evaluacion_tpl = hojas_tpl.get("evaluación") or hojas_tpl.get("evaluacion")

            total_celdas = 0
            total_hojas = 0

            archivos_escritos = set()

            with zipfile.ZipFile(nuevo_zip, "w", zipfile.ZIP_DEFLATED) as z_out:
                for item in z_tpl.infolist():
                    nombre = item.filename

                    if partes_extra_de_referencia(nombre) and nombre in z_ref.namelist():
                        z_out.writestr(item, z_ref.read(nombre))
                        archivos_escritos.add(nombre)
                        continue

                    if evaluacion_tpl and evaluacion_ref and nombre == evaluacion_tpl:
                        z_out.writestr(item, z_ref.read(evaluacion_ref))
                        archivos_escritos.add(nombre)
                        print("Hoja Evaluación copiada desde el ejemplo, incluyendo referencias de imágenes.")
                        continue

                    hoja_nombre = None

                    for nombre_hoja, path_hoja in hojas_tpl.items():
                        if path_hoja == nombre:
                            hoja_nombre = nombre_hoja
                            break

                    if hoja_nombre and hoja_nombre in hojas_ref:
                        source_xml = z_ref.read(hojas_ref[hoja_nombre])
                        target_xml = z_tpl.read(nombre)

                        source_root = ET.fromstring(source_xml)
                        target_root = ET.fromstring(target_xml)

                        copiadas = copiar_celdas_visibles(source_root, target_root, shared_ref)

                        if copiadas:
                            total_celdas += copiadas
                            total_hojas += 1

                        contenido = ET.tostring(
                            target_root,
                            encoding="utf-8",
                            xml_declaration=True
                        )

                        z_out.writestr(item, contenido)
                        archivos_escritos.add(nombre)
                    else:
                        z_out.writestr(item, z_tpl.read(nombre))
                        archivos_escritos.add(nombre)

                for nombre in z_ref.namelist():
                    if nombre in archivos_escritos:
                        continue

                    if partes_extra_de_referencia(nombre):
                        z_out.writestr(nombre, z_ref.read(nombre))
                        archivos_escritos.add(nombre)

        shutil.move(nuevo_zip, salida)

    print("LISTO")
    print(f"Referencia usada: {referencia}")
    print(f"Archivo creado: {salida}")
    print(f"Hojas con celdas copiadas: {total_hojas}")
    print(f"Celdas visibles copiadas: {total_celdas}")
    print("")
    print("Abre el archivo creado y compara contra el Excel lleno de referencia.")


if __name__ == "__main__":
    main()
