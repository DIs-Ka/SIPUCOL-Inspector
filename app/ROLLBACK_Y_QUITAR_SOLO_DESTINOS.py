from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path.cwd().resolve()
SRC = ROOT / "src"
BACKUPS = ROOT / "backups"

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

BACKUPS.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# 1. BACKUP DEL ESTADO ACTUAL, POR SEGURIDAD
# =========================================================

current_backup = (
    BACKUPS
    / f"SIPUCOL_ANTES_ROLLBACK_UI_FOTOS_{STAMP}.zip"
)

excluded = {
    "node_modules",
    ".git",
    "dist",
    "__pycache__",
    ".venv",
    ".sipucol_runtime",
    "backups",
}


with zipfile.ZipFile(
    current_backup,
    "w",
    compression=zipfile.ZIP_DEFLATED,
) as archive:

    for path in ROOT.rglob("*"):

        if not path.is_file():
            continue

        relative = path.relative_to(ROOT)

        if any(
            part in excluded
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


print()
print("Backup del estado actual:")
print(current_backup)


# =========================================================
# 2. ENCONTRAR EL BACKUP DE LA VERSIÓN PERFECTA
# =========================================================

preferred_patterns = [
    (
        "SIPUCOL_VERSION_PERFECTA_"
        "ANTES_DE_QUITAR_ENVIO_REVISION_*.zip"
    ),
    (
        "SIPUCOL_CHECKPOINT_"
        "PDF_LIBREOFFICE_ESTABLE_*.zip"
    ),
]


stable_backup = None


for pattern in preferred_patterns:

    candidates = sorted(
        BACKUPS.glob(pattern),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )

    if candidates:

        stable_backup = candidates[0]

        break


if stable_backup is None:

    raise SystemExit(
        "\nERROR:\n"
        "No encontré el backup de la versión perfecta.\n"
        "Busqué dentro de la carpeta backups."
    )


print()
print("Versión perfecta encontrada:")
print(stable_backup)


# =========================================================
# 3. EXTRAER SOLAMENTE SRC DEL BACKUP
#
# No se toca backend para conservar el PDF estable.
# =========================================================

with tempfile.TemporaryDirectory(
    prefix="sipucol_restore_src_"
) as temporary_directory:

    temporary_root = Path(
        temporary_directory
    )

    with zipfile.ZipFile(
        stable_backup,
        "r",
    ) as archive:

        src_files = [
            name
            for name in archive.namelist()
            if (
                name == "src"
                or name.startswith("src/")
            )
        ]

        if not src_files:

            raise RuntimeError(
                "El backup no contiene "
                "la carpeta src."
            )

        for name in src_files:

            archive.extract(
                name,
                temporary_root,
            )

    restored_src = (
        temporary_root
        / "src"
    )

    if not restored_src.exists():

        raise RuntimeError(
            "No se pudo extraer src "
            "desde el backup."
        )

    if SRC.exists():

        shutil.rmtree(
            SRC
        )

    shutil.copytree(
        restored_src,
        SRC,
    )


print()
print("Frontend restaurado exactamente desde el backup.")


# =========================================================
# 4. LOCALIZAR PANELFOTOS REAL
# =========================================================

candidates = []


for path in SRC.rglob("*"):

    if (
        not path.is_file()
        or path.suffix.lower()
        not in {
            ".jsx",
            ".tsx",
            ".js",
        }
    ):

        continue

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    normalized = (
        text.lower()
        .replace("ó", "o")
        .replace("í", "i")
    )

    if (
        "enviar foto a evaluacion"
        in normalized
    ):

        candidates.append(
            path
        )


preferred = [
    path
    for path in candidates
    if "panelfotos" in path.name.lower()
]


if preferred:

    panel_path = preferred[0]

elif len(candidates) == 1:

    panel_path = candidates[0]

else:

    found = "\n".join(
        str(path)
        for path in candidates
    )

    raise RuntimeError(
        "No pude identificar con seguridad "
        "el componente PanelFotos.\n"
        + found
    )


panel_original = panel_path.read_text(
    encoding="utf-8",
    errors="replace",
)


print()
print("Panel de Fotos encontrado:")
print(panel_path)


# =========================================================
# 5. ENCONTRAR EL CONTENEDOR JSX EXACTO
# =========================================================

normalized_panel = (
    panel_original.lower()
    .replace("ó", "o")
    .replace("í", "i")
)


phrase_position = normalized_panel.find(
    "enviar foto a evaluacion"
)


if phrase_position < 0:

    raise RuntimeError(
        "No encontré el texto "
        "'Enviar foto a Evaluación'."
    )


tag_pattern = re.compile(
    r"<(?P<closing>/)?"
    r"(?P<tag>div|section|nav|header)"
    r"\b[^>]*>",
    flags=re.IGNORECASE | re.DOTALL,
)


stack = []
blocks = []


for match in tag_pattern.finditer(
    panel_original
):

    tag = match.group(
        "tag"
    ).lower()

    closing = bool(
        match.group(
            "closing"
        )
    )

    raw = match.group(0)


    if not closing:

        if raw.rstrip().endswith(
            "/>"
        ):

            continue

        stack.append(
            (
                tag,
                match.start(),
            )
        )

        continue


    opening_index = None


    for index in range(
        len(stack) - 1,
        -1,
        -1,
    ):

        if stack[index][0] == tag:

            opening_index = (
                stack[index][1]
            )

            del stack[index:]

            break


    if opening_index is None:

        continue


    end_index = match.end()


    if not (
        opening_index
        <= phrase_position
        <= end_index
    ):

        continue


    fragment = panel_original[
        opening_index:end_index
    ]


    normalized_fragment = (
        fragment.lower()
        .replace("ó", "o")
        .replace("í", "i")
    )


    destination_count = sum(
        destination
        in normalized_fragment
        for destination in [
            "superficie del puente",
            "juntas de dilatacion",
            "bordillo",
            "barandas",
            "aletas",
            "estribos",
        ]
    )


    has_controls = (
        "<button"
        in normalized_fragment
        or ".map("
        in normalized_fragment
    )


    has_destination = (
        "destino:"
        in normalized_fragment
    )


    score = (
        destination_count * 20
        + (
            40
            if has_destination
            else 0
        )
        + (
            30
            if has_controls
            else 0
        )
    )


    blocks.append(
        (
            score,
            opening_index,
            end_index,
            len(fragment),
        )
    )


valid_blocks = [
    block
    for block in blocks
    if block[0] >= 50
]


if not valid_blocks:

    raise RuntimeError(
        "Encontré el título, pero no pude "
        "identificar con seguridad la franja "
        "completa de destinos."
    )


valid_blocks.sort(
    key=lambda block: (
        -block[0],
        block[3],
    )
)


_, block_start, block_end, _ = (
    valid_blocks[0]
)


removed_fragment = panel_original[
    block_start:block_end
]


panel_updated = (
    panel_original[:block_start].rstrip()
    + "\n\n"
    + panel_original[block_end:].lstrip()
)


# =========================================================
# 6. VALIDAR QUE QUITAMOS LA SECCIÓN CORRECTA
# =========================================================

normalized_removed = (
    removed_fragment.lower()
    .replace("ó", "o")
    .replace("í", "i")
)


required_markers = [
    "enviar foto a evaluacion",
    "juntas de dilatacion",
    "bordillo",
    "barandas",
]


missing_markers = [
    marker
    for marker in required_markers
    if marker not in normalized_removed
]


if missing_markers:

    raise RuntimeError(
        "El bloque localizado no contiene "
        "todos los elementos esperados.\n"
        "No se modificó el archivo."
    )


panel_backup = panel_path.with_name(
    panel_path.stem
    + f".backup_before_simple_remove_{STAMP}"
    + panel_path.suffix
)


panel_backup.write_text(
    panel_original,
    encoding="utf-8",
)


panel_path.write_text(
    panel_updated,
    encoding="utf-8",
)


# =========================================================
# 7. VALIDAR BUILD
# =========================================================

npm = (
    shutil.which("npm.cmd")
    or shutil.which("npm")
)


if not npm:

    panel_path.write_text(
        panel_original,
        encoding="utf-8",
    )

    raise RuntimeError(
        "No encontré npm."
    )


print()
print("Validando frontend...")


build = subprocess.run(
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


print(build.stdout)


if build.returncode != 0:

    panel_path.write_text(
        panel_original,
        encoding="utf-8",
    )

    raise RuntimeError(
        "La compilación falló y "
        "PanelFotos fue restaurado.\n\n"
        + build.stderr
    )


# =========================================================
# 8. LIMPIAR CACHÉ DE VITE
# =========================================================

vite_cache = (
    ROOT
    / "node_modules"
    / ".vite"
)


if vite_cache.exists():

    shutil.rmtree(
        vite_cache,
        ignore_errors=True,
    )


# =========================================================
# 9. BACKUP FINAL
# =========================================================

final_backup = (
    BACKUPS
    / f"SIPUCOL_PERFECTO_SOLO_SIN_DESTINOS_FOTOS_{STAMP}.zip"
)


with zipfile.ZipFile(
    final_backup,
    "w",
    compression=zipfile.ZIP_DEFLATED,
) as archive:

    for path in ROOT.rglob("*"):

        if not path.is_file():
            continue

        relative = path.relative_to(ROOT)

        if any(
            part in excluded
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


print()
print("=" * 72)
print("LISTO — VERSIÓN PERFECTA RESTAURADA")
print("=" * 72)

print()
print("Único cambio aplicado:")
print(
    "- Franja de destinos eliminada "
    "del módulo Fotos."
)

print()
print("Se eliminaron:")
print("- Enviar foto a Evaluación")
print("- Destino")
print("- Superficie del Puente")
print("- Juntas de dilatación")
print("- Bordillo")
print("- Barandas")
print("- Aletas")
print("- Estribos")
print("- Scroll horizontal de esa franja")

print()
print("No se modificó:")
print("- Backend")
print("- Generación PDF")
print("- Exportación Excel")
print("- Panel Evaluación")
print("- Códigos de daño")
print("- Autoguardado")
print("- Visor de fotos")
print("- Botones Cargar y Limpiar")

print()
print("BACKUP ORIGINAL RESTAURADO:")
print(stable_backup)

print()
print("BACKUP FINAL:")
print(final_backup)
