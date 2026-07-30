
from __future__ import annotations


import os

import shutil

import subprocess

import tempfile

import unicodedata

import zipfile


from datetime import datetime

from pathlib import Path

from xml.etree import ElementTree as ET



ALLOWED_EXTENSIONS = {

    ".xlsm",

    ".xlsx",

    ".xls",

    ".xlsb",

    ".ods",
}



MAIN_NS = (

    "http://schemas.openxmlformats.org/"

    "spreadsheetml/2006/main"
)


REL_NS = (

    "http://schemas.openxmlformats.org/"

    "officeDocument/2006/relationships"
)


PKG_REL_NS = (

    "http://schemas.openxmlformats.org/"

    "package/2006/relationships"
)



ET.register_namespace(

    "",

    MAIN_NS,
)


ET.register_namespace(

    "r",

    REL_NS,
)



# =========================================================
# HOJAS QUE DEBEN CABER COMPLETAS
# EN UNA SOLA PÁGINA
# =========================================================

ONE_PAGE_SHEETS = {

    "indice",

    "superficie del tablero",

    "superficie de accesos",

    "juntas de dilatacion",

    "bordillo",

    "anden",

    "barandas",

    "barrera separador",

    "proteccion de talud",

    "proteccion talud",

    "aletas",

    "estribos",

    "pilas pilones",

    "pilas/pilones",

    "macizo",

    "torres de acero",

    "apoyos",

    "losa",

    "vigas",

    "elementos puentes en arco",

    "elementos puentes en armadura",

    "tirante",

    "pendolones",

    "cables",

    "cables y pendolones",

    "taludes y accesos",

    "deslizamiento",

    "socavacion",

    "avenidas torrenciales",

    "senalizacion",
}



def _normalizar(

    value: str,

) -> str:


    text = (

        unicodedata.normalize(

            "NFD",

            str(

                value

                or ""
            ),
        )
    )


    text = "".join(

        char

        for char in text

        if (

            unicodedata.category(

                char

            )

            != "Mn"
        )
    )


    return (

        " ".join(

            text

            .lower()

            .replace(

                "_",

                " "
            )

            .replace(

                "-",

                " "
            )

            .split()
        )
    )



def _is_one_page_sheet(

    sheet_name: str,

) -> bool:


    normalized = (

        _normalizar(

            sheet_name
        )
    )


    if (

        normalized

        in ONE_PAGE_SHEETS

    ):


        return True


    aliases = (

        "superficie del tablero",

        "superficie de accesos",

        "juntas de dilatacion",

        "barrera separador",

        "proteccion de talud",

        "pilas pilones",

        "elementos puentes en arco",

        "elementos puentes en armadura",

        "taludes y accesos",

        "avenidas torrenciales",
    )


    return any(

        alias in normalized

        for alias in aliases
    )



# =========================================================
# BUSCAR LIBREOFFICE
# =========================================================

def _find_soffice() -> Path:


    candidates: list[Path] = []


    configured = (

        os.environ

        .get(

            "SIPUCOL_SOFFICE_PATH",

            "",
        )

        .strip()
    )


    if configured:


        candidates.append(

            Path(

                configured
            )
        )


    for executable_name in (

        "soffice.exe",

        "soffice",

        "libreoffice.exe",

        "libreoffice",

    ):


        found = (

            shutil.which(

                executable_name
            )
        )


        if found:


            candidates.append(

                Path(

                    found
                )
            )


    for environment_name in (

        "ProgramFiles",

        "ProgramFiles(x86)",

    ):


        base_value = (

            os.environ

            .get(

                environment_name
            )
        )


        if not base_value:


            continue


        base = (

            Path(

                base_value
            )
        )


        candidates.extend([

            (

                base

                / "LibreOffice"

                / "program"

                / "soffice.exe"
            ),

            (

                base

                / "LibreOffice 25"

                / "program"

                / "soffice.exe"
            ),

            (

                base

                / "LibreOffice 24"

                / "program"

                / "soffice.exe"
            ),
        ])


    local_app_data = (

        os.environ

        .get(

            "LOCALAPPDATA"
        )
    )


    if local_app_data:


        candidates.append(

            Path(

                local_app_data
            )

            / "Programs"

            / "LibreOffice"

            / "program"

            / "soffice.exe"
        )


    checked: set[str] = set()


    for candidate in candidates:


        key = (

            str(

                candidate

            ).lower()
        )


        if key in checked:


            continue


        checked.add(

            key
        )


        if (

            candidate.exists()

            and

            candidate.is_file()

        ):


            return (

                candidate.resolve()
            )


    raise RuntimeError(

        "LibreOffice no está instalado."
    )



def _decode(

    data: bytes,

) -> str:


    for encoding in (

        "utf-8",

        "mbcs",

        "cp1252",

        "latin-1",

    ):


        try:


            return (

                data.decode(

                    encoding
                )
            )


        except Exception:


            continue


    return (

        data.decode(

            "latin-1",

            errors="replace",
        )
    )



# =========================================================
# UTILIDADES XML
# =========================================================

def _ensure_child(

    root: ET.Element,

    tag_name: str,

    before_tags: tuple[str, ...],

) -> ET.Element:


    full_tag = (

        f"{{{MAIN_NS}}}"

        f"{tag_name}"
    )


    existing = (

        root.find(

            full_tag
        )
    )


    if (

        existing

        is not None

    ):


        return existing


    element = (

        ET.Element(

            full_tag
        )
    )


    children = (

        list(

            root
        )
    )


    before_full = {

        f"{{{MAIN_NS}}}"

        f"{name}"

        for name in before_tags
    }


    for index, child in enumerate(

        children

    ):


        if (

            child.tag

            in before_full

        ):


            root.insert(

                index,

                element,
            )


            return element


    root.append(

        element
    )


    return element



# =========================================================
# CORREGIR CONFIGURACIÓN DE IMPRESIÓN
# =========================================================

def _prepare_sheet_xml(

    xml_bytes: bytes,

    *,

    one_page: bool,

) -> bytes:


    root = (

        ET.fromstring(

            xml_bytes
        )
    )


    # -----------------------------------------------------
    # FIT TO PAGE
    # -----------------------------------------------------

    sheet_pr = (

        root.find(

            f"{{{MAIN_NS}}}"

            "sheetPr"
        )
    )


    if (

        sheet_pr

        is None

    ):


        sheet_pr = (

            ET.Element(

                f"{{{MAIN_NS}}}"

                "sheetPr"
            )
        )


        root.insert(

            0,

            sheet_pr,
        )


    page_setup_pr = (

        sheet_pr.find(

            f"{{{MAIN_NS}}}"

            "pageSetUpPr"
        )
    )


    if (

        page_setup_pr

        is None

    ):


        page_setup_pr = (

            ET.SubElement(

                sheet_pr,

                f"{{{MAIN_NS}}}"

                "pageSetUpPr",
            )
        )


    page_setup_pr.set(

        "fitToPage",

        "1",
    )


    page_setup_pr.set(

        "autoPageBreaks",

        "0",
    )


    # -----------------------------------------------------
    # CENTRAR CONTENIDO
    # -----------------------------------------------------

    print_options = (

        _ensure_child(

            root,

            "printOptions",

            (

                "pageMargins",

                "pageSetup",

                "headerFooter",

                "rowBreaks",

                "colBreaks",

                "drawing",

                "legacyDrawing",

                "legacyDrawingHF",

                "picture",

                "oleObjects",

                "controls",

                "webPublishItems",

                "tableParts",

                "extLst",
            ),
        )
    )


    print_options.set(

        "horizontalCentered",

        "1",
    )


    # -----------------------------------------------------
    # AJUSTAR ANCHO Y ALTO
    # -----------------------------------------------------

    page_setup = (

        _ensure_child(

            root,

            "pageSetup",

            (

                "headerFooter",

                "rowBreaks",

                "colBreaks",

                "customProperties",

                "cellWatches",

                "ignoredErrors",

                "smartTags",

                "drawing",

                "legacyDrawing",

                "legacyDrawingHF",

                "picture",

                "oleObjects",

                "controls",

                "webPublishItems",

                "tableParts",

                "extLst",
            ),
        )
    )


    # Scale entra en conflicto
    # con fitToWidth / fitToHeight.

    page_setup.attrib.pop(

        "scale",

        None,
    )


    # Todas las hojas:
    # una sola página horizontal.

    page_setup.set(

        "fitToWidth",

        "1",
    )


    # Índice y componentes:
    # una sola página vertical.
    #
    # Cálculos y anexos:
    # altura automática.

    page_setup.set(

        "fitToHeight",

        (
            "1"

            if one_page

            else "0"
        ),
    )


    # Primero baja,
    # después pasa a la derecha.
    #
    # Evita páginas angostas
    # generadas por columnas sobrantes.

    page_setup.set(

        "pageOrder",

        "downThenOver",
    )


    page_setup.set(

        "usePrinterDefaults",

        "0",
    )


    # -----------------------------------------------------
    # QUITAR SALTOS HORIZONTALES MANUALES
    # -----------------------------------------------------

    col_breaks = (

        root.find(

            f"{{{MAIN_NS}}}"

            "colBreaks"
        )
    )


    if (

        col_breaks

        is not None

    ):


        root.remove(

            col_breaks
        )


    # -----------------------------------------------------
    # COMPONENTES:
    # QUITAR SALTOS VERTICALES MANUALES
    # -----------------------------------------------------

    if one_page:


        row_breaks = (

            root.find(

                f"{{{MAIN_NS}}}"

                "rowBreaks"
            )
        )


        if (

            row_breaks

            is not None

        ):


            root.remove(

                row_breaks
            )


    return (

        ET.tostring(

            root,

            encoding="utf-8",

            xml_declaration=True,
        )
    )



# =========================================================
# RELACIONAR HOJAS CON SUS XML
# =========================================================

def _sheet_path_map(

    workbook_xml: bytes,

    rels_xml: bytes,

) -> dict[str, str]:


    workbook_root = (

        ET.fromstring(

            workbook_xml
        )
    )


    rels_root = (

        ET.fromstring(

            rels_xml
        )
    )


    targets_by_id: dict[
        str,
        str
    ] = {}


    for relationship in (

        rels_root.findall(

            f"{{{PKG_REL_NS}}}"

            "Relationship"
        )

    ):


        relationship_id = (

            relationship.get(

                "Id",

                "",
            )
        )


        target = (

            relationship.get(

                "Target",

                "",
            )
        )


        if (

            relationship_id

            and

            target

        ):


            targets_by_id[

                relationship_id

            ] = target


    result: dict[
        str,
        str
    ] = {}


    sheets = (

        workbook_root.find(

            f"{{{MAIN_NS}}}"

            "sheets"
        )
    )


    if (

        sheets

        is None

    ):


        return result


    for sheet in (

        sheets.findall(

            f"{{{MAIN_NS}}}"

            "sheet"
        )

    ):


        name = (

            sheet.get(

                "name",

                "",
            )
        )


        relationship_id = (

            sheet.get(

                f"{{{REL_NS}}}"

                "id",

                "",
            )
        )


        target = (

            targets_by_id.get(

                relationship_id,

                "",
            )
        )


        if (

            not name

            or

            not target

        ):


            continue


        if (

            target.startswith(

                "/"
            )

        ):


            zip_path = (

                target.lstrip(

                    "/"
                )
            )


        else:


            zip_path = (

                str(

                    Path(

                        "xl"
                    )

                    / Path(

                        target
                    )
                )

                .replace(

                    "\\",

                    "/",
                )
            )


        result[

            zip_path

        ] = name


    return result



# =========================================================
# OPTIMIZAR XLSX / XLSM
# SIN MODIFICAR EL ORIGINAL
# =========================================================

def _optimizar_ooxml_para_pdf(

    source: Path,

    destination: Path,

) -> None:


    if (

        source.suffix.lower()

        not in {

            ".xlsx",

            ".xlsm",

        }

    ):


        shutil.copy2(

            source,

            destination,
        )


        return


    with zipfile.ZipFile(

        source,

        "r",

    ) as input_zip:


        names = (

            set(

                input_zip.namelist()
            )
        )


        workbook_name = (

            "xl/workbook.xml"
        )


        rels_name = (

            "xl/_rels/"

            "workbook.xml.rels"
        )


        if (

            workbook_name

            not in names

            or

            rels_name

            not in names

        ):


            raise RuntimeError(

                "El Excel no contiene "

                "una estructura "

                "XLSX/XLSM válida."
            )


        sheet_names = (

            _sheet_path_map(

                input_zip.read(

                    workbook_name
                ),

                input_zip.read(

                    rels_name
                ),
            )
        )


        with zipfile.ZipFile(

            destination,

            "w",

        ) as output_zip:


            for item in (

                input_zip.infolist()

            ):


                data = (

                    input_zip.read(

                        item.filename
                    )
                )


                sheet_name = (

                    sheet_names.get(

                        item.filename
                    )
                )


                if (

                    sheet_name

                    is not None

                ):


                    data = (

                        _prepare_sheet_xml(

                            data,

                            one_page=(

                                _is_one_page_sheet(

                                    sheet_name
                                )
                            ),
                        )
                    )


                # Mantiene macros,
                # estilos,
                # relaciones,
                # imágenes,
                # fórmulas
                # y propiedades.

                output_zip.writestr(

                    item,

                    data,
                )



# =========================================================
# VALIDAR PDF
# =========================================================

def _validate_pdf(

    path: Path,

) -> None:


    if (

        not path.exists()

        or

        not path.is_file()

    ):


        raise RuntimeError(

            "LibreOffice terminó "

            "sin crear el PDF."
        )


    if (

        path

        .stat()

        .st_size

        < 5000

    ):


        raise RuntimeError(

            "El PDF quedó vacío "

            "o incompleto."
        )


    with path.open(

        "rb"

    ) as file:


        header = (

            file.read(

                5
            )
        )


    if (

        header

        != b"%PDF-"

    ):


        raise RuntimeError(

            "El archivo generado "

            "no es un PDF válido."
        )



# =========================================================
# JOB PRINCIPAL
# =========================================================

def convertir_excel_seleccionado_job(

    job_id: str,

    excel_path: str,

    pdf_path: str,

) -> None:


    from backend import server


    temp_root: Path | None = None


    try:


        source = (

            Path(

                excel_path
            )

            .resolve()
        )


        output = (

            Path(

                pdf_path
            )

            .resolve()
        )


        server.log(

            "=" * 70
        )


        server.log(

            f"Job {job_id}: "

            "PDF LIBREOFFICE - "

            "MAQUETACIÓN FINA V2"
        )


        server.log(

            f"Excel origen: "

            f"{source}"
        )


        server.log(

            f"PDF destino: "

            f"{output}"
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

                "seleccionado:\n"

                f"{source}"
            )


        extension = (

            source

            .suffix

            .lower()
        )


        if (

            extension

            not in

            ALLOWED_EXTENSIONS

        ):


            raise RuntimeError(

                "Formato no compatible: "

                + extension
            )


        soffice = (

            _find_soffice()
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

            progress=8,

            message=(

                "Preparando el Excel "

                "para impresión..."
            ),

            source_excel=str(

                source
            ),

            output_path=str(

                output
            ),
        )


        temp_root = (

            Path(

                tempfile.mkdtemp(

                    prefix=(

                        "sipucol_pdf_"

                        "layout_v2_"
                    )
                )
            )
        )


        input_directory = (

            temp_root

            / "input"
        )


        output_directory = (

            temp_root

            / "output"
        )


        profile_directory = (

            temp_root

            / "profile"
        )


        input_directory.mkdir(

            parents=True,

            exist_ok=True,
        )


        output_directory.mkdir(

            parents=True,

            exist_ok=True,
        )


        profile_directory.mkdir(

            parents=True,

            exist_ok=True,
        )


        local_excel = (

            input_directory

            / (

                "informe_optimizado"

                + extension
            )
        )


        # -------------------------------------------------
        # SOLO MODIFICA LA COPIA TEMPORAL
        # -------------------------------------------------

        _optimizar_ooxml_para_pdf(

            source,

            local_excel,
        )


        if (

            not local_excel.exists()

            or

            local_excel

            .stat()

            .st_size

            < 1000

        ):


            raise RuntimeError(

                "La copia optimizada "

                "del Excel quedó "

                "incompleta."
            )


        server.set_job(

            job_id,

            progress=32,

            message=(

                "Ajustando tablas, "

                "índice y saltos "

                "de página..."
            ),
        )


        profile_uri = (

            profile_directory

            .resolve()

            .as_uri()
        )


        command = [

            str(

                soffice
            ),

            (

                "-env:"

                "UserInstallation="

                + profile_uri
            ),

            "--headless",

            "--nologo",

            "--nodefault",

            "--nofirststartwizard",

            "--nolockcheck",

            "--convert-to",

            "pdf:calc_pdf_Export",

            "--outdir",

            str(

                output_directory
            ),

            str(

                local_excel
            ),
        ]


        server.log(

            "Comando PDF: "

            + " ".join(

                command
            )
        )


        result = (

            subprocess.run(

                command,

                capture_output=True,

                timeout=1200,

                creationflags=(

                    getattr(

                        subprocess,

                        "CREATE_NO_WINDOW",

                        0,
                    )
                ),
            )
        )


        stdout = (

            _decode(

                result.stdout
            )

            .strip()
        )


        stderr = (

            _decode(

                result.stderr
            )

            .strip()
        )


        if stdout:


            server.log(

                "LibreOffice stdout: "

                + stdout
            )


        if stderr:


            server.log(

                "LibreOffice stderr: "

                + stderr
            )


        pdf_candidates = (

            sorted(

                output_directory

                .glob(

                    "*.pdf"
                ),

                key=(

                    lambda item:

                    item

                    .stat()

                    .st_mtime
                ),

                reverse=True,
            )
        )


        if not pdf_candidates:


            detail = (

                stderr

                or

                stdout

                or

                (

                    "Código de salida: "

                    + str(

                        result.returncode
                    )
                )
            )


            raise RuntimeError(

                "LibreOffice no pudo "

                "convertir el Excel.\n"

                + detail
            )


        generated_pdf = (

            pdf_candidates[0]
        )


        _validate_pdf(

            generated_pdf
        )


        server.set_job(

            job_id,

            progress=88,

            message=(

                "Guardando el PDF "

                "optimizado..."
            ),
        )


        shutil.copy2(

            generated_pdf,

            output,
        )


        _validate_pdf(

            output
        )


        report_path = (

            output

            .with_suffix(

                ".conversion_report.txt"
            )
        )


        report_path.write_text(

            "\n".join([

                (

                    "REPORTE DE "

                    "CONVERSIÓN "

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

                "Excel origen:",

                str(

                    source
                ),

                "",

                "PDF creado:",

                str(

                    output
                ),

                "",

                "Motor:",

                "LibreOffice",

                str(

                    soffice
                ),

                "",

                "Perfil de impresión:",

                (

                    "SIPUCOL Layout Fino V2"
                ),

                (

                    "- Índice: una página."
                ),

                (

                    "- Componentes: "

                    "una página de ancho "

                    "y una de alto."
                ),

                (

                    "- Cálculos y anexos: "

                    "una página de ancho "

                    "y altura automática."
                ),

                (

                    "- Saltos verticales "

                    "extra eliminados."
                ),
            ]),

            encoding="utf-8",
        )


        server.set_job(

            job_id,

            status="done",

            progress=100,

            message=(

                "PDF creado con "

                "maquetación optimizada."
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

            f"PDF LISTO -> "

            f"{output}"
        )


    except subprocess.TimeoutExpired:


        error = (

            "La conversión superó "

            "20 minutos. "

            "Cierra LibreOffice "

            "y vuelve a intentar."
        )


        server.set_job(

            job_id,

            status="error",

            progress=0,

            message=(

                "No se pudo "

                "crear el PDF"
            ),

            error=error,
        )


        server.log(

            f"Job {job_id}: "

            f"ERROR PDF -> "

            f"{error}"
        )


    except Exception as error:


        server.set_job(

            job_id,

            status="error",

            progress=0,

            message=(

                "No se pudo "

                "crear el PDF"
            ),

            error=str(

                error
            ),
        )


        server.log(

            f"Job {job_id}: "

            f"ERROR PDF -> "

            f"{error}"
        )


    finally:


        if (

            temp_root

            is not None

        ):


            shutil.rmtree(

                temp_root,

                ignore_errors=True,
            )
