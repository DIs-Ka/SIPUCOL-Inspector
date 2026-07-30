from __future__ import annotations

import hashlib
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path.cwd()

STAMP = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

ZIP_PATH = (
    ROOT
    / f"DIAGNOSTICO_SIPUCOL_{STAMP}.zip"
)

REPORT_LINES: list[str] = []


def add_report(
    text: str = "",
) -> None:

    REPORT_LINES.append(
        str(
            text
        )
    )


def is_excluded(
    path: Path,
) -> bool:

    excluded_parts = {
        "node_modules",
        ".git",
        "dist",
        "__pycache__",
        "backups",
        ".venv",
        ".sipucol_runtime",
    }

    if any(
        part in excluded_parts
        for part in path.parts
    ):

        return True

    lower_name = (
        path.name.lower()
    )

    if (
        "backup" in lower_name
        or
        "broken" in lower_name
    ):

        return True

    return False


def sha256_file(
    path: Path,
) -> str:

    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as file:

        while True:

            chunk = file.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def select_excel() -> Path | None:

    try:

        import tkinter as tk

        from tkinter import filedialog


        root = tk.Tk()

        root.withdraw()

        root.attributes(
            "-topmost",
            True
        )

        root.update()


        selected = (
            filedialog
            .askopenfilename(

                title=(
                    "Selecciona el Excel "
                    "exacto que falla "
                    "al crear el PDF"
                ),

                filetypes=[

                    (
                        "Archivos Excel",
                        "*.xlsm *.xlsx *.xls *.xlsb"
                    ),

                    (
                        "Todos los archivos",
                        "*.*"
                    ),
                ],
            )
        )


        root.destroy()


        if not selected:

            return None


        return Path(
            selected
        )


    except Exception as error:

        add_report(
            "ERROR ABRIENDO SELECTOR:"
        )

        add_report(
            repr(
                error
            )
        )

        return None


def inspect_excel(
    path: Path,
) -> None:

    add_report()

    add_report(
        "=" * 72
    )

    add_report(
        "EXCEL SELECCIONADO"
    )

    add_report(
        "=" * 72
    )

    add_report(
        f"Ruta: {path}"
    )

    add_report(
        f"Existe: {path.exists()}"
    )


    if not path.exists():

        return


    add_report(
        f"Tamaño: {path.stat().st_size} bytes"
    )

    add_report(
        f"Extensión: {path.suffix.lower()}"
    )

    add_report(
        f"SHA256: {sha256_file(path)}"
    )


    if (
        path.suffix.lower()
        not in {
            ".xlsx",
            ".xlsm",
        }
    ):

        add_report(
            "No se valida como ZIP OOXML "
            "porque no es XLSX/XLSM."
        )

        return


    is_zip = (
        zipfile.is_zipfile(
            path
        )
    )


    add_report(
        f"Es contenedor ZIP válido: {is_zip}"
    )


    if not is_zip:

        add_report(
            "RESULTADO: "
            "el archivo no tiene "
            "una estructura XLSX/XLSM válida."
        )

        return


    try:

        with zipfile.ZipFile(
            path,
            "r",
        ) as archive:

            bad_file = (
                archive.testzip()
            )


            add_report(
                "Primer archivo interno dañado: "
                f"{bad_file}"
            )


            names = set(
                archive.namelist()
            )


            required = [
                "[Content_Types].xml",
                "xl/workbook.xml",
                "_rels/.rels",
            ]


            for item in required:

                add_report(
                    f"{item}: "
                    f"{item in names}"
                )


            add_report(
                "Cantidad de archivos internos: "
                f"{len(names)}"
            )


            worksheet_count = len([
                name
                for name in names
                if (
                    name.startswith(
                        "xl/worksheets/"
                    )
                    and
                    name.endswith(
                        ".xml"
                    )
                )
            ])


            add_report(
                "Hojas XML encontradas: "
                f"{worksheet_count}"
            )


    except Exception as error:

        add_report(
            "ERROR LEYENDO EL EXCEL:"
        )

        add_report(
            repr(
                error
            )
        )


def inspect_main() -> None:

    main_path = (
        ROOT
        / "src"
        / "main.jsx"
    )


    add_report()

    add_report(
        "=" * 72
    )

    add_report(
        "IMPORTS ACTIVOS EN MAIN.JSX"
    )

    add_report(
        "=" * 72
    )


    if not main_path.exists():

        add_report(
            "No existe src/main.jsx"
        )

        return


    for line in (
        main_path
        .read_text(
            encoding="utf-8",
            errors="replace",
        )
        .splitlines()
    ):

        if (
            line.strip()
            .startswith(
                "import "
            )
        ):

            add_report(
                line
            )


def inspect_keywords() -> None:

    patterns = [
        "Máximo 2 dígitos",
        "ID Puente",
        "Enviar foto a Evaluación",
        "Enviar foto a Evaluacion",
        "pdf-from-selected-excel",
        "convertir_excel_seleccionado_job",
        "Workbooks.Open",
        "ExportAsFixedFormat",
        "source.xlsm",
    ]


    add_report()

    add_report(
        "=" * 72
    )

    add_report(
        "COINCIDENCIAS IMPORTANTES"
    )

    add_report(
        "=" * 72
    )


    roots = [
        ROOT / "src",
        ROOT / "backend",
    ]


    extensions = {
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".py",
        ".ps1",
        ".vbs",
    }


    for base in roots:

        if not base.exists():

            continue


        for path in base.rglob(
            "*"
        ):

            if (
                not path.is_file()
                or
                path.suffix.lower()
                not in extensions
                or
                is_excluded(
                    path
                )
            ):

                continue


            try:

                lines = (
                    path
                    .read_text(
                        encoding="utf-8",
                        errors="replace",
                    )
                    .splitlines()
                )


            except Exception:

                continue


            for number, line in enumerate(
                lines,
                start=1,
            ):

                if any(
                    pattern.lower()
                    in line.lower()
                    for pattern in patterns
                ):

                    relative = (
                        path
                        .relative_to(
                            ROOT
                        )
                    )


                    add_report(
                        f"{relative}:{number}"
                    )

                    add_report(
                        line
                    )

                    add_report()


def inspect_active_pdf_engine() -> None:

    add_report()

    add_report(
        "=" * 72
    )

    add_report(
        "MOTOR PDF CARGADO REALMENTE"
    )

    add_report(
        "=" * 72
    )


    result = subprocess.run(

        [
            sys.executable,

            "-c",

            (
                "import backend.server as s; "
                "print("
                "s.convertir_excel_seleccionado_job"
                ".__module__"
                ")"
            ),
        ],

        cwd=str(
            ROOT
        ),

        capture_output=True,

        text=True,
    )


    add_report(
        f"Código de salida: "
        f"{result.returncode}"
    )


    add_report(
        "STDOUT:"
    )

    add_report(
        result.stdout.strip()
    )


    add_report(
        "STDERR:"
    )

    add_report(
        result.stderr.strip()
    )


def collect_files(
    archive: zipfile.ZipFile,
) -> None:

    allowed_roots = [
        ROOT / "src",
        ROOT / "backend",
    ]


    standalone = [
        ROOT / "package.json",
        ROOT / "RUN_SIPUCOL_ESTABLE.ps1",
    ]


    for path in standalone:

        if path.exists():

            archive.write(

                path,

                (
                    Path(
                        "proyecto"
                    )

                    / path.relative_to(
                        ROOT
                    )
                ),
            )


    extensions = {
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".py",
        ".ps1",
        ".vbs",
        ".json",
    }


    for base in allowed_roots:

        if not base.exists():

            continue


        for path in base.rglob(
            "*"
        ):

            if (
                not path.is_file()
                or
                path.suffix.lower()
                not in extensions
                or
                is_excluded(
                    path
                )
            ):

                continue


            archive.write(

                path,

                (
                    Path(
                        "proyecto"
                    )

                    / path.relative_to(
                        ROOT
                    )
                ),
            )


selected_excel = (
    select_excel()
)


add_report(
    "DIAGNÓSTICO SIPUCOL"
)

add_report(
    f"Fecha: "
    f"{datetime.now():%Y-%m-%d %H:%M:%S}"
)


inspect_main()

inspect_keywords()

inspect_active_pdf_engine()


if selected_excel is not None:

    inspect_excel(
        selected_excel
    )

else:

    add_report()

    add_report(
        "No se seleccionó un Excel."
    )


with zipfile.ZipFile(

    ZIP_PATH,

    "w",

    compression=(
        zipfile.ZIP_DEFLATED
    ),

) as archive:

    collect_files(
        archive
    )


    archive.writestr(

        "REPORTE_DIAGNOSTICO.txt",

        "\n".join(
            REPORT_LINES
        ),
    )


    if (
        selected_excel is not None
        and
        selected_excel.exists()
    ):

        archive.write(

            selected_excel,

            (
                Path(
                    "excel_que_falla"
                )

                / selected_excel.name
            ),
        )


print()

print(
    "=" * 72
)

print(
    "DIAGNÓSTICO CREADO"
)

print(
    "=" * 72
)

print(
    ZIP_PATH
)

print()

print(
    "Adjunta ese ZIP en el chat."
)
