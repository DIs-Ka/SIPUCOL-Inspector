
import copy
import json
import re
import shutil
import threading
import time
import uuid
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


BASE_DIR = Path(__file__).resolve().parents[1]
MANUALS_DIR = BASE_DIR / "manuals"
RUNTIME_DIR = BASE_DIR / ".sipucol_runtime"
TRACKER_PATH = BASE_DIR / "backend" / "template_tracker.json"

RUNTIME_DIR.mkdir(exist_ok=True)

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

ET.register_namespace("", NS_MAIN)
ET.register_namespace("r", R_NS)

jobs = {}
jobs_lock = threading.Lock()

app = FastAPI(title="SIPUCOL Inspector Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def log(msg):
    print(f"[SIPUCOL] {msg}", flush=True)


def set_job(job_id, **changes):
    with jobs_lock:
        job = jobs.setdefault(job_id, {})
        job.update(changes)
        return job


def normalizar(txt):
    txt = str(txt or "").strip().lower()
    txt = (
        txt.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )
    return re.sub(r"[^a-z0-9]+", "", txt)


def nombre_seguro(txt):
    txt = str(txt or "INSPECCION_SIPUCOL")
    txt = re.sub(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ _.-]+", "", txt)
    txt = re.sub(r"\s+", "_", txt).strip("_")
    return txt[:90] or "INSPECCION_SIPUCOL"


def nombre_base_desde_data(data):
    identificacion = data.get("identificacion") or {}

    nombre = (
        data.get("projectName")
        or identificacion.get("nombrePuente")
        or data.get("nombreArchivo")
        or "INSPECCION_SIPUCOL"
    )

    nombre = nombre_seguro(nombre)

    if nombre.lower().endswith(".xlsm"):
        nombre = nombre[:-5]

    return nombre_seguro(nombre)


def buscar_plantilla():
    exactas = [
        MANUALS_DIR / "04. FORMATO INSPECCION NIVEL 2 CON CALCULO DE IC SIN BLOQUEO (1).xlsm",
        MANUALS_DIR / "04. FORMATO INSPECCION NIVEL 2 CON CALCULO DE IC SIN BLOQUEO.xlsm",
    ]

    for path in exactas:
        if path.exists() and path.stat().st_size > 50000:
            return path

    candidatos = [
        p for p in MANUALS_DIR.glob("*.xlsm")
        if "CUEVA" not in p.name.upper()
    ]

    if candidatos:
        candidatos.sort(key=lambda p: p.stat().st_size, reverse=True)
        return candidatos[0]

    raise RuntimeError("No encontré la plantilla original .xlsm en manuals.")


def validar_xlsm(path):
    path = Path(path)

    if not path.exists():
        raise RuntimeError(f"No existe: {path}")

    if path.stat().st_size < 50000:
        raise RuntimeError(f"Archivo demasiado pequeño o vacío: {path}")

    with zipfile.ZipFile(path, "r") as zf:
        bad = zf.testzip()

        if bad:
            raise RuntimeError(f"XLSM corrupto internamente en: {bad}")

        required = [
            "[Content_Types].xml",
            "xl/workbook.xml",
            "xl/_rels/workbook.xml.rels",
        ]

        names = set(zf.namelist())

        for req in required:
            if req not in names:
                raise RuntimeError(f"Falta parte obligatoria: {req}")

        hojas = [n for n in names if n.startswith("xl/worksheets/") and n.endswith(".xml")]

        if not hojas:
            raise RuntimeError("El libro no tiene hojas.")


def elegir_archivo_guardar_excel(nombre_sugerido):
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update()

    path = filedialog.asksaveasfilename(
        title="Guardar Excel SIPUCOL",
        defaultextension=".xlsm",
        initialfile=nombre_sugerido,
        filetypes=[
            ("Excel habilitado para macros", "*.xlsm"),
            ("Todos los archivos", "*.*"),
        ],
    )

    root.destroy()

    if not path:
        return None

    if not path.lower().endswith(".xlsm"):
        path += ".xlsm"

    return Path(path)


def leer_shared_strings(zf):
    try:
        xml = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []

    root = ET.fromstring(xml)
    values = []

    for si in root.findall(f"{{{NS_MAIN}}}si"):
        text = []
        for t in si.findall(f".//{{{NS_MAIN}}}t"):
            text.append(t.text or "")
        values.append("".join(text))

    return values


def leer_valor_celda(cell, shared):
    tipo = cell.attrib.get("t")

    if tipo == "s":
        v = cell.find(f"{{{NS_MAIN}}}v")

        if v is None or v.text is None:
            return ""

        try:
            return shared[int(v.text)]
        except Exception:
            return ""

    if tipo == "inlineStr":
        return "".join(t.text or "" for t in cell.findall(f".//{{{NS_MAIN}}}t"))

    v = cell.find(f"{{{NS_MAIN}}}v")

    return v.text if v is not None and v.text is not None else ""


def split_ref(ref):
    m = re.match(r"([A-Z]+)(\d+)", str(ref or ""))

    if not m:
        return "", 0

    return m.group(1), int(m.group(2))


def col_num(col):
    n = 0

    for ch in str(col or ""):
        n = n * 26 + (ord(ch.upper()) - 64)

    return n


def ordenar_celdas(row):
    cells = [c for c in row.findall(f"{{{NS_MAIN}}}c")]
    others = [c for c in list(row) if c.tag != f"{{{NS_MAIN}}}c"]

    cells.sort(key=lambda c: col_num(split_ref(c.attrib.get("r", ""))[0]))

    for child in list(row):
        row.remove(child)

    for c in cells:
        row.append(c)

    for c in others:
        row.append(c)


def get_or_create_cell(row, ref):
    for cell in row.findall(f"{{{NS_MAIN}}}c"):
        if cell.attrib.get("r") == ref:
            return cell

    cell = ET.Element(f"{{{NS_MAIN}}}c", {"r": ref})
    row.append(cell)
    ordenar_celdas(row)

    return cell


def escribir_texto(row, ref, value):
    cell = get_or_create_cell(row, ref)

    # Preserva estilo, pero cambia contenido.
    style = cell.attrib.get("s")

    for child in list(cell):
        cell.remove(child)

    cell.attrib.clear()
    cell.attrib["r"] = ref

    if style is not None:
        cell.attrib["s"] = style

    cell.attrib["t"] = "inlineStr"

    is_el = ET.SubElement(cell, f"{{{NS_MAIN}}}is")
    t_el = ET.SubElement(is_el, f"{{{NS_MAIN}}}t")
    t_el.text = str(value)


def limpiar_contenido(row, ref):
    cell = get_or_create_cell(row, ref)
    style = cell.attrib.get("s")

    for child in list(cell):
        cell.remove(child)

    cell.attrib.clear()
    cell.attrib["r"] = ref

    if style is not None:
        cell.attrib["s"] = style


def sheet_map(zf):
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))

    rid_target = {}

    for rel in rels:
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target")

        if not rid or not target:
            continue

        if target.startswith("/"):
            p = target.lstrip("/")
        else:
            p = "xl/" + target.lstrip("/")

        rid_target[rid] = p.replace("\\", "/").replace("xl/xl/", "xl/")

    out = []

    for sheet in wb.findall(f".//{{{NS_MAIN}}}sheet"):
        rid = sheet.attrib.get(f"{{{R_NS}}}id")
        name = sheet.attrib.get("name", "")
        path = rid_target.get(rid)

        if path:
            out.append({
                "name": name,
                "path": path,
                "sheetId": sheet.attrib.get("sheetId", ""),
                "rid": rid,
            })

    return out


def hoja_excluida(name):
    n = normalizar(name)

    return (
        "indice" in n
        or "calculo" in n
        or "anx" in n
        or "categoria" in n
        or "patologia" in n
        or "evaluacion" in n
    )


def valor_en_ref(row, shared, ref):
    for cell in row.findall(f"{{{NS_MAIN}}}c"):
        if cell.attrib.get("r") == ref:
            return leer_valor_celda(cell, shared)

    return ""


def generar_template_tracker():
    template = buscar_plantilla()
    validar_xlsm(template)

    tracker = {
        "version": "1.0",
        "template": str(template),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "severity_cols": {
            "0": "G",
            "1": "H",
            "2": "I",
            "3": "J",
            "4": "K",
            "5": "L",
        },
        "foto_col": "M",
        "ubicacion_col": "O",
        "observaciones": {
            "levantamiento": "B106",
            "revisor": "H106",
        },
        "identificacion": {
            "nombrePuente": "C13",
            "administradorVial": "C15",
            "entidadAdministradora": "C17",
            "responsableDiligenciamiento": "C19",
            "cargoDiligenciamiento": "F19",
            "tarjetaDiligenciamiento": "Q19",
            "responsableRevision": "C21",
            "cargoRevision": "F21",
            "tarjetaRevision": "Q21",
        },
        "sheets": [],
    }

    total_rows = 0

    with zipfile.ZipFile(template, "r") as zf:
        shared = leer_shared_strings(zf)

        for sh in sheet_map(zf):
            if hoja_excluida(sh["name"]):
                continue

            root = ET.fromstring(zf.read(sh["path"]))
            sheet_data = root.find(f"{{{NS_MAIN}}}sheetData")

            if sheet_data is None:
                continue

            entries = []

            for row in sheet_data.findall(f"{{{NS_MAIN}}}row"):
                try:
                    rn = int(row.attrib.get("r", "0") or 0)
                except Exception:
                    continue

                # Solo tabla visible real del formato.
                if rn < 1 or rn > 150:
                    continue

                codigo = str(valor_en_ref(row, shared, f"B{rn}") or "").strip().upper()
                dano = str(valor_en_ref(row, shared, f"C{rn}") or "").strip()
                material = str(valor_en_ref(row, shared, f"D{rn}") or "").strip()

                if not re.match(r"^[A-Z]\d", codigo):
                    continue

                entries.append({
                    "row": rn,
                    "codigo": codigo,
                    "dano": dano,
                    "material": material,
                    "cells": {
                        "sev0": f"G{rn}",
                        "sev1": f"H{rn}",
                        "sev2": f"I{rn}",
                        "sev3": f"J{rn}",
                        "sev4": f"K{rn}",
                        "sev5": f"L{rn}",
                        "fotos": f"M{rn}",
                        "ubicacion": f"O{rn}",
                    },
                })

            if entries:
                tracker["sheets"].append({
                    "name": sh["name"],
                    "path": sh["path"],
                    "component_key": normalizar(sh["name"]),
                    "rows": entries,
                })
                total_rows += len(entries)

    tracker["total_sheets"] = len(tracker["sheets"])
    tracker["total_rows"] = total_rows

    TRACKER_PATH.write_text(json.dumps(tracker, ensure_ascii=False, indent=2), encoding="utf-8")

    return tracker


def get_tracker():
    if not TRACKER_PATH.exists():
        return generar_template_tracker()

    try:
        return json.loads(TRACKER_PATH.read_text(encoding="utf-8"))
    except Exception:
        return generar_template_tracker()



def payload_componentes(data):
    # Fuente preferida: tablas = solo lo activo/filtrado.
    # Fallback: componentesEstado = proyecto completo guardado.
    source = data.get("tablas")

    if not source:
        source = data.get("componentesEstado") or []

    comps = []

    for comp in source:
        items = []

        for item in comp.get("items") or []:
            codigo = str(item.get("codigo") or "").strip().upper()
            severidad = str(item.get("severidad") or "").strip()
            fotos = str(item.get("fotos") or "").strip()
            ubicacion = str(item.get("ubicacion") or "").strip()

            # Solo se exportan filas donde el usuario hizo algo.
            if not codigo:
                continue

            if not severidad and not fotos and not ubicacion:
                continue

            items.append({
                "codigo": codigo,
                "severidad": severidad,
                "fotos": fotos,
                "ubicacion": ubicacion,
                "detalle": str(item.get("detalle") or item.get("material") or "").strip(),
                "dano": str(item.get("dano") or item.get("daño") or "").strip(),
                "filaExcel": str(item.get("filaExcel") or item.get("fila") or item.get("row") or "").strip(),
            })

        obs_lev = (
            comp.get("observacionesLevantamiento")
            or comp.get("observacionesInspector")
            or comp.get("observacionesCampo")
            or ""
        )

        obs_rev = (
            comp.get("observacionesRevisor")
            or comp.get("observacionesEquipoTecnico")
            or comp.get("observacionesTecnico")
            or comp.get("observacionesEquipo")
            or ""
        )

        # Conserva componentes con observaciones aunque no tengan daños marcados.
        if items or obs_lev or obs_rev:
            comps.append({
                "nombre": comp.get("nombre") or "",
                "key": normalizar(comp.get("nombre") or ""),
                "observacionesLevantamiento": obs_lev,
                "observacionesRevisor": obs_rev,
                "items": items,
            })

    return comps

def match_sheet_for_component(comp, tracker):
    key = comp["key"]

    best = None
    best_score = 0

    for sh in tracker["sheets"]:
        skey = sh["component_key"]

        score = 0

        if key == skey:
            score = 100
        elif key and skey and (key in skey or skey in key):
            score = 80
        else:
            score = sum(10 for part in re.findall(r"[a-z0-9]{4,}", key) if part in skey)

        if score > best_score:
            best = sh
            best_score = score

    return best if best_score >= 10 else None


def material_key_from_item(item):
    texto = normalizar(f"{item.get('detalle', '')} {item.get('dano', '')}")

    for mat in ["asfalto", "concreto", "acero", "afirmado", "mamposteria"]:
        if mat in texto:
            return mat

    return ""


def row_hint(item):
    m = re.search(r"\d+", str(item.get("filaExcel") or ""))

    if not m:
        return None

    n = int(m.group(0))

    if 1 <= n <= 150:
        return n

    return None



def match_row_for_item(item, sheet_tracker, used_rows):
    codigo = item["codigo"]
    mat_item = material_key_from_item(item)
    hint = row_hint(item)

    rows = sheet_tracker["rows"]

    # Prioridad total: filaExcel viene de la plantilla real.
    # Si la UI dice fila 34, se escribe fila 34.
    if hint:
        for r in rows:
            if r["row"] == hint and r["row"] not in used_rows:
                if r["codigo"] == codigo:
                    return r, "filaExcel"
                return r, f"filaExcel_advertencia_codigo_template_{r['codigo']}"

    candidates = [
        r for r in rows
        if r["codigo"] == codigo and r["row"] not in used_rows
    ]

    if not candidates:
        return None, "no encontrado"

    if mat_item:
        material_candidates = [
            r for r in candidates
            if mat_item in normalizar(r.get("material"))
        ]

        if material_candidates:
            return material_candidates[0], "codigo+material"

    return candidates[0], "codigo"

def get_or_create_row(sheet_data, row_num):
    for row in sheet_data.findall(f"{{{NS_MAIN}}}row"):
        if int(row.attrib.get("r", "0") or 0) == row_num:
            return row

    row = ET.Element(f"{{{NS_MAIN}}}row", {"r": str(row_num)})
    sheet_data.append(row)

    rows = sheet_data.findall(f"{{{NS_MAIN}}}row")
    rows.sort(key=lambda r: int(r.attrib.get("r", "0") or 0))

    for child in list(sheet_data):
        sheet_data.remove(child)

    for r in rows:
        sheet_data.append(r)

    return row



def escribir_identificacion_en_root(root, tracker, data):
    identificacion = data.get("identificacion") or {}
    sheet_data = root.find(f"{{{NS_MAIN}}}sheetData")

    if sheet_data is None:
        return []

    written = []

    def write(ref, value, campo):
        if value in [None, ""]:
            return

        _, rn = split_ref(ref)
        row = get_or_create_row(sheet_data, rn)
        escribir_texto(row, ref, value)
        written.append({"campo": campo, "cell": ref, "value": str(value)})

    def clear(ref):
        _, rn = split_ref(ref)
        row = get_or_create_row(sheet_data, rn)
        limpiar_contenido(row, ref)

    # Celdas reales según plantilla.
    # Corrección importante:
    # Cargo NO va en F19/F21, va en G19/G21.
    # Tarjeta NO va en Q19/Q21, va en S19/S21.
    simple_map = {
        "nombrePuente": "C13",
        "administradorVial": "C15",
        "entidadAdministradora": "C17",
        "responsableDiligenciamiento": "C19",
        "cargoDiligenciamiento": "G19",
        "tarjetaDiligenciamiento": "S19",
        "responsableRevision": "C21",
        "cargoRevision": "G21",
        "tarjetaRevision": "S21",
    }

    for key, ref in simple_map.items():
        write(ref, identificacion.get(key), key)

    # ID Puente dividido en cuatro secciones.
    #
    # IMPORTANTE:
    # ID carretera y tramo se escribe siempre alineado
    # contra la derecha de sus ocho casillas J13:Q13.
    #
    # Ejemplos:
    # 120 -> P13=1, Q13 no: realmente N/A; se distribuye
    #        en las últimas tres celdas manteniendo 1,2,0.
    # 10  -> únicamente las últimas dos celdas.
    #
    # No se invierte el texto: 120 nunca se convierte en 021.

    grupos_id = [
        (
            "idPuente",
            ["G13", "H13"],
            r"[^0-9]",
        ),
        (
            "idCarreteraTramo",
            [
                "J13",
                "K13",
                "L13",
                "M13",
                "N13",
                "O13",
                "P13",
                "Q13",
            ],
            r"[^A-Za-z0-9]",
        ),
        (
            "sentido",
            ["S13", "T13"],
            r"[^A-Za-z0-9]",
        ),
        (
            "consecutivo",
            ["V13", "W13", "X13", "Y13"],
            r"[^A-Za-z0-9]",
        ),
    ]

    todas_celdas_id = [
        ref
        for _, refs, _ in grupos_id
        for ref in refs
    ]

    # Siempre se limpian primero todas las casillas.
    # Así no quedan caracteres de un valor anterior más largo.
    for ref in todas_celdas_id:
        clear(ref)

    id_anterior = str(
        identificacion.get("idPuente")
        or ""
    ).strip()

    partes_anteriores = (
        id_anterior.split("-")
        if "-" in id_anterior
        else []
    )

    for indice, (key, refs, prohibidos) in enumerate(
        grupos_id
    ):
        raw = str(
            identificacion.get(key)
            or ""
        ).strip()

        # Compatibilidad con proyectos antiguos que guardaban
        # todo el ID dentro de idPuente separado por guiones.
        if (
            not raw
            and partes_anteriores
            and indice < len(partes_anteriores)
        ):
            raw = partes_anteriores[indice]

        clean = re.sub(
            prohibidos,
            "",
            raw,
        )

        if key in {
            "idCarreteraTramo",
            "sentido",
            "consecutivo",
        }:
            clean = clean.upper()

        if key == "idCarreteraTramo":
            # El Excel solo tiene ocho casillas.
            # Si existen más de ocho caracteres, se conservan
            # para el proyecto, pero se exportan los últimos ocho.
            texto_excel = clean[-len(refs):]

            if texto_excel:
                inicio = len(refs) - len(texto_excel)
                celdas_destino = refs[inicio:]
            else:
                celdas_destino = []

        else:
            # Los demás grupos conservan su alineación actual.
            texto_excel = clean[:len(refs)]
            celdas_destino = refs[:len(texto_excel)]

        for ref, character in zip(
            celdas_destino,
            texto_excel,
        ):
            write(
                ref,
                character,
                key,
            )

    # Fecha: formato visual M6 N6 / P6 Q6 / S6
    fecha_raw = str(identificacion.get("fecha") or "").strip()

    if fecha_raw:
        nums = re.findall(r"\d+", fecha_raw)
        dia = mes = anio = ""

        if len(nums) >= 3:
            if len(nums[0]) == 4:
                anio, mes, dia = nums[0], nums[1], nums[2]
            else:
                dia, mes, anio = nums[0], nums[1], nums[2]

        dia = dia.zfill(2)[:2]
        mes = mes.zfill(2)[:2]

        if dia and mes and anio:
            write("M6", dia[0], "fecha_dia")
            write("N6", dia[1], "fecha_dia")
            write("P6", mes[0], "fecha_mes")
            write("Q6", mes[1], "fecha_mes")
            write("S6", anio, "fecha_anio")

    # Hora: F8 G8 : I8 J8 + checkbox L8 AM / O8 PM
    hora_raw = str(identificacion.get("hora") or "").strip()

    if hora_raw:
        nums = re.findall(r"\d+", hora_raw)

        if nums:
            hh = int(nums[0])
            mm = int(nums[1]) if len(nums) > 1 else 0

            is_pm = "pm" in hora_raw.lower() or "p.m" in hora_raw.lower()

            if hh >= 12:
                is_pm = True

            hh_12 = hh

            if hh_12 == 0:
                hh_12 = 12
            elif hh_12 > 12:
                hh_12 -= 12

            hh_s = str(hh_12).zfill(2)
            mm_s = str(mm).zfill(2)

            write("F8", hh_s[0], "hora_hora")
            write("G8", hh_s[1], "hora_hora")
            write("I8", mm_s[0], "hora_minuto")
            write("J8", mm_s[1], "hora_minuto")

            clear("L8")
            clear("O8")

            if is_pm:
                write("O8", "X", "hora_pm")
            else:
                write("L8", "X", "hora_am")

    return written

def escribir_observaciones(root, tracker, comp):
    sheet_data = root.find(f"{{{NS_MAIN}}}sheetData")

    if sheet_data is None:
        return []

    written = []
    obs_map = tracker["observaciones"]

    pairs = [
        ("observacionesLevantamiento", obs_map["levantamiento"], comp.get("observacionesLevantamiento")),
        ("observacionesRevisor", obs_map["revisor"], comp.get("observacionesRevisor")),
    ]

    for key, ref, value in pairs:
        if value in [None, ""]:
            continue

        _, rn = split_ref(ref)
        row = get_or_create_row(sheet_data, rn)
        escribir_texto(row, ref, value)
        written.append({"campo": key, "cell": ref, "value": str(value)})

    return written


def escribir_item(root, tracker, row_map, item):
    sheet_data = root.find(f"{{{NS_MAIN}}}sheetData")

    if sheet_data is None:
        return []

    rn = row_map["row"]
    row = get_or_create_row(sheet_data, rn)
    cells = row_map["cells"]
    sev_cols = tracker["severity_cols"]

    written = []

    # Limpia solo la rejilla visible exacta de esa fila.
    for sev, col in sev_cols.items():
        ref = f"{col}{rn}"
        limpiar_contenido(row, ref)
        written.append({"cell": ref, "action": "clear_severity"})

    sev = str(item.get("severidad") or "").strip()

    if sev in sev_cols:
        ref = cells[f"sev{sev}"]
        escribir_texto(row, ref, "x")
        written.append({"cell": ref, "action": "write", "value": "x", "field": "severidad"})

    if item.get("fotos"):
        ref = cells["fotos"]
        escribir_texto(row, ref, item["fotos"])
        written.append({"cell": ref, "action": "write", "value": item["fotos"], "field": "fotos"})

    if item.get("ubicacion"):
        ref = cells["ubicacion"]
        escribir_texto(row, ref, item["ubicacion"])
        written.append({"cell": ref, "action": "write", "value": item["ubicacion"], "field": "ubicacion"})

    return written



def exportar_xlsm_tracked(data, output_path, job_id):
    template = buscar_plantilla()
    validar_xlsm(template)

    tracker = generar_template_tracker()
    comps = payload_componentes(data)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_input = RUNTIME_DIR / f"{output_path.stem}_{job_id}_base.xlsm"
    temp_output = RUNTIME_DIR / f"{output_path.stem}_{job_id}_tracked.xlsm"

    shutil.copy2(template, temp_input)
    validar_xlsm(temp_input)

    set_job(job_id, progress=25, message=f"Plantilla trackeada: {tracker['total_rows']} filas editables")

    report = {
        "job": job_id,
        "template": str(template),
        "output": str(output_path),
        "tracker_rows": tracker["total_rows"],
        "payload_components": len(comps),
        "payload_items": sum(len(c["items"]) for c in comps),
        "written_items": [],
        "missing_items": [],
        "component_sheet_matches": [],
        "identification_written": [],
        "observations_written": [],
        "sheets_touched": [],
        "sheets_identification": [],
        "disabled_features": [
            "Hoja Evaluación desactivada definitivamente para este Excel",
            "Fotos físicas desactivadas definitivamente en Excel",
            "Módulo Fotos queda solo como apoyo visual dentro de la app",
        ],
    }

    sheet_by_path = {sh["path"]: sh for sh in tracker["sheets"]}
    comp_for_sheet = {}

    for comp in comps:
        sh = match_sheet_for_component(comp, tracker)

        if sh:
            comp_for_sheet[sh["path"]] = comp
            report["component_sheet_matches"].append({
                "component": comp["nombre"],
                "sheet": sh["name"],
                "sheet_path": sh["path"],
            })
        elif comp["items"]:
            for item in comp["items"]:
                report["missing_items"].append({
                    "component": comp["nombre"],
                    "codigo": item["codigo"],
                    "reason": "No se encontró hoja para el componente",
                })

    set_job(job_id, progress=40, message="Escribiendo identificación y celdas exactas...")

    with zipfile.ZipFile(temp_input, "r") as zin, zipfile.ZipFile(temp_output, "w", zipfile.ZIP_DEFLATED) as zout:
        names_written = set()

        for info in zin.infolist():
            if info.filename in names_written:
                continue

            names_written.add(info.filename)
            content = zin.read(info.filename)

            if info.filename in sheet_by_path:
                sheet_tracker = sheet_by_path[info.filename]
                comp = comp_for_sheet.get(info.filename)

                root = ET.fromstring(content)

                ident_written = escribir_identificacion_en_root(root, tracker, data)

                if ident_written:
                    report["sheets_identification"].append(sheet_tracker["name"])

                    report["identification_written"].extend(
                        {
                            "sheet": sheet_tracker["name"],
                            **x,
                        }
                        for x in ident_written
                    )

                if comp:
                    report["sheets_touched"].append(sheet_tracker["name"])

                    report["observations_written"].extend(
                        {
                            "sheet": sheet_tracker["name"],
                            **x,
                        }
                        for x in escribir_observaciones(root, tracker, comp)
                    )

                    used_rows = set()

                    for item in comp["items"]:
                        row_map, method = match_row_for_item(item, sheet_tracker, used_rows)

                        if not row_map:
                            report["missing_items"].append({
                                "component": comp["nombre"],
                                "sheet": sheet_tracker["name"],
                                "codigo": item["codigo"],
                                "filaExcel": item.get("filaExcel"),
                                "material_ui": item.get("detalle"),
                                "reason": method,
                            })
                            continue

                        used_rows.add(row_map["row"])

                        writes = escribir_item(root, tracker, row_map, item)

                        report["written_items"].append({
                            "component": comp["nombre"],
                            "sheet": sheet_tracker["name"],
                            "codigo": item["codigo"],
                            "material_template": row_map.get("material"),
                            "row": row_map["row"],
                            "match_method": method,
                            "writes": writes,
                        })

                content = ET.tostring(root, encoding="utf-8", xml_declaration=True)

            zi = zipfile.ZipInfo(info.filename)
            zi.date_time = info.date_time
            zi.compress_type = info.compress_type
            zi.external_attr = info.external_attr

            zout.writestr(zi, content)

    validar_xlsm(temp_output)
    shutil.copy2(temp_output, output_path)
    validar_xlsm(output_path)

    try:
        temp_input.unlink(missing_ok=True)
        temp_output.unlink(missing_ok=True)
    except Exception:
        pass

    return report

def guardar_reporte(output_path, report):
    output_path = Path(output_path)
    report_txt = output_path.with_suffix(".export_report.txt")
    report_json = output_path.with_suffix(".export_report.json")

    lines = []
    lines.append("REPORTE DE EXPORTACIÓN SIPUCOL - V1 TRACKER")
    lines.append("=" * 70)
    lines.append(f"Fecha/hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Excel: {output_path}")
    lines.append(f"Plantilla: {report['template']}")
    lines.append("")
    lines.append("RESUMEN")
    lines.append("-" * 70)
    lines.append(f"Filas editables trackeadas en plantilla: {report['tracker_rows']}")
    lines.append(f"Componentes enviados desde UI: {report['payload_components']}")
    lines.append(f"Filas enviadas desde UI: {report['payload_items']}")
    lines.append(f"Filas escritas en Excel: {len(report['written_items'])}")
    lines.append(f"Filas faltantes: {len(report['missing_items'])}")
    lines.append(f"Celdas verificadas OK: {report.get('cell_validation', {}).get('ok_count', 0)}")
    lines.append(f"Celdas con fallo de verificación: {report.get('cell_validation', {}).get('fail_count', 0)}")
    lines.append("")
    lines.append("HOJAS TOCADAS")
    lines.append("-" * 70)

    for sheet in report["sheets_touched"]:
        lines.append(f"- {sheet}")

    lines.append("")
    lines.append("CELDAS ESCRITAS POR ITEM")
    lines.append("-" * 70)

    for item in report["written_items"]:
        lines.append(f"{item['sheet']} | fila {item['row']} | {item['codigo']} | {item['material_template']} | método {item['match_method']}")

        for w in item["writes"]:
            if w["action"] == "write":
                lines.append(f"  - {w['cell']} = {w.get('value')} ({w.get('field')})")

    lines.append("")
    lines.append("OBSERVACIONES")
    lines.append("-" * 70)

    for obs in report["observations_written"]:
        lines.append(f"{obs['sheet']} | {obs['cell']} = {obs['value']}")

    lines.append("")
    lines.append("IDENTIFICACIÓN")
    lines.append("-" * 70)

    for ident in report["identification_written"]:
        lines.append(f"{ident['sheet']} | {ident['cell']} = {ident['value']}")

    lines.append("")
    lines.append("FALTANTES")
    lines.append("-" * 70)

    if not report["missing_items"]:
        lines.append("Ninguno.")
    else:
        for item in report["missing_items"]:
            lines.append(json.dumps(item, ensure_ascii=False))

    lines.append("")
    lines.append("FUNCIONES DESACTIVADAS EN V1")
    lines.append("-" * 70)

    for f in report["disabled_features"]:
        lines.append(f"- {f}")

    report_txt.write_text("\n".join(lines), encoding="utf-8")
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report_txt, report_json


def run_excel_job(job_id, data, output_path):
    try:
        output_path = Path(output_path)

        log("=" * 70)
        log(f"Job {job_id}: EXPORT V1 TRACKER")
        log(f"Salida elegida: {output_path}")
        log("=" * 70)

        set_job(
            job_id,
            status="running",
            progress=5,
            message=f"Guardará en: {output_path}",
            output_path=str(output_path),
        )

        report = exportar_xlsm_tracked(data, output_path, job_id)

        set_job(job_id, progress=88, message="Verificando celdas escritas...")
        report["cell_validation"] = verificar_celdas_escritas(output_path, report)

        set_job(job_id, progress=92, message="Guardando reporte de celdas...")
        report_txt, report_json = guardar_reporte(output_path, report)

        set_job(
            job_id,
            status="done",
            progress=100,
            message=f"Excel guardado. Filas escritas: {len(report['written_items'])}",
            output_path=str(output_path),
            report_path=str(report_txt),
            report_json_path=str(report_json),
            stats={
                "payload_items": report["payload_items"],
                "written_items": len(report["written_items"]),
                "missing_items": len(report["missing_items"]),
                "tracker_rows": report["tracker_rows"],
            },
        )

        log(f"Job {job_id}: EXCEL LISTO -> {output_path}")
        log(f"Job {job_id}: REPORTE TXT -> {report_txt}")
        log(f"Job {job_id}: REPORTE JSON -> {report_json}")

    except Exception as e:
        set_job(
            job_id,
            status="error",
            progress=0,
            message="Error exportando Excel",
            error=str(e),
        )
        log(f"Job {job_id}: ERROR -> {e}")


@app.get("/api/health")
def health():
    try:
        tracker = generar_template_tracker()
        ok = True
        err = None
    except Exception as e:
        tracker = {}
        ok = False
        err = str(e)

    return {
        "ok": ok,
        "backend": "SIPUCOL Inspector V1 Tracker",
        "template": tracker.get("template"),
        "tracker_rows": tracker.get("total_rows"),
        "tracker_sheets": tracker.get("total_sheets"),
        "error": err,
    }


@app.get("/api/template-map")
def template_map():
    return get_tracker()


@app.post("/api/export/excel-save-dialog")
def export_excel_save_dialog(data: dict):
    base = nombre_base_desde_data(data)

    try:
        output_path = elegir_archivo_guardar_excel(f"{base}.xlsm")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not output_path:
        return {"cancelled": True}

    job_id = uuid.uuid4().hex[:12]

    set_job(
        job_id,
        status="queued",
        progress=0,
        message=f"Ruta elegida: {output_path}",
        output_path=str(output_path),
    )

    thread = threading.Thread(
        target=run_excel_job,
        args=(job_id, copy.deepcopy(data), str(output_path)),
        daemon=True,
    )
    thread.start()

    return {
        "job_id": job_id,
        "output_path": str(output_path),
    }


@app.get("/api/export/job/{job_id}")
def get_export_job(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    return job



# === PROJECT SAVE DIALOG ===

def elegir_archivo_guardar_proyecto(nombre_sugerido):
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update()

    path = filedialog.asksaveasfilename(
        title="Guardar proyecto SIPUCOL",
        defaultextension=".sipucol.json",
        initialfile=nombre_sugerido,
        filetypes=[
            ("Proyecto SIPUCOL", "*.sipucol.json"),
            ("JSON", "*.json"),
            ("Todos los archivos", "*.*"),
        ],
    )

    root.destroy()

    if not path:
        return None

    if not path.lower().endswith(".json"):
        path += ".sipucol.json"

    return Path(path)


@app.post("/api/project/save-dialog")
def save_project_dialog(data: dict):
    base = nombre_base_desde_data(data)
    nombre_sugerido = f"{base}.sipucol.json"

    try:
        output_path = elegir_archivo_guardar_proyecto(nombre_sugerido)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not output_path:
        return {"cancelled": True}

    output_path.parent.mkdir(parents=True, exist_ok=True)

    paquete = copy.deepcopy(data)
    paquete["savedAt"] = datetime.now().isoformat(timespec="seconds")
    paquete["app"] = paquete.get("app") or "SIPUCOL Inspector"
    paquete["type"] = "sipucol-project"

    output_path.write_text(
        json.dumps(paquete, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    log(f"Proyecto guardado -> {output_path}")

    return {
        "ok": True,
        "path": str(output_path),
    }



# === V1 SIN FOTOS EN EXCEL + VALIDACIÓN DE CELDAS ===

def leer_valor_ref_root(root, shared, ref):
    for cell in root.findall(f".//{{{NS_MAIN}}}c"):
        if cell.attrib.get("r") == ref:
            return leer_valor_celda(cell, shared)
    return ""


def verificar_celdas_escritas(output_path, report):
    """
    Después de crear el Excel:
    1. Abre el XLSM final.
    2. Lee cada celda que el reporte dice que escribió.
    3. Confirma valor esperado vs valor real.
    """
    output_path = Path(output_path)

    resultado = {
        "ok_count": 0,
        "fail_count": 0,
        "checked": [],
        "failed": [],
        "note": "Validación post-export. No valida celdas limpiadas, solo escrituras reales.",
    }

    try:
        with zipfile.ZipFile(output_path, "r") as zf:
            shared = leer_shared_strings(zf)
            mapa = sheet_map(zf)
            path_por_hoja = {x["name"]: x["path"] for x in mapa}
            root_cache = {}

            def get_root(sheet_name):
                path = path_por_hoja.get(sheet_name)

                if not path:
                    return None

                if path not in root_cache:
                    root_cache[path] = ET.fromstring(zf.read(path))

                return root_cache[path]

            def check(sheet, cell, expected, source):
                root = get_root(sheet)

                if root is None:
                    item = {
                        "sheet": sheet,
                        "cell": cell,
                        "expected": str(expected),
                        "actual": None,
                        "source": source,
                        "ok": False,
                        "reason": "Hoja no encontrada",
                    }
                    resultado["failed"].append(item)
                    resultado["fail_count"] += 1
                    return

                actual = leer_valor_ref_root(root, shared, cell)

                ok = str(actual) == str(expected)

                item = {
                    "sheet": sheet,
                    "cell": cell,
                    "expected": str(expected),
                    "actual": str(actual),
                    "source": source,
                    "ok": ok,
                }

                resultado["checked"].append(item)

                if ok:
                    resultado["ok_count"] += 1
                else:
                    resultado["fail_count"] += 1
                    resultado["failed"].append(item)

            # Daños / severidades / N. fotos / ubicación.
            for item in report.get("written_items") or []:
                sheet = item.get("sheet")

                for w in item.get("writes") or []:
                    if w.get("action") != "write":
                        continue

                    check(
                        sheet=sheet,
                        cell=w.get("cell"),
                        expected=w.get("value"),
                        source=f"item:{item.get('codigo')}:{w.get('field')}",
                    )

            # Observaciones.
            for obs in report.get("observations_written") or []:
                check(
                    sheet=obs.get("sheet"),
                    cell=obs.get("cell"),
                    expected=obs.get("value"),
                    source=f"observacion:{obs.get('campo')}",
                )

            # Identificación.
            for ident in report.get("identification_written") or []:
                check(
                    sheet=ident.get("sheet"),
                    cell=ident.get("cell"),
                    expected=ident.get("value"),
                    source=f"identificacion:{ident.get('campo')}",
                )

    except Exception as e:
        resultado["fail_count"] += 1
        resultado["failed"].append({
            "reason": f"Error verificando archivo final: {e}",
            "ok": False,
        })

    return resultado

# === SIPUCOL_PDF_EXCEL_COM_V2_START ===

def elegir_archivo_guardar_pdf_v2(
    nombre_sugerido
):

    import tkinter as tk

    from tkinter import filedialog


    root = tk.Tk()

    root.withdraw()

    root.attributes(
        "-topmost",
        True
    )

    root.update()


    path = (
        filedialog
        .asksaveasfilename(

            title=(
                "Guardar PDF oficial "
                "SIPUCOL"
            ),

            defaultextension=".pdf",

            initialfile=nombre_sugerido,

            filetypes=[

                (
                    "Documento PDF",
                    "*.pdf"
                ),

                (
                    "Todos los archivos",
                    "*.*"
                ),
            ],
        )
    )


    root.destroy()


    if not path:

        return None


    if not path.lower().endswith(
        ".pdf"
    ):

        path += ".pdf"


    return Path(
        path
    )



def validar_pdf_final_v2(
    pdf_path
):

    pdf_path = Path(
        pdf_path
    )


    if not pdf_path.exists():

        raise RuntimeError(
            f"No se creó el PDF: {pdf_path}"
        )


    if pdf_path.stat().st_size < 5000:

        raise RuntimeError(
            "El PDF creado está vacío "
            "o es demasiado pequeño."
        )


    with pdf_path.open(
        "rb"
    ) as file:

        header = file.read(
            5
        )


    if header != b"%PDF-":

        raise RuntimeError(
            "El archivo creado no es "
            "un PDF válido."
        )



def exportar_con_excel_a_pdf_v2(
    xlsm_path,
    pdf_path,
    sheet_names,
    job_id
):

    import subprocess


    xlsm_path = Path(
        xlsm_path
    )

    pdf_path = Path(
        pdf_path
    )


    ps1_path = (

        BASE_DIR
        / "backend"
        / "export_excel_to_pdf.ps1"
    )


    if not ps1_path.exists():

        raise RuntimeError(
            "Falta backend/"
            "export_excel_to_pdf.ps1"
        )


    sheets_json = (

        RUNTIME_DIR
        / f"pdf_sheets_{job_id}.json"
    )


    sheets_json.write_text(

        json.dumps(
            sheet_names,
            ensure_ascii=False,
            indent=2
        ),

        encoding="utf-8"
    )


    command = [

        "powershell.exe",

        "-NoProfile",

        "-ExecutionPolicy",
        "Bypass",

        "-File",
        str(
            ps1_path
        ),

        "-WorkbookPath",
        str(
            xlsm_path
        ),

        "-PdfPath",
        str(
            pdf_path
        ),

        "-SheetsJson",
        str(
            sheets_json
        ),
    ]


    log(
        f"Job {job_id}: "
        "abriendo Microsoft Excel "
        "para crear PDF..."
    )


    result = subprocess.run(

        command,

        capture_output=True,

        timeout=360,

        creationflags=(
            0x08000000
        ),
    )


    stdout = (
        result.stdout
        .decode(
            "utf-8",
            errors="replace"
        )
    )


    stderr = (
        result.stderr
        .decode(
            "utf-8",
            errors="replace"
        )
    )


    try:

        sheets_json.unlink(
            missing_ok=True
        )

    except Exception:

        pass


    if stdout.strip():

        log(
            f"Job {job_id}: "
            f"Excel PDF stdout: "
            f"{stdout.strip()}"
        )


    if (
        result.returncode != 0
    ):

        raise RuntimeError(

            "Microsoft Excel no pudo "
            "crear el PDF.\n\n"

            + (
                stderr.strip()
                or stdout.strip()
                or (
                    "Error desconocido "
                    "de automatización."
                )
            )
        )


    validar_pdf_final_v2(
        pdf_path
    )



def hojas_pdf_desde_reporte_v2(
    report
):

    candidates = [

        "ÍNDICE",

        *(
            report.get(
                "sheets_touched"
            )
            or []
        ),

        "CALCULO IC",
    ]


    result = []

    seen = set()


    for name in candidates:

        clean = str(
            name
            or ""
        ).strip()


        key = (
            clean
            .lower()
        )


        if (
            not clean
            or key in seen
        ):

            continue


        seen.add(
            key
        )


        result.append(
            clean
        )


    return result



def guardar_reporte_pdf_v2(
    output_path,
    source_xlsm,
    sheet_names,
    report
):

    output_path = Path(
        output_path
    )


    report_path = (

        output_path
        .with_suffix(
            ".pdf_export_report.txt"
        )
    )


    lines = [

        (
            "REPORTE DE EXPORTACIÓN "
            "PDF SIPUCOL"
        ),

        "=" * 70,

        (
            "Fecha/hora: "
            + datetime.now()
            .strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ),

        (
            "PDF: "
            + str(
                output_path
            )
        ),

        (
            "Excel temporal: "
            + str(
                source_xlsm
            )
        ),

        "",

        "HOJAS EXPORTADAS",

        "-" * 70,
    ]


    for name in sheet_names:

        lines.append(
            f"- {name}"
        )


    lines.extend([

        "",

        "REGLAS",

        "-" * 70,

        (
            "- Se conservan las áreas "
            "de impresión del Excel."
        ),

        (
            "- Se conserva la escala, "
            "orientación y paginación."
        ),

        (
            "- Se excluye Evaluación."
        ),

        (
            "- Se excluyen anexos."
        ),

        (
            "- No se insertan fotos "
            "en el PDF."
        ),

        "",

        "DATOS DEL EXPORTADOR",

        "-" * 70,

        json.dumps(
            {
                "componentes": (
                    report.get(
                        "payload_components"
                    )
                ),

                "filas_ui": (
                    report.get(
                        "payload_items"
                    )
                ),

                "filas_excel": len(
                    report.get(
                        "written_items"
                    )
                    or []
                ),

                "faltantes": len(
                    report.get(
                        "missing_items"
                    )
                    or []
                ),
            },

            ensure_ascii=False,

            indent=2
        ),
    ])


    report_path.write_text(

        "\n".join(
            lines
        ),

        encoding="utf-8"
    )


    return report_path



def run_pdf_job_v2(
    job_id,
    data,
    output_path
):

    temp_xlsm = None


    try:

        output_path = Path(
            output_path
        )


        log(
            "=" * 70
        )


        log(
            f"Job {job_id}: "
            "EXPORT PDF OFICIAL"
        )


        log(
            f"Salida PDF: "
            f"{output_path}"
        )


        log(
            "=" * 70
        )


        set_job(

            job_id,

            status="running",

            progress=5,

            message=(
                "Preparando Excel "
                "temporal..."
            ),

            output_path=str(
                output_path
            ),
        )


        temp_xlsm = (

            RUNTIME_DIR
            / (
                f"pdf_source_"
                f"{job_id}.xlsm"
            )
        )


        set_job(

            job_id,

            progress=15,

            message=(
                "Escribiendo datos "
                "en la plantilla..."
            ),
        )


        report = (
            exportar_xlsm_tracked(

                data,

                temp_xlsm,

                job_id
            )
        )


        sheet_names = (
            hojas_pdf_desde_reporte_v2(
                report
            )
        )


        set_job(

            job_id,

            progress=62,

            message=(
                "Recalculando fórmulas "
                "en Microsoft Excel..."
            ),
        )


        exportar_con_excel_a_pdf_v2(

            temp_xlsm,

            output_path,

            sheet_names,

            job_id
        )


        set_job(

            job_id,

            progress=94,

            message=(
                "Validando PDF final..."
            ),
        )


        validar_pdf_final_v2(
            output_path
        )


        report_path = (
            guardar_reporte_pdf_v2(

                output_path,

                temp_xlsm,

                sheet_names,

                report
            )
        )


        set_job(

            job_id,

            status="done",

            progress=100,

            message=(
                "PDF oficial guardado "
                "correctamente."
            ),

            output_path=str(
                output_path
            ),

            report_path=str(
                report_path
            ),

            sheets=sheet_names,
        )


        log(
            f"Job {job_id}: "
            f"PDF LISTO -> "
            f"{output_path}"
        )


        log(
            f"Job {job_id}: "
            f"REPORTE PDF -> "
            f"{report_path}"
        )


    except Exception as error:

        set_job(

            job_id,

            status="error",

            progress=0,

            message=(
                "Error creando PDF"
            ),

            error=str(
                error
            ),
        )


        log(
            f"Job {job_id}: "
            f"ERROR PDF -> "
            f"{error}"
        )


    finally:

        if temp_xlsm:

            try:

                Path(
                    temp_xlsm
                ).unlink(
                    missing_ok=True
                )

            except Exception:

                pass



@app.post(
    "/api/export/"
    "pdf-save-dialog-v2"
)
def export_pdf_save_dialog_v2(
    data: dict
):

    base = (
        nombre_base_desde_data(
            data
        )
    )


    try:

        output_path = (
            elegir_archivo_guardar_pdf_v2(

                f"{base}.pdf"
            )
        )

    except Exception as error:

        raise HTTPException(

            status_code=500,

            detail=str(
                error
            )
        )


    if not output_path:

        return {
            "cancelled": True
        }


    job_id = (
        uuid.uuid4()
        .hex[:12]
    )


    set_job(

        job_id,

        status="queued",

        progress=0,

        message=(
            "PDF en cola."
        ),

        output_path=str(
            output_path
        ),
    )


    thread = threading.Thread(

        target=run_pdf_job_v2,

        args=(

            job_id,

            copy.deepcopy(
                data
            ),

            str(
                output_path
            ),
        ),

        daemon=True,
    )


    thread.start()


    return {

        "job_id": job_id,

        "output_path": str(
            output_path
        ),
    }

# === SIPUCOL_PDF_EXCEL_COM_V2_END ===

# === PDF_FROM_SELECTED_EXCEL_START ===

def seleccionar_excel_y_destino_pdf():

    import tkinter as tk

    from tkinter import filedialog


    root = tk.Tk()

    root.withdraw()

    root.attributes(
        "-topmost",
        True
    )

    root.update()


    excel_path = (
        filedialog
        .askopenfilename(

            title=(
                "Selecciona el Excel "
                "que deseas convertir"
            ),

            filetypes=[

                (
                    "Archivos de Excel",
                    (
                        "*.xlsm "
                        "*.xlsx "
                        "*.xls "
                        "*.xlsb"
                    )
                ),

                (
                    "Excel con macros",
                    "*.xlsm"
                ),

                (
                    "Excel normal",
                    "*.xlsx"
                ),

                (
                    "Todos los archivos",
                    "*.*"
                ),
            ],
        )
    )


    if not excel_path:

        root.destroy()

        return None, None


    source = Path(
        excel_path
    )


    pdf_path = (
        filedialog
        .asksaveasfilename(

            title=(
                "Guardar PDF convertido"
            ),

            defaultextension=".pdf",

            initialfile=(
                source.stem
                + ".pdf"
            ),

            filetypes=[

                (
                    "Documento PDF",
                    "*.pdf"
                ),

                (
                    "Todos los archivos",
                    "*.*"
                ),
            ],
        )
    )


    root.destroy()


    if not pdf_path:

        return None, None


    if not pdf_path.lower().endswith(
        ".pdf"
    ):

        pdf_path += ".pdf"


    return (
        source,
        Path(
            pdf_path
        )
    )



def validar_pdf_seleccionado(
    pdf_path
):

    pdf_path = Path(
        pdf_path
    )


    if not pdf_path.exists():

        raise RuntimeError(
            "Microsoft Excel no creó "
            "el archivo PDF."
        )


    if pdf_path.stat().st_size < 5000:

        raise RuntimeError(
            "El PDF quedó vacío "
            "o incompleto."
        )


    with pdf_path.open(
        "rb"
    ) as file:

        header = file.read(
            5
        )


    if header != b"%PDF-":

        raise RuntimeError(
            "El archivo generado "
            "no es un PDF válido."
        )



def convertir_excel_seleccionado_job(
    job_id,
    excel_path,
    pdf_path
):

    import subprocess


    try:

        excel_path = Path(
            excel_path
        )


        pdf_path = Path(
            pdf_path
        )


        log(
            "=" * 70
        )


        log(
            f"Job {job_id}: "
            "PDF DESDE EXCEL SELECCIONADO"
        )


        log(
            f"Excel origen: "
            f"{excel_path}"
        )


        log(
            f"PDF destino: "
            f"{pdf_path}"
        )


        log(
            "=" * 70
        )


        set_job(

            job_id,

            status="running",

            progress=10,

            message=(
                "Abriendo Microsoft Excel..."
            ),

            source_excel=str(
                excel_path
            ),

            output_path=str(
                pdf_path
            ),
        )


        script_path = (

            BASE_DIR
            / "backend"
            / (
                "convert_selected_"
                "excel_to_pdf.ps1"
            )
        )


        if not script_path.exists():

            raise RuntimeError(

                "No existe el conversor "
                "de Excel a PDF."
            )


        set_job(

            job_id,

            progress=30,

            message=(
                "Convirtiendo el Excel "
                "seleccionado..."
            ),
        )


        command = [

            "powershell.exe",

            "-NoProfile",

            "-ExecutionPolicy",
            "Bypass",

            "-File",
            str(
                script_path
            ),

            "-ExcelPath",
            str(
                excel_path
            ),

            "-PdfPath",
            str(
                pdf_path
            ),
        ]


        process = subprocess.run(

            command,

            capture_output=True,

            timeout=600,

            creationflags=(
                0x08000000
            ),
        )


        stdout = (
            process.stdout
            .decode(
                "utf-8",
                errors="replace"
            )
        )


        stderr = (
            process.stderr
            .decode(
                "utf-8",
                errors="replace"
            )
        )


        if stdout.strip():

            log(

                f"Job {job_id}: "
                f"{stdout.strip()}"
            )


        if (
            process.returncode
            != 0
        ):

            raise RuntimeError(

                stderr.strip()

                or stdout.strip()

                or (
                    "Microsoft Excel "
                    "no pudo crear el PDF."
                )
            )


        set_job(

            job_id,

            progress=90,

            message=(
                "Validando PDF..."
            ),
        )


        validar_pdf_seleccionado(
            pdf_path
        )


        report_path = (

            pdf_path
            .with_suffix(
                ".conversion_report.txt"
            )
        )


        report_path.write_text(

            "\n".join([

                (
                    "REPORTE DE CONVERSIÓN "
                    "EXCEL A PDF"
                ),

                "=" * 70,

                (
                    "Fecha: "
                    + datetime.now()
                    .strftime(
                        "%Y-%m-%d "
                        "%H:%M:%S"
                    )
                ),

                "",

                (
                    "Excel origen:"
                ),

                str(
                    excel_path
                ),

                "",

                (
                    "PDF creado:"
                ),

                str(
                    pdf_path
                ),

                "",

                (
                    "Tamaño:"
                ),

                str(
                    pdf_path
                    .stat()
                    .st_size
                ),

                "",

                (
                    "Método:"
                ),

                (
                    "Microsoft Excel "
                    "ExportAsFixedFormat"
                ),

                "",

                (
                    "Se respetaron las "
                    "áreas de impresión, "
                    "escalas, márgenes, "
                    "saltos de página y "
                    "hojas visibles "
                    "del Excel seleccionado."
                ),
            ]),

            encoding="utf-8"
        )


        set_job(

            job_id,

            status="done",

            progress=100,

            message=(
                "PDF creado directamente "
                "desde el Excel."
            ),

            source_excel=str(
                excel_path
            ),

            output_path=str(
                pdf_path
            ),

            report_path=str(
                report_path
            ),
        )


        log(
            f"Job {job_id}: "
            f"PDF LISTO -> "
            f"{pdf_path}"
        )


    except Exception as error:

        set_job(

            job_id,

            status="error",

            progress=0,

            message=(
                "Error convirtiendo "
                "el Excel a PDF"
            ),

            error=str(
                error
            ),
        )


        log(

            f"Job {job_id}: "
            f"ERROR PDF -> "
            f"{error}"
        )



@app.post(
    "/api/export/"
    "pdf-from-selected-excel"
)
def pdf_from_selected_excel():

    try:

        excel_path, pdf_path = (
            seleccionar_excel_y_destino_pdf()
        )

    except Exception as error:

        raise HTTPException(

            status_code=500,

            detail=str(
                error
            )
        )


    if (
        not excel_path
        or
        not pdf_path
    ):

        return {

            "cancelled":
                True
        }


    job_id = (

        uuid.uuid4()
        .hex[:12]
    )


    set_job(

        job_id,

        status="queued",

        progress=0,

        message=(
            "Conversión en cola."
        ),

        source_excel=str(
            excel_path
        ),

        output_path=str(
            pdf_path
        ),
    )


    thread = threading.Thread(

        target=(
            convertir_excel_seleccionado_job
        ),

        args=(

            job_id,

            str(
                excel_path
            ),

            str(
                pdf_path
            ),
        ),

        daemon=True,
    )


    thread.start()


    return {

        "job_id":
            job_id,

        "source_excel":
            str(
                excel_path
            ),

        "output_path":
            str(
                pdf_path
            ),
    }

# === PDF_FROM_SELECTED_EXCEL_END ===

# === SIPUCOL_VBS_PDF_BINDING_START ===

# Motor definitivo para:
# Excel seleccionado -> PDF.
#
# El conversor PowerShell antiguo
# queda completamente fuera del flujo.

from backend.pdf_vbs_worker import (
    convertir_excel_seleccionado_job
    as _sipucol_pdf_vbs_job
)

convertir_excel_seleccionado_job = (
    _sipucol_pdf_vbs_job
)

# === SIPUCOL_VBS_PDF_BINDING_END ===

# === SIPUCOL_LIBREOFFICE_PDF_FINAL_START ===

# Motor PDF definitivo.
#
# Reemplaza todos los motores antiguos:
#
# - Excel COM
# - Workbooks.Open
# - VBScript
# - PowerShell de automatización

from backend.pdf_libreoffice_worker import (

    convertir_excel_seleccionado_job

    as _sipucol_pdf_libreoffice_job
)


convertir_excel_seleccionado_job = (

    _sipucol_pdf_libreoffice_job
)

# === SIPUCOL_LIBREOFFICE_PDF_FINAL_END ===

# === SIPUCOL_LIBREOFFICE_PDF_LAYOUT_V2_START ===

# Motor PDF estable con maquetación fina:
#
# - Componentes e índice:
#   una sola página.
#
# - Cálculos y anexos:
#   una página de ancho.
#
# - Sin páginas angostas
#   causadas por desborde.

from backend.pdf_libreoffice_worker import (

    convertir_excel_seleccionado_job

    as _sipucol_pdf_layout_v2_job
)


convertir_excel_seleccionado_job = (

    _sipucol_pdf_layout_v2_job
)

# === SIPUCOL_LIBREOFFICE_PDF_LAYOUT_V2_END ===

# === SIPUCOL_FILTERED_LIBREOFFICE_PDF_START ===

# Filtro definitivo:
#
# Excel seleccionado
# -> detectar componentes diligenciados
# -> ocultar Índice, anexos y componentes vacíos
# -> conservar CALCULO IC
# -> motor LibreOffice estable.

from backend.pdf_filtered_libreoffice_worker import (
    convertir_excel_seleccionado_job
    as _sipucol_pdf_filtered_libreoffice_job
)

convertir_excel_seleccionado_job = (
    _sipucol_pdf_filtered_libreoffice_job
)

# === SIPUCOL_FILTERED_LIBREOFFICE_PDF_END ===

# === SIPUCOL_PDF_FINAL_PAGE_FILTER_START ===

# Motor final:
#
# LibreOffice estable
# -> PDF completo
# -> eliminación física de páginas vacías
# -> componentes diligenciados
# -> Índice de Condición al final.

from backend.pdf_final_page_filter_worker import (
    convertir_excel_seleccionado_job
    as _sipucol_pdf_final_page_filter_job
)

convertir_excel_seleccionado_job = (
    _sipucol_pdf_final_page_filter_job
)

# === SIPUCOL_PDF_FINAL_PAGE_FILTER_END ===

# === SIPUCOL_PDF_CLEAN_FINAL_OVERRIDE_START ===

# Capa final aislada:
#
# - conserva el filtrado funcional actual;
# - elimina índice y catálogo;
# - conserva una única página completa de CALCULO IC;
# - no recorta ni divide páginas.

from backend.pdf_clean_final_override import (
    convertir_excel_seleccionado_job
    as _sipucol_pdf_clean_final_job
)

convertir_excel_seleccionado_job = (
    _sipucol_pdf_clean_final_job
)

# === SIPUCOL_PDF_CLEAN_FINAL_OVERRIDE_END ===
