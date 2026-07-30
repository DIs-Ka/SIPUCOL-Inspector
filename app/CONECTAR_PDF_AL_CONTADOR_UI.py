from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path.cwd().resolve()

PANEL = (
    ROOT
    / "src"
    / "components"
    / "PanelEvaluacion.jsx"
)

SERVER = (
    ROOT
    / "backend"
    / "server.py"
)

WORKER = (
    ROOT
    / "backend"
    / "pdf_filtered_libreoffice_worker.py"
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
# VALIDAR BASE CANÓNICA
# ============================================================

for required in [
    PANEL,
    SERVER,
    WORKER,
]:

    if not required.exists():

        raise SystemExit(
            f"ERROR: no encontré {required}"
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
    "SIPUCOL_BASE_CANONICA_ANTES_PDF_SEGUN_CONTADOR_UI"
)


print()
print("=" * 72)
print("BACKUP CANÓNICO CREADO")
print("=" * 72)
print(backup_before)


panel_original = PANEL.read_bytes()
server_original = SERVER.read_bytes()
worker_original = WORKER.read_bytes()


def rollback() -> None:

    PANEL.write_bytes(
        panel_original
    )

    SERVER.write_bytes(
        server_original
    )

    WORKER.write_bytes(
        worker_original
    )


# ============================================================
# AYUDANTES
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


def find_python_function_range(
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


def replace_python_function(
    source: str,
    function_name: str,
    replacement: str,
) -> str:

    start, end = find_python_function_range(
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
# 1. FRONTEND
# ENVIAR AL BACKEND SOLO payload.tablas
# ============================================================

try:

    panel_code = read_text(
        PANEL
    )

    fetch_pattern = re.compile(
        r'''
        const\s+response\s*=\s*
        await\s+fetch\s*\(
        \s*
        "http://127\.0\.0\.1:8000"
        \s*\+\s*
        "/api/export/"
        \s*\+\s*
        "pdf-from-selected-excel"
        \s*,\s*
        \{
        \s*
        method\s*:\s*
        "POST"
        \s*
        \}
        \s*
        \)
        ''',
        flags=(
            re.DOTALL
            | re.VERBOSE
        ),
    )

    replacement_fetch = r'''const payloadPdf =
        crearPayload()

      /*
      Fuente de verdad del PDF:

      payloadPdf.tablas ya contiene únicamente componentes
      con filas diligenciadas u observaciones.

      Ejemplo:
      - Superficie del tablero 2/40 -> entra.
      - Superficie de accesos 0/48 -> no entra.
      */

      const componentesPdf =
        (
          payloadPdf.tablas
          || []
        )
          .map(
            componente =>
              String(
                componente.nombre
                || ""
              ).trim()
          )
          .filter(
            Boolean
          )


      if (
        componentesPdf.length
        === 0
      ) {

        throw new Error(

          "No hay componentes diligenciados. "

          + "La identificación del puente no cuenta. "

          + "Marca una severidad, escribe fotos, "

          + "ubicación o una observación."
        )
      }


      const response =
        await fetch(

          "http://127.0.0.1:8000"
          + "/api/export/"
          + "pdf-from-selected-excel",

          {
            method:
              "POST",

            headers: {
              "Content-Type":
                "application/json"
            },

            body:
              JSON.stringify({

                componentes_pdf:
                  componentesPdf
              })
          }
        )'''

    panel_code, replacement_count = (
        fetch_pattern.subn(
            replacement_fetch,
            panel_code,
            count=1,
        )
    )

    if replacement_count != 1:

        raise RuntimeError(
            "No pude conectar la lista de componentes "
            "al botón Guardar PDF. "
            f"Coincidencias: {replacement_count}"
        )

    PANEL.write_text(
        panel_code,
        encoding="utf-8",
        newline="\n",
    )


    # ========================================================
    # 2. BACKEND
    # RECIBIR LA LISTA EXACTA DE LA UI
    # ========================================================

    server_code = read_text(
        SERVER
    )

    fastapi_import = re.search(
        r"(?m)^from fastapi import ([^\n]+)$",
        server_code,
    )

    if not fastapi_import:

        raise RuntimeError(
            "No encontré el import de FastAPI."
        )

    imports = [
        item.strip()
        for item in fastapi_import
        .group(1)
        .split(",")
        if item.strip()
    ]

    if "Body" not in imports:

        imports.append(
            "Body"
        )

    imports = list(
        dict.fromkeys(
            imports
        )
    )

    server_code = (
        server_code[
            :fastapi_import.start()
        ]
        + "from fastapi import "
        + ", ".join(
            imports
        )
        + server_code[
            fastapi_import.end():
        ]
    )


    new_endpoint = r'''def pdf_from_selected_excel(
    payload: dict = Body(
        default={}
    ),
):
    """
    Convierte el Excel seleccionado usando exclusivamente
    la lista de componentes diligenciados enviada por la UI.

    La identificación/localización nunca decide qué hojas
    aparecen en el PDF.
    """

    raw_components = (
        payload.get(
            "componentes_pdf"
        )
        if isinstance(
            payload,
            dict,
        )
        else []
    )

    component_names = []
    seen = set()

    for value in (
        raw_components
        or []
    ):

        clean = str(
            value
            or ""
        ).strip()

        key = normalizar(
            clean
        )

        if (
            not clean
            or not key
            or key in seen
        ):

            continue

        seen.add(
            key
        )

        component_names.append(
            clean
        )

    if not component_names:

        raise HTTPException(
            status_code=400,
            detail=(
                "No hay componentes diligenciados. "
                "La identificación del puente no cuenta. "
                "Marca una severidad, número de fotos, "
                "ubicación o una observación."
            ),
        )

    try:

        excel_path, pdf_path = (
            seleccionar_excel_y_destino_pdf()
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(
                error
            ),
        )

    if (
        not excel_path
        or not pdf_path
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
            "Conversión en cola. "
            f"{len(component_names)} componente(s) "
            "diligenciado(s)."
        ),
        source_excel=str(
            excel_path
        ),
        output_path=str(
            pdf_path
        ),
        componentes_pdf=component_names,
    )

    log(
        f"Job {job_id}: "
        "Componentes recibidos desde UI -> "
        + ", ".join(
            component_names
        )
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
            component_names,
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

        "componentes_pdf":
            component_names,
    }
'''

    server_code = replace_python_function(
        server_code,
        "pdf_from_selected_excel",
        new_endpoint,
    )

    SERVER.write_text(
        server_code,
        encoding="utf-8",
        newline="\n",
    )


    # ========================================================
    # 3. WORKER
    # NO ANALIZAR IDENTIFICACIÓN NI sheets_touched
    # USAR SOLO LOS NOMBRES RECIBIDOS DESDE LA UI
    # ========================================================

    worker_code = read_text(
        WORKER
    )


    new_create_filtered_copy = r'''def _create_filtered_copy(
    source: Path,
    destination: Path,
    component_names: list[str] | None = None,
) -> tuple[list[str], list[str], str]:
    """
    Crea la copia temporal para LibreOffice usando
    exclusivamente los componentes activos de la UI.

    Esta función no revisa:
    - Identificación/localización.
    - Fecha u hora.
    - ID Puente.
    - sheets_touched.
    - Contenido general de la plantilla.

    La lista recibida procede de payload.tablas, que usa el
    mismo criterio de los contadores 2/40, 0/48, etc.
    """

    requested = []
    requested_keys = set()

    for value in (
        component_names
        or []
    ):

        clean = str(
            value
            or ""
        ).strip()

        key = _normalize(
            clean
        )

        if (
            not clean
            or not key
            or key in requested_keys
            or _is_system_sheet(
                clean
            )
        ):

            continue

        requested_keys.add(
            key
        )

        requested.append(
            clean
        )

    if not requested:

        raise RuntimeError(
            "No hay componentes diligenciados "
            "para generar el PDF. "
            "La identificación del puente no cuenta."
        )

    workbook_names = (
        _workbook_sheet_names(
            source
        )
    )

    workbook_by_key = {
        _normalize(
            name
        ):
            name

        for name in workbook_names
    }

    components = []
    missing = []

    for requested_name in requested:

        key = _normalize(
            requested_name
        )

        actual_name = (
            workbook_by_key.get(
                key
            )
        )

        if not actual_name:

            missing.append(
                requested_name
            )

            continue

        components.append(
            actual_name
        )

    if missing:

        raise RuntimeError(
            "No encontré en el Excel estas hojas "
            "diligenciadas: "
            + ", ".join(
                missing
            )
        )

    visible = _patch_workbook_visibility(
        source,
        destination,
        components,
    )

    visible_components = [
        name
        for name in visible
        if not _is_calculo_ic(
            name
        )
    ]

    expected_keys = {
        _normalize(
            name
        )
        for name in components
    }

    visible_keys = {
        _normalize(
            name
        )
        for name in visible_components
    }

    if visible_keys != expected_keys:

        raise RuntimeError(
            "El filtro dejó visibles componentes "
            "que no corresponden al contador de la UI."
        )

    if any(
        _is_index(
            name
        )
        for name in visible
    ):

        raise RuntimeError(
            "El Índice continuó visible."
        )

    if any(
        _is_evaluation(
            name
        )
        for name in visible
    ):

        raise RuntimeError(
            "Evaluación continuó visible."
        )

    if any(
        _is_annex(
            name
        )
        for name in visible
    ):

        raise RuntimeError(
            "Un anexo continuó visible."
        )

    if not any(
        _is_calculo_ic(
            name
        )
        for name in visible
    ):

        raise RuntimeError(
            "CALCULO IC no quedó visible."
        )

    return (
        components,
        visible,
        (
            "lista exacta enviada desde "
            "payload.tablas de la interfaz"
        ),
    )
'''


    new_converter = r'''def convertir_excel_seleccionado_job(
    job_id: str,
    excel_path: str,
    pdf_path: str,
    component_names: list[str] | None = None,
) -> None:
    """
    Flujo definitivo:

    UI payload.tablas
    -> lista exacta de componentes diligenciados
    -> copia temporal con solo esas hojas
    -> CALCULO IC
    -> LibreOffice estable.
    """

    from backend import server

    temporary_directory = None

    try:

        source = Path(
            excel_path
        ).resolve()

        if (
            not source.exists()
            or not source.is_file()
        ):

            raise RuntimeError(
                "No existe el Excel seleccionado."
            )

        temporary_directory = Path(
            tempfile.mkdtemp(
                prefix=(
                    "sipucol_pdf_ui_"
                )
            )
        )

        filtered_excel = (
            temporary_directory
            / (
                "SIPUCOL_PDF_COMPONENTES_UI"
                + source.suffix
            )
        )

        server.set_job(
            job_id,
            status="running",
            progress=5,
            message=(
                "Aplicando el contador "
                "de componentes de la interfaz..."
            ),
            source_excel=str(
                source
            ),
            output_path=str(
                pdf_path
            ),
            componentes_pdf=(
                component_names
                or []
            ),
        )

        (
            components,
            visible,
            detection_method,
        ) = _create_filtered_copy(
            source,
            filtered_excel,
            component_names,
        )

        server.log(
            f"Job {job_id}: "
            f"Filtro PDF por {detection_method}"
        )

        server.log(
            f"Job {job_id}: "
            "Componentes incluidos -> "
            + ", ".join(
                components
            )
        )

        server.log(
            f"Job {job_id}: "
            "Hojas visibles -> "
            + ", ".join(
                visible
            )
        )

        server.set_job(
            job_id,
            status="running",
            progress=18,
            message=(
                f"{len(components)} componente(s) "
                "diligenciado(s). "
                "Exportando con LibreOffice..."
            ),
            filtered_sheets=visible,
        )

        stable_worker.convertir_excel_seleccionado_job(
            job_id,
            str(
                filtered_excel
            ),
            str(
                pdf_path
            ),
        )

    except Exception as error:

        server.set_job(
            job_id,
            status="error",
            progress=0,
            message=(
                "No se pudo crear "
                "el PDF filtrado"
            ),
            error=str(
                error
            ),
        )

        server.log(
            f"Job {job_id}: "
            f"ERROR FILTRO PDF -> {error}"
        )

    finally:

        if temporary_directory is not None:

            shutil.rmtree(
                temporary_directory,
                ignore_errors=True,
            )
'''

    worker_code = replace_python_function(
        worker_code,
        "_create_filtered_copy",
        new_create_filtered_copy,
    )

    worker_code = replace_python_function(
        worker_code,
        "convertir_excel_seleccionado_job",
        new_converter,
    )

    WORKER.write_text(
        worker_code,
        encoding="utf-8",
        newline="\n",
    )


    # ========================================================
    # 4. VALIDAR PYTHON
    # ========================================================

    print()
    print("Validando backend...")

    compile_result = subprocess.run(
        [
            "py",
            "-m",
            "py_compile",
            str(
                SERVER
            ),
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
        "Backend correcto."
    )


    # ========================================================
    # 5. VALIDAR MOTOR ACTIVO
    # ========================================================

    active_result = subprocess.run(
        [
            "py",
            "-c",
            (
                "from backend import server; "
                "f=server.convertir_excel_seleccionado_job; "
                "print('MODULO_ACTIVO=' + f.__module__); "
                "assert f.__module__ == "
                "'backend.pdf_filtered_libreoffice_worker'"
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
    # 6. PRUEBA REAL DE VISIBILIDAD
    # DEJAR SOLO UN COMPONENTE + CALCULO IC
    # ========================================================

    filter_test = subprocess.run(
        [
            "py",
            "-c",
            r'''
import tempfile
from pathlib import Path

from backend import server
from backend import pdf_filtered_libreoffice_worker as worker


template = Path(
    server.buscar_plantilla()
).resolve()


with tempfile.TemporaryDirectory(
    prefix="sipucol_test_ui_"
) as directory:

    output = (
        Path(directory)
        / (
            "prueba"
            + template.suffix
        )
    )

    components, visible, method = (
        worker._create_filtered_copy(
            template,
            output,
            [
                "Superficie del tablero"
            ],
        )
    )

    visible_components = [
        name
        for name in visible
        if not worker._is_calculo_ic(
            name
        )
    ]

    if visible_components != [
        "Superficie del tablero"
    ]:

        raise RuntimeError(
            "Se imprimieron componentes extra: "
            + repr(
                visible_components
            )
        )

    if not any(
        worker._is_calculo_ic(
            name
        )
        for name in visible
    ):

        raise RuntimeError(
            "Falta CALCULO IC."
        )

    print(
        "COMPONENTES_VISIBLES="
        + " | ".join(
            visible_components
        )
    )

    print(
        "TABLAS_CON_CERO_OCULTAS=OK"
    )

    print(
        "CALCULO_IC_VISIBLE=OK"
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
        filter_test.stdout
    )

    if filter_test.returncode != 0:

        raise RuntimeError(
            filter_test.stderr
            or filter_test.stdout
        )


    # ========================================================
    # 7. VALIDAR FRONTEND
    # ========================================================

    npm = (
        shutil.which("npm.cmd")
        or shutil.which("npm")
    )

    if not npm:

        raise RuntimeError(
            "No encontré npm."
        )

    print()
    print("Validando frontend...")

    frontend_result = subprocess.run(
        [
            npm,
            "run",
            "build",
        ],
        cwd=str(
            ROOT
        ),
        capture_output=True,
        text=True,
        timeout=600,
    )

    print(
        frontend_result.stdout
    )

    if frontend_result.returncode != 0:

        raise RuntimeError(
            frontend_result.stderr
            or frontend_result.stdout
        )


    # ========================================================
    # 8. VERIFICAR MARCADORES FINALES
    # ========================================================

    final_panel = read_text(
        PANEL
    )

    final_server = read_text(
        SERVER
    )

    final_worker = read_text(
        WORKER
    )

    required_panel_markers = [
        "componentes_pdf:",
        "payloadPdf.tablas",
        "La identificación del puente no cuenta",
    ]

    required_server_markers = [
        "component_names",
        "componentes_pdf",
        "Body(",
    ]

    required_worker_markers = [
        "lista exacta enviada desde",
        "component_names",
        "La lista recibida procede de payload.tablas",
    ]

    for marker in required_panel_markers:

        if marker not in final_panel:

            raise RuntimeError(
                "Falta en frontend: "
                + marker
            )

    for marker in required_server_markers:

        if marker not in final_server:

            raise RuntimeError(
                "Falta en backend: "
                + marker
            )

    for marker in required_worker_markers:

        if marker not in final_worker:

            raise RuntimeError(
                "Falta en worker: "
                + marker
            )


except Exception as error:

    rollback()

    print()
    print("=" * 72)
    print("ERROR — CAMBIOS REVERTIDOS AUTOMÁTICAMENTE")
    print("=" * 72)
    print(error)

    raise SystemExit(1)


# ============================================================
# LIMPIAR CACHÉS
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


shutil.rmtree(
    ROOT
    / "node_modules"
    / ".vite",
    ignore_errors=True,
)


# ============================================================
# BACKUP FINAL
# ============================================================

backup_after = create_backup(
    "SIPUCOL_BASE_CANONICA_PDF_SEGUN_CONTADOR_UI"
)


checkpoint = (
    ROOT
    / (
        "CHECKPOINT_PDF_SEGUN_CONTADOR_UI_"
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
        "Fuente de verdad del PDF:",
        "- payload.tablas de la interfaz.",
        "- Mismo criterio que los contadores 2/40, 0/48, etc.",
        "",
        "Ejemplo:",
        "- Superficie del tablero 2/40: visible.",
        "- Superficie de accesos 0/48: oculta.",
        "- Juntas 0/30: oculta.",
        "",
        "La identificación nunca cuenta.",
        "CALCULO IC permanece al final.",
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
print("PDF CONECTADO AL CONTADOR DE LA UI")
print("=" * 72)

print()
print("Regla definitiva:")
print("- Un componente 2/40 se imprime.")
print("- Un componente 0/48 no se imprime.")
print("- Un componente 0/30 no se imprime.")
print("- Identificación/localización no cuenta.")
print("- Una observación escrita sí cuenta.")
print("- CALCULO IC queda al final.")

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
