from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path


def _decode_output(
    data: bytes,
) -> str:

    encodings = (
        "utf-8",
        "mbcs",
        "cp1252",
        "latin-1",
    )

    for encoding in encodings:

        try:

            return data.decode(
                encoding
            )

        except Exception:

            continue

    return data.decode(
        "latin-1",
        errors="replace",
    )


def _validate_pdf(
    path: Path,
) -> None:

    if not path.exists():

        raise RuntimeError(
            "Microsoft Excel terminó "
            "sin crear el PDF."
        )

    if path.stat().st_size < 5000:

        raise RuntimeError(
            "El PDF creado está vacío "
            "o incompleto."
        )

    with path.open(
        "rb"
    ) as file:

        header = file.read(
            5
        )

    if header != b"%PDF-":

        raise RuntimeError(
            "El archivo creado "
            "no es un PDF válido."
        )


def convertir_excel_seleccionado_job(
    job_id: str,
    excel_path: str,
    pdf_path: str,
) -> None:

    from backend import server

    temp_dir: Path | None = None

    try:

        source = Path(
            excel_path
        )

        output = Path(
            pdf_path
        )

        server.log(
            "=" * 70
        )

        server.log(
            f"Job {job_id}: "
            "PDF DESDE EXCEL "
            "SELECCIONADO - MOTOR VBS"
        )

        server.log(
            f"Excel origen: {source}"
        )

        server.log(
            f"PDF destino: {output}"
        )

        server.log(
            "=" * 70
        )


        if (
            not source.exists()
            or
            not source.is_file()
        ):

            raise RuntimeError(
                "No existe el Excel "
                f"seleccionado: {source}"
            )


        allowed_extensions = {
            ".xlsm",
            ".xlsx",
            ".xls",
            ".xlsb",
        }


        if (
            source.suffix.lower()
            not in allowed_extensions
        ):

            raise RuntimeError(
                "Formato de Excel "
                "no compatible: "
                f"{source.suffix}"
            )


        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )


        if output.exists():

            output.unlink()


        server.set_job(

            job_id,

            status="running",

            progress=10,

            message=(
                "Preparando una copia "
                "local del Excel..."
            ),

            source_excel=str(
                source
            ),

            output_path=str(
                output
            ),
        )


        temp_dir = Path(

            tempfile.mkdtemp(
                prefix="sipucol_pdf_"
            )
        )


        local_excel = (

            temp_dir
            / (
                "source"
                + source.suffix.lower()
            )
        )


        local_pdf = (

            temp_dir
            / "output.pdf"
        )


        shutil.copy2(

            source,

            local_excel,
        )


        if (
            not local_excel.exists()
            or
            local_excel.stat().st_size
            < 1000
        ):

            raise RuntimeError(
                "No se pudo crear "
                "una copia local válida "
                "del Excel."
            )


        script_path = (

            Path(
                server.BASE_DIR
            )

            / "backend"

            / (
                "convert_selected_"
                "excel_to_pdf.vbs"
            )
        )


        if not script_path.exists():

            raise RuntimeError(
                "No se encontró "
                "el motor VBS."
            )


        windows_dir = (

            os.environ.get(
                "WINDIR"
            )

            or r"C:\Windows"
        )


        cscript_path = (

            Path(
                windows_dir
            )

            / "System32"

            / "cscript.exe"
        )


        if not cscript_path.exists():

            raise RuntimeError(
                "No se encontró "
                "cscript.exe."
            )


        server.set_job(

            job_id,

            progress=35,

            message=(
                "Microsoft Excel está "
                "abriendo el archivo..."
            ),
        )


        command = [

            str(
                cscript_path
            ),

            "//nologo",

            str(
                script_path
            ),

            str(
                local_excel
            ),

            str(
                local_pdf
            ),
        ]


        result = subprocess.run(

            command,

            capture_output=True,

            timeout=600,

            creationflags=getattr(

                subprocess,

                "CREATE_NO_WINDOW",

                0,
            ),
        )


        stdout = _decode_output(

            result.stdout

        ).strip()


        stderr = _decode_output(

            result.stderr

        ).strip()


        if stdout:

            server.log(

                f"Job {job_id}: "
                f"VBS stdout: {stdout}"
            )


        if stderr:

            server.log(

                f"Job {job_id}: "
                f"VBS stderr: {stderr}"
            )


        if result.returncode != 0:

            detail = (

                stderr

                or stdout

                or (
                    "Microsoft Excel "
                    "no pudo crear el PDF."
                )
            )


            if "ERROR=" in detail:

                detail = (

                    detail
                    .split(
                        "ERROR=",
                        1,
                    )[1]
                    .strip()
                )


            raise RuntimeError(
                detail
            )


        server.set_job(

            job_id,

            progress=80,

            message=(
                "Validando el PDF "
                "creado por Excel..."
            ),
        )


        _validate_pdf(
            local_pdf
        )


        shutil.copy2(

            local_pdf,

            output,
        )


        server.set_job(

            job_id,

            progress=94,

            message=(
                "Validando el archivo "
                "en su ubicación final..."
            ),
        )


        _validate_pdf(
            output
        )


        report_path = (

            output.with_suffix(
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
                    source
                ),

                "",

                (
                    "PDF creado:"
                ),

                str(
                    output
                ),

                "",

                (
                    "Motor:"
                ),

                (
                    "Microsoft Excel "
                    "mediante VBScript"
                ),

                "",

                (
                    "El Excel se copió "
                    "temporalmente fuera "
                    "de OneDrive."
                ),

                (
                    "Excel conservó sus "
                    "hojas visibles, áreas "
                    "de impresión, escala, "
                    "orientación y saltos "
                    "de página."
                ),
            ]),

            encoding="utf-8",
        )


        server.set_job(

            job_id,

            status="done",

            progress=100,

            message=(
                "PDF creado correctamente "
                "desde el Excel seleccionado."
            ),

            source_excel=str(
                source
            ),

            output_path=str(
                output
            ),

            report_path=str(
                report_path
            ),
        )


        server.log(

            f"Job {job_id}: "
            f"PDF LISTO -> {output}"
        )


    except Exception as error:

        server.set_job(

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


        server.log(

            f"Job {job_id}: "
            f"ERROR PDF -> {error}"
        )


    finally:

        if temp_dir is not None:

            shutil.rmtree(

                temp_dir,

                ignore_errors=True,
            )
