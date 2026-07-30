from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path.cwd().resolve()
PANEL = ROOT / "src" / "components" / "PanelEvaluacion.jsx"
SERVER = ROOT / "backend" / "server.py"
BACKUPS = ROOT / "backups"

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

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

BACKUPS.mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    return path.read_text(
        encoding="utf-8-sig",
        errors="strict",
    ).replace("\r\n", "\n")


def create_backup(label: str) -> Path:
    destination = BACKUPS / f"{label}_{STAMP}.zip"

    with zipfile.ZipFile(
        destination,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:

        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue

            relative = path.relative_to(ROOT)

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


def find_function_range(
    source: str,
    function_name: str,
) -> tuple[int, int]:

    match = re.search(
        rf"\bfunction\s+{re.escape(function_name)}"
        rf"\s*\([^)]*\)\s*\{{",
        source,
    )

    if not match:
        raise RuntimeError(
            f"No encontré la función {function_name}."
        )

    opening = source.find(
        "{",
        match.start(),
    )

    depth = 0

    for index in range(
        opening,
        len(source),
    ):
        character = source[index]

        if character == "{":
            depth += 1

        elif character == "}":
            depth -= 1

            if depth == 0:
                return match.start(), index + 1

    raise RuntimeError(
        f"No pude cerrar la función {function_name}."
    )


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
        + replacement
        + source[end:]
    )


if not PANEL.exists():
    raise SystemExit(
        f"ERROR: no existe {PANEL}"
    )

if not SERVER.exists():
    raise SystemExit(
        f"ERROR: no existe {SERVER}"
    )


# ============================================================
# 1. BACKUP DE LA VERSIÓN CANÓNICA ACTUAL
# ============================================================

backup_before = create_backup(
    "SIPUCOL_BASE_CANONICA_ANTES_ID_ALFANUMERICO"
)

print()
print("=" * 72)
print("BACKUP CANÓNICO CREADO")
print("=" * 72)
print(backup_before)


panel_original = PANEL.read_bytes()
server_original = SERVER.read_bytes()


def rollback() -> None:
    PANEL.write_bytes(panel_original)
    SERVER.write_bytes(server_original)


try:
    panel = read_text(PANEL)
    server = read_text(SERVER)

    # ========================================================
    # 2. CAMPOS NUEVOS: ALFANUMÉRICOS Y SIN MAXLENGTH
    # ========================================================

    block_start = panel.find(
        "const camposIdentificacionExtra = ["
    )

    if block_start < 0:
        raise RuntimeError(
            "No encontré camposIdentificacionExtra. "
            "El scroll nuevo no está instalado en este archivo."
        )

    block_end = panel.find(
        "\n]\n",
        block_start,
    )

    if block_end < 0:
        raise RuntimeError(
            "No pude cerrar camposIdentificacionExtra."
        )

    block_end += len("\n]\n")

    new_extra_fields = """const camposIdentificacionExtra = [
  {
    key: 'idCarreteraTramo',
    label: 'ID carretera y tramo',
    mode: 'alphanumeric'
  },
  {
    key: 'sentido',
    label: 'Sentido',
    mode: 'alphanumeric'
  },
  {
    key: 'consecutivo',
    label: 'Consecutivo',
    mode: 'alphanumeric'
  }
]
"""

    panel = (
        panel[:block_start]
        + new_extra_fields
        + panel[block_end:]
    )

    # ========================================================
    # 3. NORMALIZADOR: SIN LÍMITE PARA LOS CAMPOS NUEVOS
    # ========================================================

    possible_normalizers = [
        "normalizarSegmentoIdPuente",
        "normalizarIdentificacion",
        "normalizarCampoIdentificacion",
    ]

    normalizer_name = None

    for candidate in possible_normalizers:
        if re.search(
            rf"\bfunction\s+{re.escape(candidate)}\s*\(",
            panel,
        ):
            normalizer_name = candidate
            break

    if not normalizer_name:
        raise RuntimeError(
            "No encontré la función que valida "
            "los segmentos del ID."
        )

    new_normalizer = f"""function {normalizer_name}(key, value) {{
  const texto = String(value ?? '')

  // Territorial / Departamento conserva su regla actual.
  if (key === 'idPuente') {{
    return texto
      .replace(/\\D/g, '')
      .slice(0, 2)
  }}

  // Los tres campos nuevos aceptan cualquier cantidad
  // de letras y números, sin espacios ni símbolos.
  if (
    key === 'idCarreteraTramo' ||
    key === 'sentido' ||
    key === 'consecutivo'
  ) {{
    return texto
      .replace(/[^A-Za-z0-9]/g, '')
      .toUpperCase()
  }}

  return texto
}}"""

    panel = replace_function(
        panel,
        normalizer_name,
        new_normalizer,
    )

    # ========================================================
    # 4. QUITAR MAXLENGTH DEL INPUT NUEVO
    # ========================================================

    panel = re.sub(
        r"""
        \n[ \t]*maxLength=
        \{
            campo\.maxLength
        \}
        """,
        "",
        panel,
        flags=re.VERBOSE,
    )

    # ========================================================
    # 5. BACKEND: ID CARRETERA ALINEADO A LA DERECHA
    # ========================================================

    function_position = server.find(
        "def escribir_identificacion_en_root"
    )

    if function_position < 0:
        raise RuntimeError(
            "No encontré escribir_identificacion_en_root."
        )

    id_block_start = server.find(
        "    # ID Puente",
        function_position,
    )

    date_block_start = server.find(
        "    # Fecha: formato visual",
        id_block_start,
    )

    if (
        id_block_start < 0
        or date_block_start < 0
    ):
        raise RuntimeError(
            "No encontré el bloque de escritura "
            "del ID Puente en server.py."
        )

    backend_id_block = """    # ID Puente dividido en las cuatro secciones reales.
    #
    # Los tres campos nuevos aceptan letras y números.
    # ID carretera y tramo se alinea exclusivamente
    # a la derecha dentro de J13:Q13.

    grupos_id = [
        (
            "idPuente",
            ["G13", "H13"],
            r"[^0-9]",
        ),
        (
            "idCarreteraTramo",
            [
                "J13", "K13", "L13", "M13",
                "N13", "O13", "P13", "Q13",
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
            # La plantilla tiene ocho casillas.
            # Se toman los últimos ocho caracteres y
            # se colocan contra el borde derecho.
            clean_excel = clean[-len(refs):]

            refs_destino = refs[
                len(refs) - len(clean_excel):
            ]

        else:
            # Los otros grupos mantienen escritura
            # desde la primera casilla disponible.
            clean_excel = clean[:len(refs)]
            refs_destino = refs[:len(clean_excel)]

        for ref, character in zip(
            refs_destino,
            clean_excel,
        ):
            write(
                ref,
                character,
                key,
            )

"""

    server = (
        server[:id_block_start]
        + backend_id_block
        + server[date_block_start:]
    )

    # ========================================================
    # 6. GUARDAR
    # ========================================================

    PANEL.write_text(
        panel,
        encoding="utf-8",
        newline="\n",
    )

    SERVER.write_text(
        server,
        encoding="utf-8",
        newline="\n",
    )

    # ========================================================
    # 7. VALIDAR BACKEND
    # ========================================================

    print()
    print("Validando backend...")

    backend_result = subprocess.run(
        [
            "py",
            "-m",
            "py_compile",
            str(SERVER),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )

    if backend_result.returncode != 0:
        raise RuntimeError(
            backend_result.stderr
        )

    print("Backend correcto.")

    # ========================================================
    # 8. VALIDAR FRONTEND
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
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )

    print(frontend_result.stdout)

    if frontend_result.returncode != 0:
        raise RuntimeError(
            frontend_result.stderr
        )

    # ========================================================
    # 9. COMPROBACIÓN FINAL
    # ========================================================

    final_panel = read_text(PANEL)
    final_server = read_text(SERVER)

    required_panel = [
        "const camposIdentificacionExtra",
        "ID carretera y tramo",
        "mode: 'alphanumeric'",
        ".replace(/[^A-Za-z0-9]/g, '')",
    ]

    required_server = [
        "clean_excel = clean[-len(refs):]",
        "refs_destino = refs[",
        '"idCarreteraTramo"',
        '["J13", "K13", "L13", "M13"',
    ]

    for marker in required_panel:
        if marker not in final_panel:
            raise RuntimeError(
                f"No quedó instalado en frontend: {marker}"
            )

    for marker in required_server:
        if marker not in final_server:
            raise RuntimeError(
                f"No quedó instalado en backend: {marker}"
            )

except Exception as error:
    rollback()

    print()
    print("=" * 72)
    print("ERROR — CAMBIOS REVERTIDOS")
    print("=" * 72)
    print(error)

    raise SystemExit(1)


# ============================================================
# 10. CACHÉ Y BACKUP FINAL
# ============================================================

shutil.rmtree(
    ROOT / "node_modules" / ".vite",
    ignore_errors=True,
)

shutil.rmtree(
    ROOT / "dist",
    ignore_errors=True,
)

backup_after = create_backup(
    "SIPUCOL_BASE_CANONICA_ID_ALFANUMERICO_DERECHA"
)

print()
print("=" * 72)
print("ID NUEVOS ALFANUMÉRICOS — INSTALADO")
print("=" * 72)

print()
print("Interfaz:")
print("- ID carretera y tramo: letras y números sin límite.")
print("- Sentido: letras y números sin límite.")
print("- Consecutivo: letras y números sin límite.")
print("- Espacios y símbolos siguen bloqueados.")

print()
print("Excel — ID carretera y tramo:")
print("- 100 se escribe en las últimas 3 casillas.")
print("- 10 se escribe en las últimas 2 casillas.")
print("- Solo este grupo queda alineado a la derecha.")
print("- Si supera 8 caracteres, se usan los últimos 8.")

print()
print("BACKUP ANTERIOR:")
print(backup_before)

print()
print("BACKUP FINAL:")
print(backup_after)
