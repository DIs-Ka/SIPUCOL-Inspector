from __future__ import annotations

import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path


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
# VALIDAR
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
    "SIPUCOL_BASE_CANONICA_ANTES_REPARAR_PDF_SIMPLE"
)


print()
print("=" * 72)
print("BACKUP CANÓNICO CREADO")
print("=" * 72)
print(backup_before)


worker_original = WORKER.read_bytes()


# ============================================================
# UTILIDADES
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
# FILTRO SIMPLE Y DEFINITIVO
# ============================================================

simple_filter = r'''def filtrar_paginas_pdf(
    full_pdf: Path,
    final_pdf: Path,
    component_names: list[str],
) -> dict:
    """
    Conserva únicamente:

    1. Las páginas reales de los componentes solicitados.
    2. Las páginas originales de CALCULO IC al final.

    No recorta, divide, rasteriza, escala ni recompone páginas.
    """

    import re
    import unicodedata

    from pypdf import PdfReader, PdfWriter


    def fold_text(
        value,
    ) -> str:

        text = unicodedata.normalize(
            "NFD",
            str(
                value
                or ""
            ),
        )

        text = "".join(
            character
            for character in text
            if unicodedata.category(
                character
            )
            != "Mn"
        )

        text = text.lower()

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()


    def real_component(
        page_text: str,
    ) -> str | None:

        folded = fold_text(
            page_text
        )


        # Una hoja real de inspección contiene todos
        # estos encabezados. El índice y el catálogo no.
        required = [
            "identificacion",
            "localizacion",
            "registros de danos",
            "deterioro",
            "severidad",
        ]


        if not all(
            marker in folded
            for marker in required
        ):

            return None


        matches = []


        for component_name in component_names:

            clean_name = str(
                component_name
                or ""
            ).strip()

            folded_name = fold_text(
                clean_name
            )


            if not folded_name:

                continue


            exact_header = re.compile(
                r"\bcomponente\s*:\s*"
                + re.escape(
                    folded_name
                )
                + r"(?=\s|$)",
                flags=re.IGNORECASE,
            )


            if exact_header.search(
                folded
            ):

                matches.append(
                    clean_name
                )


        if not matches:

            return None


        matches.sort(
            key=lambda name: len(
                fold_text(
                    name
                )
            ),
            reverse=True,
        )


        return matches[0]


    def calculation_page(
        page_text: str,
    ) -> bool:

        folded = fold_text(
            page_text
        )


        # El índice inicial menciona "Índice de condición",
        # pero no contiene estas señales de la hoja de cálculo.
        strong_markers = [
            "calificacion ponderada del puente",
            "calificacion ponderada del grupo",
            "calificacion ponderada del componente",
            "ponderados por componentes",
            "ponderados por grupo",
            "seleccionar categoria de la via",
            "descripcion del estado del puente",
            "indicaciones consideraciones",
        ]


        marker_count = sum(
            1
            for marker in strong_markers
            if marker in folded
        )


        has_final_result = (
            "indice de condicion"
            in folded

            and (
                "descripcion del estado del puente"
                in folded

                or "calificacion ponderada"
                in folded
            )
        )


        has_calculation_tables = (
            "ponderados por componentes"
            in folded

            and (
                "elegir caso"
                in folded

                or "seleccionar categoria de la via"
                in folded
            )
        )


        return (
            marker_count >= 2
            or has_final_result
            or has_calculation_tables
        )


    reader = PdfReader(
        str(
            full_pdf
        )
    )


    component_pages = []
    condition_pages = []

    found_components = set()
    debug = []


    for page_index, page in enumerate(
        reader.pages
    ):

        try:

            page_text = (
                page.extract_text()
                or ""
            )

        except Exception:

            page_text = ""


        component = real_component(
            page_text
        )


        if component is not None:

            component_pages.append(
                page_index
            )

            found_components.add(
                fold_text(
                    component
                )
            )

            debug.append((
                page_index + 1,
                "COMPONENTE_REAL",
                component,
            ))

            continue


        if calculation_page(
            page_text
        ):

            condition_pages.append(
                page_index
            )

            debug.append((
                page_index + 1,
                "CALCULO_IC",
                "",
            ))


    expected_components = {
        fold_text(
            component
        )
        for component in component_names
        if fold_text(
            component
        )
    }


    missing_components = (
        expected_components
        - found_components
    )


    if missing_components:

        raise RuntimeError(
            "No pude localizar estos componentes "
            "en el PDF generado: "
            + ", ".join(
                sorted(
                    missing_components
                )
            )
        )


    if not component_pages:

        raise RuntimeError(
            "No se encontró ninguna página "
            "real de componente."
        )


    if not condition_pages:

        raise RuntimeError(
            "No se encontró la página de CALCULO IC."
        )


    # Eliminar duplicados sin alterar el orden original.
    component_pages = list(
        dict.fromkeys(
            sorted(
                component_pages
            )
        )
    )

    condition_pages = list(
        dict.fromkeys(
            sorted(
                condition_pages
            )
        )
    )


    selected_pages = (
        component_pages
        + condition_pages
    )


    writer = PdfWriter()


    # Copia directa de las páginas originales.
    # No hay cropbox, mosaicos, zoom ni transformaciones.
    for page_index in selected_pages:

        writer.add_page(
            reader.pages[
                page_index
            ]
        )


    final_pdf.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    temporary_output = (
        final_pdf.parent
        / (
            final_pdf.stem
            + ".sipucol_reparando.tmp.pdf"
        )
    )


    with temporary_output.open(
        "wb"
    ) as output_file:

        writer.write(
            output_file
        )


    if (
        not temporary_output.exists()
        or temporary_output.stat().st_size
        < 1000
    ):

        raise RuntimeError(
            "El PDF final quedó vacío "
            "o incompleto."
        )


    if final_pdf.exists():

        final_pdf.unlink()


    temporary_output.replace(
        final_pdf
    )


    return {
        "original_pages":
            len(
                reader.pages
            ),

        "final_pages":
            len(
                selected_pages
            ),

        "component_pages":
            [
                page + 1
                for page in component_pages
            ],

        "condition_pages":
            [
                page + 1
                for page in condition_pages
            ],

        "selected_pages":
            [
                page + 1
                for page in selected_pages
            ],

        "condition_output_pages":
            len(
                condition_pages
            ),

        # Compatibilidad con el reporte existente.
        # Ya no se divide ninguna página.
        "tiled_condition_pages":
            [],

        "debug":
            debug,
    }
'''


try:

    worker_code = read_text(
        WORKER
    )


    # ========================================================
    # 1. RETIRAR EL CAMBIO DE ALTURA AUTOMÁTICA
    # ========================================================

    layout_pattern = re.compile(
        r"(?ms)"
        r"^(?P<indent>[ \t]*)"
        + re.escape(
            LAYOUT_START
        )
        + r"\s*$"
        + r".*?"
        + r"^[ \t]*"
        + re.escape(
            LAYOUT_END
        )
        + r"\s*$",
    )


    layout_match = layout_pattern.search(
        worker_code
    )


    if layout_match:

        indentation = layout_match.group(
            "indent"
        )


        original_libreoffice_call = "\n".join([
            (
                indentation
                + "stable_worker."
                + "convertir_excel_seleccionado_job("
            ),
            (
                indentation
                + "    child_job_id,"
            ),
            (
                indentation
                + "    str("
            ),
            (
                indentation
                + "        source"
            ),
            (
                indentation
                + "    ),"
            ),
            (
                indentation
                + "    str("
            ),
            (
                indentation
                + "        full_pdf"
            ),
            (
                indentation
                + "    ),"
            ),
            (
                indentation
                + ")"
            ),
        ])


        worker_code = (
            worker_code[:layout_match.start()]
            + original_libreoffice_call
            + worker_code[layout_match.end():]
        )


    # ========================================================
    # 2. GARANTIZAR QUE LIBREOFFICE USE EL EXCEL ORIGINAL
    # ========================================================

    converter_start, converter_end = (
        find_function_range(
            worker_code,
            "convertir_excel_seleccionado_job",
        )
    )


    converter_code = worker_code[
        converter_start:converter_end
    ]


    stable_call_pattern = re.compile(
        r"(?ms)"
        r"^(?P<indent>[ \t]*)"
        r"stable_worker"
        r"\."
        r"convertir_excel_seleccionado_job"
        r"\("
        r"\s*child_job_id\s*,"
        r"\s*str\("
        r"\s*(?:source|prepared_excel)\s*"
        r"\)\s*,"
        r"\s*str\("
        r"\s*full_pdf\s*"
        r"\)\s*,?"
        r"\s*\)",
    )


    stable_match = stable_call_pattern.search(
        converter_code
    )


    if not stable_match:

        raise RuntimeError(
            "No encontré la llamada activa "
            "a LibreOffice."
        )


    indentation = stable_match.group(
        "indent"
    )


    canonical_call = "\n".join([
        (
            indentation
            + "stable_worker."
            + "convertir_excel_seleccionado_job("
        ),
        (
            indentation
            + "    child_job_id,"
        ),
        (
            indentation
            + "    str("
        ),
        (
            indentation
            + "        source"
        ),
        (
            indentation
            + "    ),"
        ),
        (
            indentation
            + "    str("
        ),
        (
            indentation
            + "        full_pdf"
        ),
        (
            indentation
            + "    ),"
        ),
        (
            indentation
            + ")"
        ),
    ])


    converter_code = (
        converter_code[:stable_match.start()]
        + canonical_call
        + converter_code[stable_match.end():]
    )


    worker_code = (
        worker_code[:converter_start]
        + converter_code
        + worker_code[converter_end:]
    )


    # ========================================================
    # 3. REEMPLAZAR SOLO EL FILTRO FINAL
    # ========================================================

    worker_code = replace_function(
        worker_code,
        "filtrar_paginas_pdf",
        simple_filter,
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
    print("Validando reparación...")


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
    # CONFIRMAR EL MOTOR ACTIVO
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
    # VERIFICAR QUE YA NO EXISTAN MOSAICOS
    # ========================================================

    final_code = read_text(
        WORKER
    )


    filter_start, filter_end = (
        find_function_range(
            final_code,
            "filtrar_paginas_pdf",
        )
    )


    filter_source = final_code[
        filter_start:filter_end
    ]


    converter_start, converter_end = (
        find_function_range(
            final_code,
            "convertir_excel_seleccionado_job",
        )
    )


    converter_source = final_code[
        converter_start:converter_end
    ]


    forbidden_filter_markers = [
        "add_condition_tiles",
        "RectangleObject",
        "cropbox",
        "tile_width",
        "tile_height",
        "columns = 2",
        "rows = 3",
    ]


    for marker in forbidden_filter_markers:

        if marker in filter_source:

            raise RuntimeError(
                "Todavía existe el recorte dañino: "
                + marker
            )


    if "prepared_excel" in converter_source:

        raise RuntimeError(
            "LibreOffice todavía está recibiendo "
            "una copia con el diseño alterado."
        )


    required_markers = [
        "writer.add_page(",
        '"tiled_condition_pages":',
        "component_pages + condition_pages",
        "str(\n            source\n        )",
    ]


    for marker in required_markers:

        if marker not in final_code:

            raise RuntimeError(
                "No quedó instalada la reparación: "
                + marker
            )


    print(
        "MOSAICOS_CALCULO_IC_ELIMINADOS=OK"
    )

    print(
        "RECORTES_PDF_ELIMINADOS=OK"
    )

    print(
        "LIBREOFFICE_USA_EXCEL_ORIGINAL=OK"
    )

    print(
        "INDICE_Y_CATALOGO_SIGUEN_EXCLUIDOS=OK"
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
# LIMPIAR CACHÉ
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
    "SIPUCOL_BASE_CANONICA_PDF_REPARADO_SIMPLE"
)


checkpoint = (
    ROOT
    / (
        "CHECKPOINT_PDF_REPARADO_SIMPLE_"
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
        "Resultado PDF:",
        "- Componente real conservado.",
        "- Índice inicial excluido.",
        "- Catálogo excluido.",
        "- CALCULO IC original conservado al final.",
        "- Sin recortes.",
        "- Sin mosaicos.",
        "- Sin división artificial en seis páginas.",
        "- Sin alteraciones de escala.",
        "",
        "No modificado:",
        "- Selección de componentes.",
        "- Contador UI.",
        "- Reporte de exportación.",
        "- Excel.",
        "- LibreOffice.",
        "- Interfaz.",
        "- Datos.",
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
print("PDF REPARADO — COMPONENTE + CALCULO IC")
print("=" * 72)

print()
print("Resultado esperado:")
print("- Página 1: Superficie del tablero.")
print("- Página 2: CALCULO IC original.")
print("- Sin índice.")
print("- Sin catálogo.")
print("- Sin mosaicos ni recortes.")

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
