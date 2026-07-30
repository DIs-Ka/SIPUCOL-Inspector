from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path.cwd().resolve()
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

BACKUPS.mkdir(
    parents=True,
    exist_ok=True,
)


def read_text(path: Path) -> str:
    return path.read_text(
        encoding="utf-8-sig",
        errors="strict",
    ).replace(
        "\r\n",
        "\n",
    )


def create_backup(label: str) -> Path:
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


def find_last_function_range(
    source: str,
    function_name: str,
) -> tuple[int, int]:

    matches = list(
        re.finditer(
            rf"(?m)^def\s+{re.escape(function_name)}\s*\(",
            source,
        )
    )

    if not matches:
        raise RuntimeError(
            f"No encontré la función {function_name}."
        )

    start = matches[-1].start()

    next_function = re.search(
        r"(?m)^def\s+[A-Za-z_][A-Za-z0-9_]*\s*\(",
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
        end = len(source)

    return start, end


if not SERVER.exists():
    raise SystemExit(
        f"ERROR: no encontré {SERVER}"
    )


# ============================================================
# 1. BACKUP DE LA BASE CANÓNICA ACTUAL
# ============================================================

backup_before = create_backup(
    "SIPUCOL_BASE_CANONICA_ANTES_PDF_COMPONENTES_MAS_CALCULO_IC"
)

server_original = SERVER.read_bytes()

print()
print("=" * 72)
print("BACKUP CANÓNICO CREADO")
print("=" * 72)
print(backup_before)


try:
    code = read_text(
        SERVER
    )

    function_start, function_end = (
        find_last_function_range(
            code,
            "hojas_pdf_desde_reporte_v2",
        )
    )

    new_function = '''def hojas_pdf_desde_reporte_v2(
    report
):
    """
    Selección definitiva de hojas para el PDF:

    1. Únicamente componentes diligenciados.
    2. Sin Índice ni nota inicial.
    3. Sin Evaluación ni anexos.
    4. CALCULO IC siempre al final.
    """

    touched = (
        report.get(
            "sheets_touched"
        )
        or []
    )

    component_sheets = []
    seen = set()

    for name in touched:
        clean = str(
            name
            or ""
        ).strip()

        key = normalizar(
            clean
        )

        if not clean:
            continue

        # Estas hojas nunca deben entrar como
        # tablas de componentes.
        if (
            key in {
                "indice",
                "evaluacion",
                "calculo ic",
            }
            or "anexo" in key
            or key.startswith("anx")
        ):
            continue

        if key in seen:
            continue

        seen.add(
            key
        )

        component_sheets.append(
            clean
        )

    # CALCULO IC sí se conserva, pero no se permite
    # generar un PDF sin ninguna tabla diligenciada.
    if not component_sheets:
        raise RuntimeError(
            "No hay componentes diligenciados para generar el PDF. "
            "Rellena al menos una severidad, número de fotos, "
            "ubicación u observación."
        )

    return [
        *component_sheets,
        "CALCULO IC",
    ]


'''

    updated = (
        code[:function_start]
        + new_function
        + code[function_end:]
    )

    SERVER.write_text(
        updated,
        encoding="utf-8",
        newline="\n",
    )

    # ========================================================
    # 2. VALIDAR SINTAXIS
    # ========================================================

    print()
    print("Validando backend...")

    compile_result = subprocess.run(
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

    if compile_result.returncode != 0:
        raise RuntimeError(
            compile_result.stderr
        )

    # ========================================================
    # 3. PROBAR LA FUNCIÓN ACTIVA
    # ========================================================

    test_code = r'''
from backend import server


func = server.hojas_pdf_desde_reporte_v2


resultado = func({
    "sheets_touched": [
        "Superficie del tablero",
        "ÍNDICE",
        "Juntas de dilatación",
        "ANX 1",
        "Evaluación",
        "CALCULO IC",
        "Superficie del tablero",
    ]
})


esperado = [
    "Superficie del tablero",
    "Juntas de dilatación",
    "CALCULO IC",
]


if resultado != esperado:
    raise RuntimeError(
        f"Selección incorrecta: {resultado}"
    )


if resultado[-1] != "CALCULO IC":
    raise RuntimeError(
        "CALCULO IC no quedó al final."
    )


prohibidas = {
    "indice",
    "índice",
    "evaluacion",
    "evaluación",
    "anx 1",
}


for hoja in resultado[:-1]:

    if hoja.strip().casefold() in prohibidas:

        raise RuntimeError(
            f"Entró una hoja prohibida: {hoja}"
        )


try:

    func({
        "sheets_touched": []
    })

except RuntimeError:

    pass

else:

    raise RuntimeError(
        "La función permitió crear un PDF "
        "sin componentes diligenciados."
    )


print("OK backend.server")
print("SELECCIÓN:", resultado)
print("ÍNDICE EXCLUIDO")
print("ANEXOS EXCLUIDOS")
print("EVALUACIÓN EXCLUIDA")
print("CALCULO IC CONSERVADO AL FINAL")
print("PDF SIN COMPONENTES BLOQUEADO")
'''

    test_result = subprocess.run(
        [
            "py",
            "-c",
            test_code,
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
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
    # 4. COMPROBACIÓN DEL ARCHIVO ACTIVO
    # ========================================================

    final_code = read_text(
        SERVER
    )

    active_start, active_end = (
        find_last_function_range(
            final_code,
            "hojas_pdf_desde_reporte_v2",
        )
    )

    active_source = final_code[
        active_start:active_end
    ]

    required_markers = [
        '"sheets_touched"',
        "component_sheets",
        '"CALCULO IC"',
        "if not component_sheets:",
        "No hay componentes diligenciados",
    ]

    for marker in required_markers:

        if marker not in active_source:

            raise RuntimeError(
                "No quedó instalada la regla: "
                + marker
            )

    forbidden_candidates = [
        '"ÍNDICE",',
        '"Índice",',
    ]

    for marker in forbidden_candidates:

        if marker in active_source:

            raise RuntimeError(
                "El Índice todavía aparece "
                "como hoja candidata."
            )

except Exception as error:

    SERVER.write_bytes(
        server_original
    )

    print()
    print("=" * 72)
    print("ERROR — SERVER.PY RESTAURADO AUTOMÁTICAMENTE")
    print("=" * 72)
    print(error)

    raise SystemExit(1)


# ============================================================
# 5. LIMPIAR CACHÉ PYTHON
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
# 6. BACKUP FINAL
# ============================================================

backup_after = create_backup(
    "SIPUCOL_BASE_CANONICA_PDF_COMPONENTES_MAS_CALCULO_IC"
)

checkpoint = (
    ROOT
    / f"CHECKPOINT_PDF_COMPONENTES_MAS_CALCULO_IC_{STAMP}.txt"
)

checkpoint.write_text(
    "\n".join([
        "SIPUCOL — BASE CANÓNICA",
        "=" * 72,
        "",
        f"Fecha: {datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        "Regla PDF definitiva:",
        "- Solo componentes diligenciados.",
        "- Índice y nota inicial excluidos.",
        "- Evaluación excluida.",
        "- Anexos excluidos.",
        "- Componentes vacíos excluidos.",
        "- CALCULO IC conservado siempre al final.",
        "- PDF sin componentes diligenciados bloqueado.",
        "",
        "No modificado:",
        "- Exportación Excel.",
        "- Motor PDF estable.",
        "- Maquetación y escalado.",
        "- Fotos.",
        "- Códigos.",
        "- Evaluación.",
        "- Autoguardado.",
        "- Identificación.",
        "",
        "Backup anterior:",
        str(backup_before),
        "",
        "Backup final:",
        str(backup_after),
    ]),
    encoding="utf-8",
)

print()
print("=" * 72)
print("PDF FILTRADO + CALCULO IC — INSTALADO")
print("=" * 72)

print()
print("Orden del PDF:")
print("1. Primera tabla de componente diligenciado.")
print("2. Resto de componentes diligenciados.")
print("3. CALCULO IC al final.")

print()
print("Excluido:")
print("- Índice y nota inicial.")
print("- Tablas de componentes vacías.")
print("- Evaluación.")
print("- Anexos.")

print()
print("Se considera componente diligenciado cuando contiene:")
print("- Severidad.")
print("- Número de fotos.")
print("- Ubicación.")
print("- Observación del levantamiento.")
print("- Observación del revisor/equipo técnico.")

print()
print("No modificado:")
print("- Guardar Excel.")
print("- Motor LibreOffice.")
print("- Diseño y escala actual del PDF.")
print("- Resto de la aplicación.")

print()
print("BACKUP ANTERIOR:")
print(backup_before)

print()
print("BACKUP FINAL:")
print(backup_after)

print()
print("CHECKPOINT:")
print(checkpoint)
