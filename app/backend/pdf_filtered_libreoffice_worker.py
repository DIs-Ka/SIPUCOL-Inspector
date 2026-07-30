from __future__ import annotations

import json
import re
import shutil
import tempfile
import unicodedata
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from backend import pdf_libreoffice_worker as stable_worker


MAIN_NS = (
    "http://schemas.openxmlformats.org/"
    "spreadsheetml/2006/main"
)

DOCUMENT_REL_NS = (
    "http://schemas.openxmlformats.org/"
    "officeDocument/2006/relationships"
)


ET.register_namespace(
    "",
    MAIN_NS,
)

ET.register_namespace(
    "r",
    DOCUMENT_REL_NS,
)


def _normalize(
    value,
) -> str:

    text = unicodedata.normalize(
        "NFD",
        str(value or ""),
    )

    text = "".join(
        character
        for character in text
        if unicodedata.category(
            character
        ) != "Mn"
    )

    return re.sub(
        r"[^a-z0-9]+",
        "",
        text.lower(),
    )


def _is_index(
    name,
) -> bool:

    return _normalize(
        name
    ) in {
        "indice",
        "index",
    }


def _is_calculo_ic(
    name,
) -> bool:

    return _normalize(
        name
    ) in {
        "calculoic",
        "calculodelic",
        "calculodeic",
        "indicedecondicion",
    }


def _is_evaluation(
    name,
) -> bool:

    return _normalize(
        name
    ) in {
        "evaluacion",
        "evaluation",
    }


def _is_annex(
    name,
) -> bool:

    normalized = _normalize(
        name
    )

    return (
        normalized.startswith(
            "anx"
        )
        or normalized.startswith(
            "anexo"
        )
        or normalized.startswith(
            "annex"
        )
    )


def _is_system_sheet(
    name,
) -> bool:

    return (
        _is_index(
            name
        )
        or _is_calculo_ic(
            name
        )
        or _is_evaluation(
            name
        )
        or _is_annex(
            name
        )
    )


def _report_candidates(
    excel_path: Path,
) -> list[Path]:

    candidates = [
        excel_path.with_suffix(
            ".export_report.json"
        ),
        excel_path.parent
        / (
            excel_path.stem
            + ".export_report.json"
        ),
        excel_path.parent
        / (
            excel_path.name
            + ".export_report.json"
        ),
    ]

    unique = []
    seen = set()

    for candidate in candidates:

        key = str(
            candidate.resolve()
        ).lower()

        if key in seen:
            continue

        seen.add(
            key
        )

        unique.append(
            candidate
        )

    return unique


def _components_from_report(
    excel_path: Path,
) -> list[str]:
    """
    Obtiene exclusivamente componentes que recibieron
    contenido real durante la exportación del Excel.

    No utiliza sheets_touched porque la interfaz envía
    todos los componentes, incluso los completamente vacíos.

    Se considera contenido real:
    - severidad escrita;
    - número de fotos escrito;
    - ubicación escrita;
    - observación del levantamiento;
    - observación del revisor.
    """

    allowed_fields = {
        "severidad",
        "fotos",
        "ubicacion",
    }

    for report_path in _report_candidates(
        excel_path
    ):

        if not report_path.exists():
            continue

        try:

            report = json.loads(
                report_path.read_text(
                    encoding="utf-8-sig",
                )
            )

        except Exception:

            continue

        # Evita usar por error un reporte correspondiente
        # a otro Excel con nombre parecido.
        report_output = str(
            report.get(
                "output"
            )
            or ""
        ).strip()

        if report_output:

            try:

                report_output_path = Path(
                    report_output
                ).resolve()

                if (
                    report_output_path
                    != excel_path.resolve()
                ):

                    continue

            except Exception:

                continue

        selected = []
        seen = set()

        def add_sheet(
            value,
        ) -> None:

            clean = str(
                value
                or ""
            ).strip()

            normalized = _normalize(
                clean
            )

            if (
                not clean
                or not normalized
                or normalized in seen
                or _is_system_sheet(
                    clean
                )
            ):

                return

            seen.add(
                normalized
            )

            selected.append(
                clean
            )

        # written_items contiene todas las filas procesadas,
        # pero solamente una acción "write" indica que el
        # usuario realmente rellenó ese campo.
        for item in (
            report.get(
                "written_items"
            )
            or []
        ):

            has_real_write = False

            for write in (
                item.get(
                    "writes"
                )
                or []
            ):

                action = str(
                    write.get(
                        "action"
                    )
                    or ""
                ).strip().lower()

                field = str(
                    write.get(
                        "field"
                    )
                    or ""
                ).strip().lower()

                value = str(
                    write.get(
                        "value"
                    )
                    or ""
                ).strip()

                if (
                    action == "write"
                    and field in allowed_fields
                    and value
                ):

                    has_real_write = True
                    break

            if has_real_write:

                add_sheet(
                    item.get(
                        "sheet"
                    )
                )

        # Esta lista únicamente recibe entradas cuando la
        # observación tiene un valor real.
        for observation in (
            report.get(
                "observations_written"
            )
            or []
        ):

            value = str(
                observation.get(
                    "value"
                )
                or ""
            ).strip()

            if value:

                add_sheet(
                    observation.get(
                        "sheet"
                    )
                )

        return selected

    return []


def _read_shared_strings(
    archive: zipfile.ZipFile,
) -> list[str]:

    path = (
        "xl/sharedStrings.xml"
    )

    if path not in archive.namelist():

        return []

    root = ET.fromstring(
        archive.read(
            path
        )
    )

    strings = []

    for item in root.findall(
        f"{{{MAIN_NS}}}si"
    ):

        text = "".join(
            node.text or ""
            for node in item.iter(
                f"{{{MAIN_NS}}}t"
            )
        )

        strings.append(
            text
        )

    return strings


def _cell_value(
    cell,
    shared_strings: list[str],
) -> str:

    cell_type = cell.attrib.get(
        "t",
        "",
    )

    if cell_type == "inlineStr":

        return "".join(
            node.text or ""
            for node in cell.iter(
                f"{{{MAIN_NS}}}t"
            )
        ).strip()

    value_node = cell.find(
        f"{{{MAIN_NS}}}v"
    )

    if (
        value_node is None
        or value_node.text is None
    ):

        return ""

    raw = value_node.text.strip()

    if cell_type == "s":

        try:

            index = int(
                raw
            )

            return shared_strings[
                index
            ].strip()

        except Exception:

            return ""

    return raw


def _worksheet_values(
    archive: zipfile.ZipFile,
    worksheet_path: str,
    shared_strings: list[str],
) -> dict[str, str]:

    normalized_path = str(
        worksheet_path
    ).replace(
        "\\",
        "/",
    ).lstrip(
        "/"
    )

    if normalized_path not in archive.namelist():

        return {}

    root = ET.fromstring(
        archive.read(
            normalized_path
        )
    )

    values = {}

    for cell in root.iter(
        f"{{{MAIN_NS}}}c"
    ):

        reference = (
            cell.attrib.get(
                "r"
            )
            or ""
        ).upper()

        if not reference:
            continue

        values[reference] = _cell_value(
            cell,
            shared_strings,
        )

    return values


def _sheet_has_user_content(
    values: dict[str, str],
    sheet_tracker: dict,
    tracker: dict,
) -> bool:

    for row in (
        sheet_tracker.get(
            "rows"
        )
        or []
    ):

        cells = (
            row.get(
                "cells"
            )
            or {}
        )

        for severity in range(
            6
        ):

            reference = str(
                cells.get(
                    f"sev{severity}"
                )
                or ""
            ).upper()

            value = str(
                values.get(
                    reference,
                    ""
                )
            ).strip().lower()

            if value == "x":

                return True

        photos_reference = str(
            cells.get(
                "fotos"
            )
            or ""
        ).upper()

        location_reference = str(
            cells.get(
                "ubicacion"
            )
            or ""
        ).upper()

        if str(
            values.get(
                photos_reference,
                ""
            )
        ).strip():

            return True

        if str(
            values.get(
                location_reference,
                ""
            )
        ).strip():

            return True

    observations = (
        tracker.get(
            "observaciones"
        )
        or {}
    )

    for key in (
        "levantamiento",
        "revisor",
    ):

        reference = str(
            observations.get(
                key
            )
            or ""
        ).upper()

        if (
            reference
            and str(
                values.get(
                    reference,
                    ""
                )
            ).strip()
        ):

            return True

    return False


def _components_from_workbook(
    excel_path: Path,
) -> list[str]:
    """
    Detecta componentes realmente diligenciados comparando
    exclusivamente sus celdas editables contra la plantilla
    original.

    Nunca se analizan las celdas de identificación.

    Cuenta únicamente:
    - severidad marcada;
    - número de fotos;
    - ubicación;
    - observación del levantamiento;
    - observación del revisor.

    Ignora:
    - fecha, hora e ID del puente;
    - fórmulas;
    - formatos;
    - celdas grises;
    - valores predeterminados de la plantilla;
    - componentes enviados por la interfaz pero vacíos.
    """

    from backend import server

    tracker_path = (
        Path(__file__)
        .resolve()
        .with_name(
            "template_tracker.json"
        )
    )

    tracker = json.loads(
        tracker_path.read_text(
            encoding="utf-8-sig",
        )
    )

    template_path = Path(
        server.buscar_plantilla()
    ).resolve()

    if not template_path.exists():

        raise RuntimeError(
            "No encontré la plantilla original "
            "para comparar los componentes."
        )


    def worksheet_records(
        archive: zipfile.ZipFile,
        worksheet_path: str,
        shared_strings: list[str],
    ) -> dict[str, dict[str, str]]:

        normalized_path = str(
            worksheet_path
            or ""
        ).replace(
            "\\",
            "/",
        ).lstrip(
            "/"
        )

        if normalized_path not in archive.namelist():

            return {}

        root = ET.fromstring(
            archive.read(
                normalized_path
            )
        )

        records = {}

        for cell in root.iter(
            f"{{{MAIN_NS}}}c"
        ):

            reference = str(
                cell.attrib.get(
                    "r"
                )
                or ""
            ).upper()

            if not reference:
                continue

            formula_node = cell.find(
                f"{{{MAIN_NS}}}f"
            )

            formula = ""

            if (
                formula_node is not None
                and formula_node.text
            ):

                formula = str(
                    formula_node.text
                ).strip()

            records[reference] = {
                "value": _cell_value(
                    cell,
                    shared_strings,
                ),
                "formula": formula,
            }

        return records


    def clean_value(
        value,
    ) -> str:

        return re.sub(
            r"\s+",
            " ",
            str(
                value
                or ""
            ),
        ).strip()


    def record_value(
        records: dict,
        reference,
    ) -> str:

        reference = str(
            reference
            or ""
        ).upper()

        return clean_value(
            records
            .get(
                reference,
                {}
            )
            .get(
                "value",
                ""
            )
        )


    def record_has_formula(
        records: dict,
        reference,
    ) -> bool:

        reference = str(
            reference
            or ""
        ).upper()

        return bool(
            clean_value(
                records
                .get(
                    reference,
                    {}
                )
                .get(
                    "formula",
                    ""
                )
            )
        )


    def changed_user_value(
        selected_records: dict,
        template_records: dict,
        reference,
    ) -> bool:

        reference = str(
            reference
            or ""
        ).upper()

        if not reference:

            return False

        # Las fórmulas nunca cuentan como diligenciamiento.
        if record_has_formula(
            selected_records,
            reference,
        ):

            return False

        selected_value = record_value(
            selected_records,
            reference,
        )

        template_value = record_value(
            template_records,
            reference,
        )

        return (
            bool(
                selected_value
            )
            and selected_value
            != template_value
        )


    result = []

    with zipfile.ZipFile(
        excel_path,
        "r",
    ) as selected_archive, zipfile.ZipFile(
        template_path,
        "r",
    ) as template_archive:

        selected_shared = (
            _read_shared_strings(
                selected_archive
            )
        )

        template_shared = (
            _read_shared_strings(
                template_archive
            )
        )

        for sheet_tracker in (
            tracker.get(
                "sheets"
            )
            or []
        ):

            name = str(
                sheet_tracker.get(
                    "name"
                )
                or ""
            ).strip()

            if (
                not name
                or _is_system_sheet(
                    name
                )
            ):

                continue

            worksheet_path = str(
                sheet_tracker.get(
                    "path"
                )
                or ""
            )

            selected_records = worksheet_records(
                selected_archive,
                worksheet_path,
                selected_shared,
            )

            template_records = worksheet_records(
                template_archive,
                worksheet_path,
                template_shared,
            )

            component_has_data = False

            # =================================================
            # SEVERIDADES, FOTOS Y UBICACIÓN
            # =================================================

            for row in (
                sheet_tracker.get(
                    "rows"
                )
                or []
            ):

                cells = (
                    row.get(
                        "cells"
                    )
                    or {}
                )

                # Severidad:
                # debe ser una X real y distinta de la plantilla.
                for severity in range(
                    6
                ):

                    reference = cells.get(
                        f"sev{severity}"
                    )

                    selected_value = record_value(
                        selected_records,
                        reference,
                    )

                    template_value = record_value(
                        template_records,
                        reference,
                    )

                    if (
                        not record_has_formula(
                            selected_records,
                            reference,
                        )
                        and selected_value.casefold()
                        == "x"
                        and selected_value.casefold()
                        != template_value.casefold()
                    ):

                        component_has_data = True
                        break

                if component_has_data:
                    break

                # Número de fotos.
                if changed_user_value(
                    selected_records,
                    template_records,
                    cells.get(
                        "fotos"
                    ),
                ):

                    component_has_data = True
                    break

                # Ubicación del daño.
                if changed_user_value(
                    selected_records,
                    template_records,
                    cells.get(
                        "ubicacion"
                    ),
                ):

                    component_has_data = True
                    break

            # =================================================
            # OBSERVACIONES
            # =================================================

            if not component_has_data:

                observations = (
                    tracker.get(
                        "observaciones"
                    )
                    or {}
                )

                for key in (
                    "levantamiento",
                    "revisor",
                ):

                    reference = observations.get(
                        key
                    )

                    if changed_user_value(
                        selected_records,
                        template_records,
                        reference,
                    ):

                        component_has_data = True
                        break

            if component_has_data:

                result.append(
                    name
                )

    return result

def _workbook_sheet_names(
    excel_path: Path,
) -> list[str]:

    with zipfile.ZipFile(
        excel_path,
        "r",
    ) as archive:

        root = ET.fromstring(
            archive.read(
                "xl/workbook.xml"
            )
        )

    sheets_node = root.find(
        f"{{{MAIN_NS}}}sheets"
    )

    if sheets_node is None:

        return []

    return [
        str(
            sheet.attrib.get(
                "name"
            )
            or ""
        )
        for sheet in sheets_node
    ]


def _visible_sheet_names(
    excel_path: Path,
) -> list[str]:

    with zipfile.ZipFile(
        excel_path,
        "r",
    ) as archive:

        root = ET.fromstring(
            archive.read(
                "xl/workbook.xml"
            )
        )

    sheets_node = root.find(
        f"{{{MAIN_NS}}}sheets"
    )

    if sheets_node is None:

        return []

    visible = []

    for sheet in sheets_node:

        state = str(
            sheet.attrib.get(
                "state"
            )
            or "visible"
        ).lower()

        if state not in {
            "hidden",
            "veryhidden",
        }:

            visible.append(
                str(
                    sheet.attrib.get(
                        "name"
                    )
                    or ""
                )
            )

    return visible


def _patch_workbook_visibility(
    source: Path,
    destination: Path,
    component_names: list[str],
) -> list[str]:

    component_keys = {
        _normalize(
            name
        )
        for name in component_names
        if _normalize(
            name
        )
    }

    visible_names = []
    first_visible_index = None

    with zipfile.ZipFile(
        source,
        "r",
    ) as input_archive:

        workbook_root = ET.fromstring(
            input_archive.read(
                "xl/workbook.xml"
            )
        )

        sheets_node = workbook_root.find(
            f"{{{MAIN_NS}}}sheets"
        )

        if sheets_node is None:

            raise RuntimeError(
                "El Excel no contiene "
                "la lista de hojas."
            )

        calculation_found = False

        for index, sheet in enumerate(
            sheets_node
        ):

            name = str(
                sheet.attrib.get(
                    "name"
                )
                or ""
            )

            normalized = _normalize(
                name
            )

            keep_visible = (
                normalized
                in component_keys
                or _is_calculo_ic(
                    name
                )
            )

            if _is_calculo_ic(
                name
            ):

                calculation_found = True

            if keep_visible:

                sheet.attrib.pop(
                    "state",
                    None,
                )

                visible_names.append(
                    name
                )

                if first_visible_index is None:

                    first_visible_index = index

            else:

                sheet.set(
                    "state",
                    "hidden",
                )

        if not calculation_found:

            raise RuntimeError(
                "No encontré la hoja "
                "CALCULO IC en el Excel."
            )

        if first_visible_index is None:

            raise RuntimeError(
                "No quedó ninguna hoja visible."
            )

        workbook_views = workbook_root.find(
            f"{{{MAIN_NS}}}bookViews"
        )

        if workbook_views is not None:

            workbook_view = workbook_views.find(
                f"{{{MAIN_NS}}}workbookView"
            )

            if workbook_view is not None:

                workbook_view.set(
                    "activeTab",
                    str(
                        first_visible_index
                    ),
                )

                workbook_view.set(
                    "firstSheet",
                    str(
                        first_visible_index
                    ),
                )

        workbook_bytes = ET.tostring(
            workbook_root,
            encoding="utf-8",
            xml_declaration=True,
        )

        with zipfile.ZipFile(
            destination,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as output_archive:

            for info in input_archive.infolist():

                content = input_archive.read(
                    info.filename
                )

                if info.filename == "xl/workbook.xml":

                    content = workbook_bytes

                output_archive.writestr(
                    info,
                    content,
                )

    return visible_names


def _create_filtered_copy(
    source: Path,
    destination: Path,
) -> tuple[list[str], list[str], str]:
    """
    Crea la copia temporal que recibe LibreOffice.

    La selección se determina exclusivamente comparando
    las celdas diligenciables del Excel contra la plantilla.

    La identificación superior nunca interviene.
    """

    components = _components_from_workbook(
        source
    )

    detection_method = (
        "comparación de severidades, fotos, ubicación "
        "y observaciones contra la plantilla original"
    )

    if not components:

        raise RuntimeError(
            "No hay componentes diligenciados "
            "para generar el PDF. "
            "La identificación del puente no cuenta. "
            "Rellena una severidad, número de fotos, "
            "ubicación u observación."
        )

    visible = _patch_workbook_visibility(
        source,
        destination,
        components,
    )

    if any(
        _is_index(
            name
        )
        for name in visible
    ):

        raise RuntimeError(
            "El Índice continuó visible "
            "en la copia temporal."
        )

    if any(
        _is_evaluation(
            name
        )
        for name in visible
    ):

        raise RuntimeError(
            "Evaluación continuó visible "
            "en la copia temporal."
        )

    if any(
        _is_annex(
            name
        )
        for name in visible
    ):

        raise RuntimeError(
            "Un anexo continuó visible "
            "en la copia temporal."
        )

    calculation_sheets = [
        name
        for name in visible
        if _is_calculo_ic(
            name
        )
    ]

    if not calculation_sheets:

        raise RuntimeError(
            "CALCULO IC no quedó visible."
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

    if expected_keys != visible_keys:

        raise RuntimeError(
            "La copia temporal no contiene "
            "exactamente los componentes diligenciados."
        )

    return (
        components,
        visible,
        detection_method,
    )

def convertir_excel_seleccionado_job(
    job_id: str,
    excel_path: str,
    pdf_path: str,
) -> None:

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
                    "sipucol_pdf_filtrado_"
                )
            )
        )

        filtered_excel = (
            temporary_directory
            / (
                "SIPUCOL_PDF_FILTRADO"
                + source.suffix
            )
        )

        server.set_job(
            job_id,
            status="running",
            progress=5,
            message=(
                "Detectando componentes "
                "diligenciados..."
            ),
            source_excel=str(
                source
            ),
            output_path=str(
                pdf_path
            ),
        )

        (
            components,
            visible,
            detection_method,
        ) = _create_filtered_copy(
            source,
            filtered_excel,
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
