from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path.cwd().resolve()

WORKER = (
    ROOT
    / "backend"
    / "pdf_final_page_filter_worker.py"
)

BACKUPS = ROOT / "backups"

STAMP = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

IGNORED_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "backups",
    "__pycache__",
    ".venv",
    "venv",
    ".sipucol_runtime",
}

LAYOUT_START = (
    "# === SIPUCOL_CALCULO_IC_LAYOUT_START ==="
)

LAYOUT_END = (
    "# === SIPUCOL_CALCULO_IC_LAYOUT_END ==="
)

BACKUPS.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# VALIDACIÓN
# ============================================================

if not WORKER.exists():

    raise SystemExit(
        "ERROR: no encontré "
        "backend/pdf_final_page_filter_worker.py"
    )


# ============================================================
# BACKUP COMPLETO
# ============================================================

def create_backup(
    label: str,
) -> Path:

    destination = (
        BACKUPS
        / f"{label}_{STAMP}.zip"
    )

    with zipfile.ZipFile(
        destination,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:

        for path in ROOT.rglob("*"):

            if not path.is_file():
                continue

            relative = path.relative_to(
                ROOT
            )

            if any(
                part in IGNORED_DIRS
                for part in relative.parts
            ):
                continue

            if path.suffix.lower() in {
                ".pyc",
                ".log",
            }:
                continue

            archive.write(
                path,
                relative,
            )

    return destination


backup_before = create_backup(
    "SIPUCOL_BASE_CANONICA_ANTES_ARREGLAR_SOLO_CALCULO_IC"
)


print()
print("=" * 72)
print("BACKUP CANÓNICO CREADO")
print("=" * 72)
print(backup_before)


worker_original = WORKER.read_bytes()


# ============================================================
# AYUDANTES DE PARCHE
# ============================================================

def read_text(
    path: Path,
) -> str:

    return path.read_text(
        encoding="utf-8-sig",
        errors="strict",
    ).replace(
        "\r\n",
        "\n",
    )


def find_function_range(
    source: str,
    function_name: str,
) -> tuple[int, int]:

    matches = list(
        re.finditer(
            rf"(?m)^def\s+"
            rf"{re.escape(function_name)}"
            rf"\s*\(",
            source,
        )
    )

    if not matches:

        raise RuntimeError(
            f"No encontré la función {function_name}."
        )

    start = matches[-1].start()

    next_function = re.search(
        r"(?m)^def\s+"
        r"[A-Za-z_][A-Za-z0-9_]*"
        r"\s*\(",
        source[
            matches[-1].end():
        ],
    )

    if next_function:

        end = (
            matches[-1].end()
            + next_function.start()
        )

    else:

        end = len(
            source
        )

    return start, end


def replace_function(
    source: str,
    function_name: str,
    replacement: str,
) -> str:

    start, end = find_function_range(
        source,
        function_name,
    )

    return (
        source[:start]
        + replacement.rstrip()
        + "\n\n"
        + source[end:].lstrip()
    )


# ============================================================
# PREPARADOR EXCLUSIVO DE CALCULO IC
# ============================================================

layout_helper = r'''def _prepare_calculo_ic_layout(
    source: Path,
    destination: Path,
) -> dict:
    """
    Crea una copia temporal del Excel y modifica únicamente
    la configuración de impresión de CALCULO IC.

    Configuración:
    - una página de ancho;
    - altura automática;
    - orientación horizontal;
    - sin comprimir toda la hoja en una sola página.

    No altera datos, fórmulas, macros ni las demás hojas.
    """

    import zipfile
    from xml.etree import ElementTree as ET


    main_namespace = (
        "http://schemas.openxmlformats.org/"
        "spreadsheetml/2006/main"
    )

    document_relationship_namespace = (
        "http://schemas.openxmlformats.org/"
        "officeDocument/2006/relationships"
    )

    package_relationship_namespace = (
        "http://schemas.openxmlformats.org/"
        "package/2006/relationships"
    )


    ET.register_namespace(
        "",
        main_namespace,
    )

    ET.register_namespace(
        "r",
        document_relationship_namespace,
    )


    main = (
        "{"
        + main_namespace
        + "}"
    )

    relationship_attribute = (
        "{"
        + document_relationship_namespace
        + "}id"
    )


    with zipfile.ZipFile(
        source,
        "r",
    ) as input_archive:

        workbook_root = ET.fromstring(
            input_archive.read(
                "xl/workbook.xml"
            )
        )

        relationships_root = ET.fromstring(
            input_archive.read(
                "xl/_rels/workbook.xml.rels"
            )
        )


        relationship_map = {}

        for relationship in relationships_root:

            relation_id = str(
                relationship.attrib.get(
                    "Id"
                )
                or ""
            )

            target = str(
                relationship.attrib.get(
                    "Target"
                )
                or ""
            )

            if relation_id:

                relationship_map[
                    relation_id
                ] = target


        sheets_node = workbook_root.find(
            main + "sheets"
        )

        if sheets_node is None:

            raise RuntimeError(
                "El Excel no contiene una lista de hojas."
            )


        calculation_sheet = None
        calculation_path = None


        for sheet in sheets_node:

            sheet_name = str(
                sheet.attrib.get(
                    "name"
                )
                or ""
            ).strip()


            if not _is_calculo_ic(
                sheet_name
            ):

                continue


            relationship_id = str(
                sheet.attrib.get(
                    relationship_attribute
                )
                or ""
            )


            target = relationship_map.get(
                relationship_id,
                "",
            ).replace(
                "\\",
                "/",
            )


            if not target:

                continue


            if target.startswith(
                "/"
            ):

                worksheet_path = target.lstrip(
                    "/"
                )

            elif target.startswith(
                "xl/"
            ):

                worksheet_path = target

            else:

                worksheet_path = (
                    "xl/"
                    + target
                )


            calculation_sheet = sheet_name
            calculation_path = worksheet_path

            break


        if (
            not calculation_sheet
            or not calculation_path
        ):

            raise RuntimeError(
                "No encontré la hoja CALCULO IC."
            )


        if calculation_path not in input_archive.namelist():

            raise RuntimeError(
                "No encontré el XML interno de CALCULO IC: "
                + calculation_path
            )


        worksheet_root = ET.fromstring(
            input_archive.read(
                calculation_path
            )
        )


        # ====================================================
        # ACTIVAR AJUSTE A PÁGINAS
        # ====================================================

        sheet_properties = worksheet_root.find(
            main + "sheetPr"
        )


        if sheet_properties is None:

            sheet_properties = ET.Element(
                main + "sheetPr"
            )

            worksheet_root.insert(
                0,
                sheet_properties,
            )


        page_setup_properties = (
            sheet_properties.find(
                main + "pageSetUpPr"
            )
        )


        if page_setup_properties is None:

            page_setup_properties = ET.SubElement(
                sheet_properties,
                main + "pageSetUpPr",
            )


        page_setup_properties.set(
            "fitToPage",
            "1",
        )

        page_setup_properties.set(
            "autoPageBreaks",
            "1",
        )


        # ====================================================
        # UNA PÁGINA DE ANCHO, ALTURA AUTOMÁTICA
        # ====================================================

        page_setup = worksheet_root.find(
            main + "pageSetup"
        )


        if page_setup is None:

            page_setup = ET.Element(
                main + "pageSetup"
            )


            insertion_index = len(
                worksheet_root
            )


            preferred_following_tags = {
                main + "headerFooter",
                main + "rowBreaks",
                main + "colBreaks",
                main + "drawing",
                main + "legacyDrawing",
                main + "picture",
                main + "tableParts",
                main + "extLst",
            }


            for index, child in enumerate(
                list(
                    worksheet_root
                )
            ):

                if child.tag in preferred_following_tags:

                    insertion_index = index
                    break


            worksheet_root.insert(
                insertion_index,
                page_setup,
            )


        # scale entra en conflicto con fitToPage.
        page_setup.attrib.pop(
            "scale",
            None,
        )


        page_setup.set(
            "fitToWidth",
            "1",
        )

        # 0 significa cantidad automática de páginas verticales.
        page_setup.set(
            "fitToHeight",
            "0",
        )

        page_setup.set(
            "orientation",
            "landscape",
        )


        # ====================================================
        # EVITAR CENTRADO VERTICAL DE TODA LA HOJA
        # ====================================================

        print_options = worksheet_root.find(
            main + "printOptions"
        )


        if print_options is None:

            print_options = ET.Element(
                main + "printOptions"
            )


            page_margins = worksheet_root.find(
                main + "pageMargins"
            )


            if page_margins is not None:

                margin_index = list(
                    worksheet_root
                ).index(
                    page_margins
                )

                worksheet_root.insert(
                    margin_index,
                    print_options,
                )

            else:

                worksheet_root.append(
                    print_options
                )


        print_options.set(
            "horizontalCentered",
            "1",
        )

        print_options.set(
            "verticalCentered",
            "0",
        )


        worksheet_bytes = ET.tostring(
            worksheet_root,
            encoding="utf-8",
            xml_declaration=True,
        )


        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )


        with zipfile.ZipFile(
            destination,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as output_archive:

            for information in input_archive.infolist():

                content = input_archive.read(
                    information.filename
                )


                if information.filename == calculation_path:

                    content = worksheet_bytes


                output_archive.writestr(
                    information,
                    content,
                )


    if (
        not destination.exists()
        or destination.stat().st_size
        < 1000
    ):

        raise RuntimeError(
            "La copia preparada para CALCULO IC "
            "quedó vacía."
        )


    return {
        "sheet":
            calculation_sheet,

        "path":
            calculation_path,

        "fit_to_width":
            1,

        "fit_to_height":
            0,

        "orientation":
            "landscape",
    }
'''


# ============================================================
# DETECTOR DE TODAS LAS PÁGINAS DE CALCULO IC
# ============================================================

condition_detector = r'''def _is_condition_index_page(
    normalized_text: str,
) -> bool:
    """
    Reconoce todas las páginas verticales pertenecientes
    a CALCULO IC.

    Se mantiene completamente separado del reconocimiento
    de páginas de componentes.
    """

    if not normalized_text:

        return False


    strong_markers = [
        "indicedecondiciondescripciondelestadodelpuente",
        "indicedecondiciondelpuente",
        "calificacionponderadadelpuente",
        "calificacionponderadadelgrupo",
        "calificacionponderadadelcomponente",
        "indicacionesconsideraciones",
    ]


    if any(
        marker in normalized_text
        for marker in strong_markers
    ):

        return True


    layout_markers = [
        "ponderadosporareadeevaluacion",
        "ponderadosporcomponentes",
        "ponderadosporgrupo",
        "seleccionarcategoriadelavia",
        "elegircaso",
        "caso1",
        "caso2",
        "caso3",
        "caso4",
    ]


    marker_count = sum(
        1
        for marker in layout_markers
        if marker in normalized_text
    )


    # Exige varias señales simultáneas para no confundir
    # anexos o páginas que mencionen una sola frase.
    return marker_count >= 2
'''


try:

    worker_code = read_text(
        WORKER
    )


    # ========================================================
    # INSTALAR/ACTUALIZAR EL PREPARADOR
    # ========================================================

    if re.search(
        r"(?m)^def\s+_prepare_calculo_ic_layout\s*\(",
        worker_code,
    ):

        worker_code = replace_function(
            worker_code,
            "_prepare_calculo_ic_layout",
            layout_helper,
        )

    else:

        converter_position = worker_code.find(
            "def convertir_excel_seleccionado_job"
        )


        if converter_position < 0:

            raise RuntimeError(
                "No encontré convertir_excel_seleccionado_job."
            )


        worker_code = (
            worker_code[:converter_position]
            + layout_helper.rstrip()
            + "\n\n"
            + worker_code[converter_position:]
        )


    # ========================================================
    # ACTUALIZAR SOLO DETECTOR DEL CALCULO IC
    # ========================================================

    worker_code = replace_function(
        worker_code,
        "_is_condition_index_page",
        condition_detector,
    )


    # ========================================================
    # HACER QUE LIBREOFFICE RECIBA LA COPIA PREPARADA
    # ========================================================

    previous_layout_pattern = re.compile(
        re.escape(
            LAYOUT_START
        )
        + r"[\s\S]*?"
        + re.escape(
            LAYOUT_END
        ),
    )


    if previous_layout_pattern.search(
        worker_code
    ):

        existing = previous_layout_pattern.search(
            worker_code
        )

        indentation_match = re.search(
            r"(?m)^(?P<indent>[ \t]*)"
            + re.escape(
                LAYOUT_START
            ),
            worker_code[
                :existing.start()
            ]
            + worker_code[
                existing.start():
                existing.end()
            ],
        )

        indentation = (
            indentation_match.group(
                "indent"
            )
            if indentation_match
            else "        "
        )


        replacement_lines = [
            indentation + LAYOUT_START,
            "",
            indentation + "prepared_excel = (",
            indentation + "    temporary_directory",
            indentation + "    / (",
            indentation + '        "SIPUCOL_CALCULO_IC_AUTO"',
            indentation + "        + source.suffix",
            indentation + "    )",
            indentation + ")",
            "",
            indentation + "layout_information = (",
            indentation + "    _prepare_calculo_ic_layout(",
            indentation + "        source,",
            indentation + "        prepared_excel,",
            indentation + "    )",
            indentation + ")",
            "",
            indentation + "server.log(",
            indentation + '    f"Job {job_id}: "',
            indentation + '    "CALCULO IC -> 1 página de ancho, "',
            indentation + '    "altura automática"',
            indentation + ")",
            "",
            indentation + "stable_worker.convertir_excel_seleccionado_job(",
            indentation + "    child_job_id,",
            indentation + "    str(",
            indentation + "        prepared_excel",
            indentation + "    ),",
            indentation + "    str(",
            indentation + "        full_pdf",
            indentation + "    ),",
            indentation + ")",
            "",
            indentation + LAYOUT_END,
        ]


        worker_code = previous_layout_pattern.sub(
            "\n".join(
                replacement_lines
            ),
            worker_code,
            count=1,
        )

    else:

        stable_call_pattern = re.compile(
            r'''(?ms)
            ^(?P<indent>[ \t]*)
            stable_worker
            \.
            convertir_excel_seleccionado_job
            \(
            \s*
            child_job_id
            \s*,
            \s*
            str
            \(
            \s*
            (?:
                source
                |
                prepared_excel
            )
            \s*
            \)
            \s*,
            \s*
            str
            \(
            \s*
            full_pdf
            \s*
            \)
            \s*,
            \s*
            \)
            ''',
            flags=re.VERBOSE,
        )


        stable_match = stable_call_pattern.search(
            worker_code
        )


        if not stable_match:

            raise RuntimeError(
                "No encontré la llamada al motor "
                "LibreOffice estable."
            )


        indentation = stable_match.group(
            "indent"
        )


        replacement_lines = [
            indentation + LAYOUT_START,
            "",
            indentation + "prepared_excel = (",
            indentation + "    temporary_directory",
            indentation + "    / (",
            indentation + '        "SIPUCOL_CALCULO_IC_AUTO"',
            indentation + "        + source.suffix",
            indentation + "    )",
            indentation + ")",
            "",
            indentation + "layout_information = (",
            indentation + "    _prepare_calculo_ic_layout(",
            indentation + "        source,",
            indentation + "        prepared_excel,",
            indentation + "    )",
            indentation + ")",
            "",
            indentation + "server.log(",
            indentation + '    f"Job {job_id}: "',
            indentation + '    "CALCULO IC -> 1 página de ancho, "',
            indentation + '    "altura automática"',
            indentation + ")",
            "",
            indentation + "stable_worker.convertir_excel_seleccionado_job(",
            indentation + "    child_job_id,",
            indentation + "    str(",
            indentation + "        prepared_excel",
            indentation + "    ),",
            indentation + "    str(",
            indentation + "        full_pdf",
            indentation + "    ),",
            indentation + ")",
            "",
            indentation + LAYOUT_END,
        ]


        worker_code = (
            worker_code[:stable_match.start()]
            + "\n".join(
                replacement_lines
            )
            + worker_code[stable_match.end():]
        )


    WORKER.write_text(
        worker_code,
        encoding="utf-8",
        newline="\n",
    )


    # ========================================================
    # VALIDAR SINTAXIS
    # ========================================================

    print()
    print("Validando módulo PDF...")


    compile_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(
                WORKER
            ),
        ],
        cwd=str(
            ROOT
        ),
        capture_output=True,
        text=True,
        timeout=120,
    )


    if compile_result.returncode != 0:

        raise RuntimeError(
            compile_result.stderr
            or compile_result.stdout
        )


    print(
        "Sintaxis correcta."
    )


    # ========================================================
    # CONFIRMAR MOTOR ACTIVO
    # ========================================================

    active_result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from backend import server; "
                "f=server.convertir_excel_seleccionado_job; "
                "print('MODULO_ACTIVO=' + f.__module__); "
                "assert f.__module__ == "
                "'backend.pdf_final_page_filter_worker'"
            ),
        ],
        cwd=str(
            ROOT
        ),
        capture_output=True,
        text=True,
        timeout=120,
    )


    print(
        active_result.stdout
    )


    if active_result.returncode != 0:

        raise RuntimeError(
            active_result.stderr
            or active_result.stdout
        )


    # ========================================================
    # PRUEBA DEL XML SOBRE EL EXCEL MÁS RECIENTE
    # ========================================================

    test_result = subprocess.run(
        [
            sys.executable,
            "-c",
            r'''
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from backend import server
from backend import pdf_final_page_filter_worker as worker


downloads = (
    Path.home()
    / "Downloads"
)


candidates = sorted(
    [
        *downloads.glob(
            "INSPECCION_SIPUCOL*.xlsm"
        ),
        *downloads.glob(
            "INSPECCION_SIPUCOL*.xlsx"
        ),
    ],
    key=lambda path: path.stat().st_mtime,
    reverse=True,
)


source = (
    candidates[0]
    if candidates
    else Path(
        server.buscar_plantilla()
    )
)


with tempfile.TemporaryDirectory(
    prefix="sipucol_test_calculo_ic_"
) as directory:

    destination = (
        Path(directory)
        / (
            "prueba"
            + source.suffix
        )
    )


    information = (
        worker._prepare_calculo_ic_layout(
            source,
            destination,
        )
    )


    main_namespace = (
        "http://schemas.openxmlformats.org/"
        "spreadsheetml/2006/main"
    )


    with zipfile.ZipFile(
        destination,
        "r",
    ) as archive:

        root = ET.fromstring(
            archive.read(
                information[
                    "path"
                ]
            )
        )


    page_setup = root.find(
        "{"
        + main_namespace
        + "}pageSetup"
    )


    if page_setup is None:

        raise RuntimeError(
            "No quedó pageSetup."
        )


    if page_setup.attrib.get(
        "fitToWidth"
    ) != "1":

        raise RuntimeError(
            "CALCULO IC no quedó "
            "a una página de ancho."
        )


    if page_setup.attrib.get(
        "fitToHeight"
    ) != "0":

        raise RuntimeError(
            "CALCULO IC no quedó "
            "con altura automática."
        )


    if "scale" in page_setup.attrib:

        raise RuntimeError(
            "Persistió el escalado que "
            "comprime toda la hoja."
        )


    print(
        "HOJA_CALCULO_IC="
        + information[
            "sheet"
        ]
    )

    print(
        "FIT_TO_WIDTH=1"
    )

    print(
        "FIT_TO_HEIGHT=0"
    )

    print(
        "ESCALA_FORZADA_ELIMINADA=OK"
    )

    print(
        "ALTURA_AUTOMATICA=OK"
    )
''',
        ],
        cwd=str(
            ROOT
        ),
        capture_output=True,
        text=True,
        timeout=180,
    )


    print(
        test_result.stdout
    )


    if test_result.returncode != 0:

        raise RuntimeError(
            test_result.stderr
            or test_result.stdout
        )


    # ========================================================
    # PRUEBA DEL DETECTOR DE PÁGINAS
    # ========================================================

    detector_result = subprocess.run(
        [
            sys.executable,
            "-c",
            r'''
from backend import (
    pdf_final_page_filter_worker
    as worker
)


component_text = worker._normalize(
    """
    1. IDENTIFICACION / LOCALIZACION
    2. REGISTROS DE DANOS
    Componente: Superficie del tablero
    Area Durabilidad
    """
)


calculation_top = worker._normalize(
    """
    INDICACIONES CONSIDERACIONES
    PONDERADOS POR AREA DE EVALUACION
    PONDERADOS POR COMPONENTES
    ELEGIR CASO
    """
)


calculation_bottom = worker._normalize(
    """
    CALIFICACION PONDERADA DEL PUENTE
    INDICE DE CONDICION
    DESCRIPCION DEL ESTADO DEL PUENTE
    """
)


if worker._is_condition_index_page(
    component_text
):

    raise RuntimeError(
        "Una página de componente se confundió "
        "con CALCULO IC."
    )


if not worker._is_condition_index_page(
    calculation_top
):

    raise RuntimeError(
        "No se reconoció la parte superior "
        "de CALCULO IC."
    )


if not worker._is_condition_index_page(
    calculation_bottom
):

    raise RuntimeError(
        "No se reconoció la parte final "
        "de CALCULO IC."
    )


print(
    "COMPONENTES_NO_MODIFICADOS=OK"
)

print(
    "PAGINAS_CALCULO_IC_RECONOCIDAS=OK"
)
''',
        ],
        cwd=str(
            ROOT
        ),
        capture_output=True,
        text=True,
        timeout=120,
    )


    print(
        detector_result.stdout
    )


    if detector_result.returncode != 0:

        raise RuntimeError(
            detector_result.stderr
            or detector_result.stdout
        )


except Exception as error:

    WORKER.write_bytes(
        worker_original
    )

    print()
    print("=" * 72)
    print("ERROR — WORKER RESTAURADO AUTOMÁTICAMENTE")
    print("=" * 72)
    print(error)

    raise SystemExit(1)


# ============================================================
# LIMPIAR CACHÉ PYTHON
# ============================================================

for cache in (
    ROOT
    / "backend"
).rglob(
    "__pycache__"
):

    shutil.rmtree(
        cache,
        ignore_errors=True,
    )


# ============================================================
# BACKUP FINAL
# ============================================================

backup_after = create_backup(
    "SIPUCOL_BASE_CANONICA_CALCULO_IC_ALTURA_AUTOMATICA"
)


checkpoint = (
    ROOT
    / (
        "CHECKPOINT_CALCULO_IC_ALTURA_AUTOMATICA_"
        + STAMP
        + ".txt"
    )
)


checkpoint.write_text(
    "\n".join([
        "SIPUCOL — NUEVA BASE CANÓNICA",
        "=" * 72,
        "",
        f"Fecha: {datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        "Único cambio:",
        "- CALCULO IC a una página de ancho.",
        "- Altura automática.",
        "- Puede ocupar varias páginas verticales.",
        "- Sin compresión total en una sola página.",
        "",
        "No modificado:",
        "- Filtrado de componentes.",
        "- Exclusión del índice inicial.",
        "- Exclusión del catálogo.",
        "- Detección de tablas diligenciadas.",
        "- Página de Superficie del tablero.",
        "- Excel original.",
        "- Interfaz.",
        "- Calidad vectorial del PDF.",
        "",
        "Backup anterior:",
        str(
            backup_before
        ),
        "",
        "Backup final:",
        str(
            backup_after
        ),
    ]),
    encoding="utf-8",
)


print()
print("=" * 72)
print("CALCULO IC CON ALTURA AUTOMÁTICA — INSTALADO")
print("=" * 72)

print()
print("Nuevo comportamiento:")
print("- CALCULO IC ocupa una página de ancho.")
print("- Se divide en tantas páginas verticales como necesite.")
print("- Ya no queda todo comprimido en una sola página.")
print("- Se conservan todas sus tablas y resultados.")

print()
print("No se tocó:")
print("- El filtrado de componentes ya resuelto.")
print("- La eliminación del índice y catálogo.")
print("- La primera página de componente.")
print("- El resto de la aplicación.")

print()
print("BACKUP ANTERIOR:")
print(
    backup_before
)

print()
print("BACKUP FINAL:")
print(
    backup_after
)

print()
print("CHECKPOINT:")
print(
    checkpoint
)
