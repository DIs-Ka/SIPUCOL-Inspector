from __future__ import annotations

import re
import shutil
import subprocess
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path.cwd().resolve()
SRC = ROOT / "src"
BACKUPS = ROOT / "backups"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

BACKUPS.mkdir(parents=True, exist_ok=True)


def normalize(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(
        char
        for char in text
        if unicodedata.category(char) != "Mn"
    )
    return " ".join(text.lower().split())


def excluded(path: Path) -> bool:
    ignored = {
        "node_modules",
        ".git",
        "dist",
        "__pycache__",
        ".venv",
        ".sipucol_runtime",
        "backups",
    }

    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        return True

    if any(part in ignored for part in relative.parts):
        return True

    lower_name = path.name.lower()

    return (
        "backup" in lower_name
        or "broken" in lower_name
    )


# =========================================================
# 1. BACKUP COMPLETO DEL ESTADO ACTUAL
# =========================================================

checkpoint = (
    BACKUPS
    / f"SIPUCOL_ANTES_QUITAR_FRANJA_FOTOS_{STAMP}.zip"
)

with zipfile.ZipFile(
    checkpoint,
    "w",
    compression=zipfile.ZIP_DEFLATED,
) as archive:

    for file_path in ROOT.rglob("*"):

        if not file_path.is_file():
            continue

        if excluded(file_path):
            continue

        if file_path.suffix.lower() in {".pyc", ".log"}:
            continue

        archive.write(
            file_path,
            file_path.relative_to(ROOT),
        )

print()
print("BACKUP CREADO:")
print(checkpoint)


# =========================================================
# 2. ENCONTRAR EL PANEL FOTOS REAL
# =========================================================

phrase_pattern = re.compile(
    r"Enviar\s+foto\s+a\s+Evaluaci[oó]n",
    flags=re.IGNORECASE,
)

source_files = [
    path
    for path in SRC.rglob("*")
    if (
        path.is_file()
        and path.suffix.lower() in {".jsx", ".tsx", ".js"}
        and not excluded(path)
    )
]

matches: list[tuple[Path, str]] = []

for path in source_files:

    content = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    if phrase_pattern.search(content):
        matches.append((path, content))


preferred = [
    item
    for item in matches
    if "panelfotos" in item[0].name.lower()
]

if preferred:
    panel_path, source = preferred[0]

elif len(matches) == 1:
    panel_path, source = matches[0]

else:
    found = "\n".join(
        str(path)
        for path, _ in matches
    )

    raise SystemExit(
        "\nERROR:\n"
        "No pude identificar de forma única PanelFotos.\n"
        f"Archivos encontrados:\n{found}"
    )


print()
print("PANEL FOTOS REAL:")
print(panel_path)


# =========================================================
# 3. ENCONTRAR EL CONTENEDOR JSX EXACTO
# =========================================================

tag_pattern = re.compile(
    r"<(?P<closing>/)?"
    r"(?P<tag>div|section|nav|header|aside)"
    r"\b[^>]*>",
    flags=re.IGNORECASE | re.DOTALL,
)

target_names = [
    "superficie del puente",
    "juntas de dilatacion",
    "bordillo",
    "barandas",
    "aletas",
    "estribos",
]


def find_block(text: str) -> tuple[int, int, str]:
    phrase_match = phrase_pattern.search(text)

    if not phrase_match:
        raise RuntimeError(
            "No se encontró la franja en PanelFotos."
        )

    phrase_position = phrase_match.start()
    stack: list[tuple[str, int]] = []
    candidates: list[tuple[int, int, int, str]] = []

    for tag_match in tag_pattern.finditer(text):
        tag = tag_match.group("tag").lower()
        is_closing = bool(tag_match.group("closing"))
        raw_tag = tag_match.group(0)

        if not is_closing:
            if raw_tag.rstrip().endswith("/>"):
                continue

            stack.append((tag, tag_match.start()))
            continue

        opening_position = None

        for index in range(len(stack) - 1, -1, -1):
            if stack[index][0] == tag:
                opening_position = stack[index][1]
                del stack[index:]
                break

        if opening_position is None:
            continue

        closing_position = tag_match.end()

        if not (
            opening_position
            <= phrase_position
            <= closing_position
        ):
            continue

        fragment = text[
            opening_position:closing_position
        ]

        normalized = normalize(fragment)

        target_count = sum(
            name in normalized
            for name in target_names
        )

        score = 0

        if "enviar foto a evaluacion" in normalized:
            score += 100

        if "destino:" in normalized:
            score += 60

        score += target_count * 20

        if "carpeta actual" in normalized:
            score -= 500

        if "ver grande" in normalized:
            score -= 500

        if "no hay foto seleccionada" in normalized:
            score -= 500

        candidates.append(
            (
                score,
                opening_position,
                closing_position,
                fragment,
            )
        )

    valid = [
        candidate
        for candidate in candidates
        if candidate[0] >= 200
    ]

    if not valid:
        raise RuntimeError(
            "Encontré el texto, pero no el contenedor completo "
            "con Destino y los botones."
        )

    valid.sort(
        key=lambda item: (
            -item[0],
            len(item[3]),
        )
    )

    _, start, end, fragment = valid[0]

    # Incluir un condicional JSX del tipo:
    # {condicion && (<div>...</div>)}
    prefix_start = max(0, start - 300)
    prefix = text[prefix_start:start]

    conditional = re.search(
        r"\{\s*[\w.$()!]+\s*&&\s*\(\s*$",
        prefix,
    )

    if conditional:
        suffix = text[end:end + 80]
        closing = re.match(
            r"\s*\)\s*\}",
            suffix,
        )

        if closing:
            start = prefix_start + conditional.start()
            end = end + closing.end()
            fragment = text[start:end]

    return start, end, fragment


start, end, removed_fragment = find_block(source)


# =========================================================
# 4. VALIDAR QUE SEA EXACTAMENTE LA FRANJA PEDIDA
# =========================================================

removed_normalized = normalize(removed_fragment)

required = [
    "enviar foto a evaluacion",
    "destino:",
    "superficie del puente",
    "juntas de dilatacion",
    "bordillo",
    "barandas",
]

missing = [
    item
    for item in required
    if item not in removed_normalized
]

if missing:
    raise SystemExit(
        "\nSEGURIDAD ACTIVADA:\n"
        "El bloque encontrado no contiene todo lo esperado.\n"
        "No se modificó nada.\n"
        f"Faltaba: {missing}"
    )


# =========================================================
# 5. ELIMINAR DIRECTAMENTE DEL COMPONENTE
# =========================================================

file_backup = panel_path.with_name(
    f"{panel_path.stem}.backup_before_remove_send_bar_"
    f"{STAMP}{panel_path.suffix}"
)

shutil.copy2(
    panel_path,
    file_backup,
)

updated = (
    source[:start].rstrip()
    + "\n\n"
    + source[end:].lstrip()
)

panel_path.write_text(
    updated,
    encoding="utf-8",
)

print()
print("FRANJA ELIMINADA DIRECTAMENTE DEL JSX.")


# =========================================================
# 6. VALIDAR COMPILACIÓN; RESTAURAR SI FALLA
# =========================================================

npm = (
    shutil.which("npm.cmd")
    or shutil.which("npm")
)

if not npm:
    shutil.copy2(file_backup, panel_path)
    raise SystemExit(
        "ERROR: no encontré npm. Archivo restaurado."
    )

build = subprocess.run(
    [npm, "run", "build"],
    cwd=str(ROOT),
    capture_output=True,
    text=True,
    timeout=600,
)

print()
print(build.stdout)

if build.returncode != 0:
    shutil.copy2(file_backup, panel_path)

    print()
    print("CAMBIO REVERTIDO AUTOMÁTICAMENTE")
    print(build.stderr)

    raise SystemExit(1)


# =========================================================
# 7. LIMPIAR CACHÉ
# =========================================================

vite_cache = ROOT / "node_modules" / ".vite"

if vite_cache.exists():
    shutil.rmtree(
        vite_cache,
        ignore_errors=True,
    )


print()
print("=" * 72)
print("LISTO — FRANJA ELIMINADA DEL CÓDIGO FUENTE")
print("=" * 72)

print()
print("Quitado únicamente:")
print("- Enviar foto a Evaluación")
print("- Destino")
print("- Superficie del Puente")
print("- Juntas de dilatación")
print("- Bordillo")
print("- Barandas")
print("- Aletas")
print("- Estribos")
print("- Scroll horizontal de esa fila")

print()
print("No modificado:")
print("- Buscador")
print("- Slider de tamaño")
print("- Miniaturas")
print("- Ver grande y zoom")
print("- Evaluación")
print("- Códigos")
print("- PDF")
print("- Excel")
print("- Backend")

print()
print("BACKUP DEL ARCHIVO:")
print(file_backup)

print()
print("BACKUP COMPLETO:")
print(checkpoint)
