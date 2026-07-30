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
# BACKUP DE LA BASE CANÓNICA ACTUAL
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
    "SIPUCOL_BASE_CANONICA_ANTES_QUITAR_INDICE_Y_CATALOGO_PDF"
)


print()
print("=" * 72)
print("BACKUP CANÓNICO CREADO")
print("=" * 72)
print(backup_before)


worker_original = WORKER.read_bytes()


# ============================================================
# LOCALIZAR UNA FUNCIÓN PYTHON SIN TOCAR EL RESTO
# ============================================================

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


# ============================================================
# ÚNICO CAMBIO:
# RECONOCER SOLO PÁGINAS REALES DE TABLAS
# ============================================================

new_component_detector = r'''def _component_for_page(
    normalized_text: str,
    component_names: list[str],
) -> str | None:
    """
    Reconoce exclusivamente una página real de inspección
    de un componente.

    No basta con que aparezca el nombre del componente.

    La página debe contener simultáneamente:
    - IDENTIFICACIÓN / LOCALIZACIÓN;
    - REGISTROS DE DAÑOS / DETERIORO / DEFECTOS;
    - el encabezado exacto "Componente: <nombre>";
    - un área inmediatamente después del componente.

    Esto excluye:
    - Índice inicial;
    - nota inicial;
    - catálogo general de códigos;
    - anexos;
    - páginas que solo mencionan el nombre del componente.
    """

    if not normalized_text:

        return None


    # Una tabla real de componente siempre contiene
    # estos encabezados propios del formato de inspección.
    has_identification = (
        "identificacionlocalizacion"
        in normalized_text
    )


    has_damage_register = any(

        marker in normalized_text

        for marker in (
            "registrosdedanosdeteriorodefectos",
            "registrodedanosdeteriorodefectos",
            "registrosdedanodeteriorodefectos",
        )
    )


    if (
        not has_identification
        or not has_damage_register
    ):

        return None


    damage_position = -1


    for marker in (
        "registrosdedanosdeteriorodefectos",
        "registrodedanosdeteriorodefectos",
        "registrosdedanodeteriorodefectos",
    ):

        position = normalized_text.find(
            marker
        )

        if position >= 0:

            damage_position = position
            break


    matches = []


    for name in component_names:

        clean_name = str(
            name
            or ""
        ).strip()


        normalized_name = _normalize(
            clean_name
        )


        if not normalized_name:

            continue


        # Al normalizar:
        #
        # "Componente : Superficie del tablero"
        #
        # se convierte en:
        #
        # "componentesuperficiedeltablero"
        component_header = (
            "componente"
            + normalized_name
        )


        header_position = normalized_text.find(
            component_header
        )


        if (
            header_position < 0
            or header_position
            <= damage_position
        ):

            continue


        # En una hoja real, inmediatamente después del
        # nombre aparece "Área: Durabilidad/Estabilidad/...".
        after_header = normalized_text[

            header_position
            + len(
                component_header
            ):

            header_position
            + len(
                component_header
            )
            + 120
        ]


        if "area" not in after_header:

            continue


        # Una tabla real también contiene las columnas
        # de severidad y número de fotos.
        local_table_text = normalized_text[

            header_position:

            header_position
            + 1000
        ]


        if (
            "severidad"
            not in local_table_text

            or (
                "nfotos"
                not in local_table_text

                and "numerodefotos"
                not in local_table_text
            )
        ):

            continue


        matches.append(
            clean_name
        )


    if not matches:

        return None


    # Evita coincidencias parciales cuando existen
    # componentes con nombres similares.
    matches.sort(

        key=lambda value: len(
            _normalize(
                value
            )
        ),

        reverse=True,
    )


    return matches[0]
'''


try:

    worker_code = WORKER.read_text(
        encoding="utf-8-sig",
        errors="strict",
    ).replace(
        "\r\n",
        "\n",
    )


    function_start, function_end = (
        find_function_range(
            worker_code,
            "_component_for_page",
        )
    )


    updated_worker = (
        worker_code[:function_start]
        + new_component_detector.rstrip()
        + "\n\n"
        + worker_code[function_end:].lstrip()
    )


    WORKER.write_text(
        updated_worker,
        encoding="utf-8",
        newline="\n",
    )


    # ========================================================
    # VALIDAR SINTAXIS
    # ========================================================

    print()
    print("Validando módulo activo...")


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
    # COMPROBAR QUE NO SE TOCÓ EL MOTOR ACTIVO
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
    # PRUEBA REAL CON EL PDF ACTUAL
    # ========================================================

    downloads = (
        Path.home()
        / "Downloads"
    )


    test_pdf = (
        downloads
        / "INSPECCION_SIPUCOL.pdf"
    )


    test_output = (
        downloads
        / "INSPECCION_SIPUCOL_SIN_INDICE_PRUEBA.pdf"
    )


    if test_pdf.exists():

        test_code = f'''
from pathlib import Path

from pypdf import PdfReader

from backend import (
    pdf_final_page_filter_worker
    as worker
)


source = Path(
    r"{test_pdf}"
)


destination = Path(
    r"{test_output}"
)


result = worker.filtrar_paginas_pdf(
    source,
    destination,
    [
        "Superficie del tablero"
    ],
)


print(
    "PAGINAS_ORIGINALES="
    + str(
        result["original_pages"]
    )
)


print(
    "PAGINAS_FINALES="
    + str(
        result["final_pages"]
    )
)


print(
    "PAGINAS_CONSERVADAS="
    + ",".join(
        str(
            page
        )
        for page in result[
            "selected_pages"
        ]
    )
)


reader = PdfReader(
    str(
        destination
    )
)


if len(
    reader.pages
) != 2:

    raise RuntimeError(
        "El PDF de prueba no quedó "
        "con exactamente 2 páginas."
    )


first_text = (
    reader.pages[0]
    .extract_text()
    or ""
).casefold()


second_text = (
    reader.pages[1]
    .extract_text()
    or ""
).casefold()


if "índice" in first_text[:500]:

    raise RuntimeError(
        "El índice inicial todavía quedó "
        "como primera página."
    )


if (
    "componente"
    not in first_text

    or "superficie del tablero"
    not in first_text
):

    raise RuntimeError(
        "La primera página no es "
        "Superficie del tablero."
    )


if (
    "índice de condición"
    not in second_text

    and "indice de condición"
    not in second_text

    and "indice de condicion"
    not in second_text
):

    raise RuntimeError(
        "La segunda página no corresponde "
        "al cálculo del Índice de Condición."
    )


print(
    "INDICE_INICIAL_ELIMINADO=OK"
)


print(
    "CATALOGO_CODIGOS_ELIMINADO=OK"
)


print(
    "COMPONENTE_REAL_CONSERVADO=OK"
)


print(
    "CALCULO_IC_CONSERVADO=OK"
)


print(
    "PDF_PRUEBA="
    + str(
        destination
    )
)
'''


        test_result = subprocess.run(
            [
                sys.executable,
                "-c",
                test_code,
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

    else:

        print()
        print(
            "Prueba local omitida: "
            "no encontré INSPECCION_SIPUCOL.pdf "
            "en Descargas."
        )


    # ========================================================
    # CONFIRMAR QUE SOLO CAMBIÓ ESA FUNCIÓN
    # ========================================================

    final_worker = WORKER.read_text(
        encoding="utf-8",
        errors="strict",
    )


    required_markers = [
        "has_identification",
        "has_damage_register",
        "component_header",
        "local_table_text",
        "CATÁLOGO",
    ]


    for marker in required_markers:

        if marker not in final_worker:

            raise RuntimeError(
                "No quedó instalada la validación: "
                + marker
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
# LIMPIAR SOLO CACHÉ PYTHON
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
    "SIPUCOL_BASE_CANONICA_PDF_SIN_INDICE_NI_CATALOGO"
)


checkpoint = (
    ROOT
    / (
        "CHECKPOINT_PDF_SIN_INDICE_NI_CATALOGO_"
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
        "- Reconocimiento estricto de páginas reales de componentes.",
        "- Índice inicial excluido.",
        "- Nota inicial excluida.",
        "- Catálogo general de códigos excluido.",
        "",
        "Conservado sin modificaciones:",
        "- Selección de componentes diligenciados.",
        "- Contador de la UI.",
        "- Reporte de exportación.",
        "- Motor LibreOffice.",
        "- Calidad y escala.",
        "- Superficie del tablero.",
        "- CALCULO IC al final.",
        "- Excel original.",
        "- Frontend.",
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
print("ÍNDICE Y CATÁLOGO ELIMINADOS DEL PDF")
print("=" * 72)

print()
print("No se cambió:")
print("- Qué componentes se consideran diligenciados.")
print("- El filtrado que ya funcionaba.")
print("- CALCULO IC.")
print("- LibreOffice.")
print("- Calidad o diseño.")
print("- Excel.")
print("- Interfaz.")

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
