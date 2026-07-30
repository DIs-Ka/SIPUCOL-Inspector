from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import unicodedata
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from backend import pdf_libreoffice_worker as stable_worker


def _normalize(
    value,
) -> str:

    text = unicodedata.normalize(
        "NFD",
        str(
            value
            or ""
        ),
    )

    text = "".join(
        character
        for character in text
        if unicodedata.category(
            character
        )
        != "Mn"
    )

    return re.sub(
        r"[^a-z0-9]+",
        "",
        text.lower(),
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
    ]

    result = []
    seen = set()

    for candidate in candidates:

        key = os.path.normcase(
            str(
                candidate.resolve()
            )
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            candidate
        )

    return result


def _add_unique(
    result: list[str],
    seen: set[str],
    value,
) -> None:

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
        or key in seen
    ):

        return

    seen.add(
        key
    )

    result.append(
        clean
    )


def componentes_desde_reporte(
    excel_path: Path,
) -> tuple[list[str], Path]:
    """
    Lee el reporte generado junto al Excel.

    La fuente prioritaria es component_sheet_matches,
    porque contiene solamente los componentes realmente
    enviados desde la UI.

    No se usa identification_written.
    """

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

        report_output = str(
            report.get(
                "output"
            )
            or ""
        ).strip()

        if report_output:

            try:

                report_name = Path(
                    report_output
                ).name.casefold()

                if (
                    report_name
                    != excel_path.name.casefold()
                ):

                    continue

            except Exception:

                continue

        result = []
        seen = set()

        # ====================================================
        # FUENTE PRINCIPAL:
        # COMPONENTES EMPAREJADOS CON HOJAS
        # ====================================================

        for match in (
            report.get(
                "component_sheet_matches"
            )
            or []
        ):

            _add_unique(
                result,
                seen,
                (
                    match.get(
                        "sheet"
                    )
                    or match.get(
                        "component"
                    )
                ),
            )

        # ====================================================
        # RESPALDO:
        # SOLO ESCRITURAS REALES
        # ====================================================

        if not result:

            for item in (
                report.get(
                    "written_items"
                )
                or []
            ):

                has_real_write = any(

                    str(
                        write.get(
                            "action"
                        )
                        or ""
                    )
                    .strip()
                    .lower()
                    == "write"

                    and bool(
                        str(
                            write.get(
                                "value"
                            )
                            or ""
                        ).strip()
                    )

                    for write in (
                        item.get(
                            "writes"
                        )
                        or []
                    )
                )

                if has_real_write:

                    _add_unique(
                        result,
                        seen,
                        (
                            item.get(
                                "sheet"
                            )
                            or item.get(
                                "component"
                            )
                        ),
                    )

        # ====================================================
        # OBSERVACIONES REALES
        # ====================================================

        for observation in (
            report.get(
                "observations_written"
            )
            or []
        ):

            if str(
                observation.get(
                    "value"
                )
                or ""
            ).strip():

                _add_unique(
                    result,
                    seen,
                    observation.get(
                        "sheet"
                    ),
                )

        if result:

            return (
                result,
                report_path,
            )

    raise RuntimeError(
        "No encontré el reporte de exportación "
        "correspondiente al Excel seleccionado. "
        "Guarda primero el Excel desde SIPUCOL."
    )


def _is_condition_index_page(
    normalized_text: str,
) -> bool:

    condition_markers = [
        "indicedecondiciondelpuente",
        "indicedecondiciondescripciondelestadodelpuente",
        "calificacionponderadadelpuente",
        "calificacionponderadadelgrupo",
    ]

    return any(
        marker in normalized_text
        for marker in condition_markers
    )


def _component_for_page(
    normalized_text: str,
    component_names: list[str],
) -> str | None:

    # Las páginas de tablas contienen el encabezado
    # "Componente : nombre".
    if (
        "componente"
        not in normalized_text
    ):

        return None

    matches = []

    for name in component_names:

        normalized_name = _normalize(
            name
        )

        if (
            normalized_name
            and normalized_name
            in normalized_text
        ):

            matches.append(
                name
            )

    if not matches:

        return None

    # Priorizar el nombre más específico.
    matches.sort(
        key=lambda value: len(
            _normalize(
                value
            )
        ),
        reverse=True,
    )

    return matches[0]


def filtrar_paginas_pdf(
    full_pdf: Path,
    final_pdf: Path,
    component_names: list[str],
) -> dict:
    """
    Filtro final definitivo.

    Conserva únicamente:

    1. Páginas reales de los componentes solicitados.
    2. CALCULO IC al final.

    Nunca conserva:

    - Índice inicial.
    - Nota inicial.
    - Catálogo general de códigos.
    - Anexos.
    - Páginas que solo mencionan el nombre del componente.

    Si CALCULO IC llega comprimido en una sola página,
    se divide en seis regiones vectoriales legibles.
    """

    import copy
    import re
    import unicodedata

    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import RectangleObject


    def fold_text(
        value,
    ) -> str:

        text = unicodedata.normalize(
            "NFD",
            str(
                value
                or ""
            ),
        )

        text = "".join(
            character
            for character in text
            if unicodedata.category(
                character
            )
            != "Mn"
        )

        text = text.lower()

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()


    def exact_component(
        page_text: str,
    ) -> str | None:

        folded = fold_text(
            page_text
        )

        # Una página real del formato debe contener
        # simultáneamente estos encabezados.
        required_markers = [
            "identificacion",
            "localizacion",
            "registros de danos",
            "deterioro",
            "severidad",
        ]

        if not all(
            marker in folded
            for marker in required_markers
        ):

            return None


        matches = []


        for component_name in component_names:

            clean_name = str(
                component_name
                or ""
            ).strip()

            folded_name = fold_text(
                clean_name
            )

            if not folded_name:
                continue


            # Se exige literalmente:
            #
            # Componente : Superficie del tablero
            #
            # El índice únicamente enumera el nombre.
            # El catálogo utiliza "Componentes" en plural.
            pattern = re.compile(
                r"\bcomponente\s*:\s*"
                + re.escape(
                    folded_name
                )
                + r"(?=\s|$)",
                flags=re.IGNORECASE,
            )


            if pattern.search(
                folded
            ):

                matches.append(
                    clean_name
                )


        if not matches:

            return None


        matches.sort(
            key=lambda value: len(
                fold_text(
                    value
                )
            ),
            reverse=True,
        )


        return matches[0]


    def is_condition_page(
        page_text: str,
    ) -> bool:

        folded = fold_text(
            page_text
        )


        # El índice inicial puede decir
        # "Índice de condición", pero no contiene
        # las tablas y cálculos siguientes.
        strong_markers = [
            "calificacion ponderada del puente",
            "calificacion ponderada del grupo",
            "calificacion ponderada del componente",
            "ponderados por componentes",
            "ponderados por grupo",
            "seleccionar categoria de la via",
            "descripcion del estado del puente",
            "indicaciones consideraciones",
        ]


        score = sum(
            1
            for marker in strong_markers
            if marker in folded
        )


        has_condition_result = (
            "indice de condicion"
            in folded

            and (
                "descripcion del estado del puente"
                in folded

                or "calificacion ponderada"
                in folded
            )
        )


        has_weight_tables = (
            "ponderados por componentes"
            in folded

            and (
                "elegir caso"
                in folded

                or "seleccionar categoria de la via"
                in folded
            )
        )


        return (
            score >= 2
            or has_condition_result
            or has_weight_tables
        )


    def condition_is_compressed(
        page_text: str,
    ) -> bool:

        folded = fold_text(
            page_text
        )


        return (
            len(
                folded
            )
            >= 3500

            or folded.count(
                "caso "
            )
            >= 7

            or folded.count(
                "ponderados"
            )
            >= 4
        )


    def add_condition_tiles(
        writer: PdfWriter,
        page,
    ) -> int:
        """
        Divide la página comprimida en:

        - 2 columnas.
        - 3 filas.
        - 6 páginas finales.

        Solo cambia la caja visible de cada copia.
        No convierte el PDF en imagen.
        No rasteriza.
        No recomprime.
        """

        left = float(
            page.mediabox.left
        )

        bottom = float(
            page.mediabox.bottom
        )

        right = float(
            page.mediabox.right
        )

        top = float(
            page.mediabox.top
        )


        width = right - left
        height = top - bottom


        columns = 2
        rows = 3


        tile_width = (
            width
            / columns
        )

        tile_height = (
            height
            / rows
        )


        overlap = min(
            width,
            height,
        ) * 0.008


        pages_added = 0


        # Orden:
        # superior izquierda,
        # superior derecha,
        # centro izquierda,
        # centro derecha,
        # inferior izquierda,
        # inferior derecha.
        for row_index in range(
            rows
        ):

            tile_top = (
                top
                - row_index
                * tile_height
            )

            tile_bottom = (
                top
                - (
                    row_index
                    + 1
                )
                * tile_height
            )


            for column_index in range(
                columns
            ):

                tile_left = (
                    left
                    + column_index
                    * tile_width
                )

                tile_right = (
                    left
                    + (
                        column_index
                        + 1
                    )
                    * tile_width
                )


                crop_left = max(
                    left,
                    tile_left
                    - overlap,
                )

                crop_right = min(
                    right,
                    tile_right
                    + overlap,
                )

                crop_bottom = max(
                    bottom,
                    tile_bottom
                    - overlap,
                )

                crop_top = min(
                    top,
                    tile_top
                    + overlap,
                )


                tile_page = copy.copy(
                    page
                )


                rectangle = RectangleObject([
                    crop_left,
                    crop_bottom,
                    crop_right,
                    crop_top,
                ])


                tile_page.mediabox = rectangle
                tile_page.cropbox = rectangle


                try:

                    tile_page.trimbox = rectangle

                except Exception:

                    pass


                try:

                    tile_page.artbox = rectangle

                except Exception:

                    pass


                writer.add_page(
                    tile_page
                )

                pages_added += 1


        return pages_added


    reader = PdfReader(
        str(
            full_pdf
        )
    )


    component_pages = []
    condition_pages = []

    found_components = set()
    debug = []


    for page_index, page in enumerate(
        reader.pages
    ):

        try:

            page_text = (
                page.extract_text()
                or ""
            )

        except Exception:

            page_text = ""


        component = exact_component(
            page_text
        )


        if component is not None:

            component_pages.append({
                "index":
                    page_index,

                "component":
                    component,

                "text":
                    page_text,
            })

            found_components.add(
                fold_text(
                    component
                )
            )

            debug.append((
                page_index + 1,
                "COMPONENTE_REAL",
                component,
            ))

            continue


        if is_condition_page(
            page_text
        ):

            condition_pages.append({
                "index":
                    page_index,

                "text":
                    page_text,
            })

            debug.append((
                page_index + 1,
                "CALCULO_IC",
                "",
            ))


    expected_components = {
        fold_text(
            name
        )
        for name in component_names
        if fold_text(
            name
        )
    }


    missing_components = (
        expected_components
        - found_components
    )


    if missing_components:

        raise RuntimeError(
            "No pude localizar las páginas reales "
            "de estos componentes: "
            + ", ".join(
                sorted(
                    missing_components
                )
            )
        )


    if not component_pages:

        raise RuntimeError(
            "No se encontró ninguna página "
            "real de componente."
        )


    if not condition_pages:

        raise RuntimeError(
            "No se encontró CALCULO IC."
        )


    writer = PdfWriter()


    # ========================================================
    # COMPONENTES PRIMERO
    # ========================================================

    for item in sorted(
        component_pages,
        key=lambda value: value[
            "index"
        ],
    ):

        writer.add_page(
            reader.pages[
                item[
                    "index"
                ]
            ]
        )


    # ========================================================
    # CALCULO IC SIEMPRE AL FINAL
    # ========================================================

    condition_output_pages = 0
    tiled_condition_pages = []


    for item in sorted(
        condition_pages,
        key=lambda value: value[
            "index"
        ],
    ):

        page = reader.pages[
            item[
                "index"
            ]
        ]


        if condition_is_compressed(
            item[
                "text"
            ]
        ):

            added = add_condition_tiles(
                writer,
                page,
            )

            condition_output_pages += added

            tiled_condition_pages.append(
                item[
                    "index"
                ]
                + 1
            )

        else:

            writer.add_page(
                page
            )

            condition_output_pages += 1


    final_pdf.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    temporary_output = (
        final_pdf.parent
        / (
            final_pdf.stem
            + ".sipucol_final.tmp.pdf"
        )
    )


    with temporary_output.open(
        "wb"
    ) as output_file:

        writer.write(
            output_file
        )


    if (
        not temporary_output.exists()
        or temporary_output.stat().st_size
        < 1000
    ):

        raise RuntimeError(
            "El PDF final quedó vacío "
            "o incompleto."
        )


    if final_pdf.exists():

        final_pdf.unlink()


    temporary_output.replace(
        final_pdf
    )


    component_source_pages = [
        item[
            "index"
        ]
        + 1

        for item in component_pages
    ]


    condition_source_pages = [
        item[
            "index"
        ]
        + 1

        for item in condition_pages
    ]


    return {
        "original_pages":
            len(
                reader.pages
            ),

        "final_pages":
            len(
                writer.pages
            ),

        "component_pages":
            component_source_pages,

        "condition_pages":
            condition_source_pages,

        "selected_pages":
            (
                component_source_pages
                + condition_source_pages
            ),

        "condition_output_pages":
            condition_output_pages,

        "tiled_condition_pages":
            tiled_condition_pages,

        "debug":
            debug,
    }

def convertir_excel_seleccionado_job(
    job_id: str,
    excel_path: str,
    pdf_path: str,
    component_names: list[str] | None = None,
) -> None:
    """
    Motor definitivo:

    1. LibreOffice genera el PDF completo con la calidad estable.
    2. Se conservan físicamente solo las páginas correspondientes
       a los componentes realmente diligenciados.
    3. Se conserva el Índice de Condición al final.
    4. No se rasteriza ninguna página.
    """

    from backend import server

    temporary_directory = None

    try:

        source = Path(
            excel_path
        ).resolve()

        destination = Path(
            pdf_path
        ).resolve()

        if (
            not source.exists()
            or not source.is_file()
        ):

            raise RuntimeError(
                "No existe el Excel seleccionado."
            )

        report_components = []
        report_path = None

        try:

            (
                report_components,
                report_path,
            ) = componentes_desde_reporte(
                source
            )

        except Exception:

            report_components = []

        # El reporte del Excel es prioritario.
        # La lista recibida desde UI queda como respaldo.
        selected_components = (
            report_components
            or [
                str(
                    name
                    or ""
                ).strip()

                for name in (
                    component_names
                    or []
                )

                if str(
                    name
                    or ""
                ).strip()
            ]
        )

        unique_components = []
        seen = set()

        for name in selected_components:

            key = _normalize(
                name
            )

            if (
                not key
                or key in seen
            ):

                continue

            seen.add(
                key
            )

            unique_components.append(
                name
            )

        selected_components = (
            unique_components
        )

        if not selected_components:

            raise RuntimeError(
                "No hay componentes diligenciados "
                "para generar el PDF."
            )

        temporary_directory = Path(
            tempfile.mkdtemp(
                prefix=(
                    "sipucol_pdf_paginas_"
                )
            )
        )

        full_pdf = (
            temporary_directory
            / "SIPUCOL_COMPLETO.pdf"
        )

        child_job_id = (
            job_id
            + "_libreoffice"
        )

        server.set_job(
            job_id,
            status="running",
            progress=5,
            message=(
                "Generando PDF base "
                "con LibreOffice..."
            ),
            source_excel=str(
                source
            ),
            output_path=str(
                destination
            ),
            componentes_pdf=(
                selected_components
            ),
        )

        server.log(
            f"Job {job_id}: "
            "COMPONENTES REALES -> "
            + ", ".join(
                selected_components
            )
        )

        if report_path is not None:

            server.log(
                f"Job {job_id}: "
                f"Reporte usado -> {report_path}"
            )

        stable_worker.convertir_excel_seleccionado_job(
            child_job_id,
            str(
                source
            ),
            str(
                full_pdf
            ),
        )

        if (
            not full_pdf.exists()
            or full_pdf.stat().st_size
            < 1000
        ):

            raise RuntimeError(
                "LibreOffice no generó "
                "el PDF base correctamente."
            )

        server.set_job(
            job_id,
            status="running",
            progress=88,
            message=(
                "Eliminando páginas "
                "de componentes vacíos..."
            ),
        )

        result = filtrar_paginas_pdf(
            full_pdf,
            destination,
            selected_components,
        )

        report_output = (
            destination.with_suffix(
                ".pdf_filter_report.txt"
            )
        )

        report_output.write_text(
            "\n".join([
                "SIPUCOL — FILTRO FINAL DE PÁGINAS",
                "=" * 72,
                "",
                (
                    "Componentes incluidos: "
                    + ", ".join(
                        selected_components
                    )
                ),
                "",
                (
                    "Páginas originales: "
                    + str(
                        result[
                            "original_pages"
                        ]
                    )
                ),
                (
                    "Páginas finales: "
                    + str(
                        result[
                            "final_pages"
                        ]
                    )
                ),
                (
                    "Páginas conservadas: "
                    + ", ".join(
                        str(
                            value
                        )
                        for value in result[
                            "selected_pages"
                        ]
                    )
                ),
                "",
                "Detección:",
                *[
                    (
                        f"- Página {page}: "
                        f"{kind} {value}"
                    ).rstrip()

                    for (
                        page,
                        kind,
                        value,
                    ) in result[
                        "debug"
                    ]
                ],
            ]),
            encoding="utf-8",
        )

        server.set_job(
            job_id,
            status="done",
            progress=100,
            message=(
                "PDF filtrado correctamente: "
                f"{result['final_pages']} página(s)."
            ),
            source_excel=str(
                source
            ),
            output_path=str(
                destination
            ),
            componentes_pdf=(
                selected_components
            ),
            original_pages=(
                result[
                    "original_pages"
                ]
            ),
            final_pages=(
                result[
                    "final_pages"
                ]
            ),
            selected_pages=(
                result[
                    "selected_pages"
                ]
            ),
            report_path=str(
                report_output
            ),
        )

        server.log(
            f"Job {job_id}: "
            f"PÁGINAS ORIGINALES -> "
            f"{result['original_pages']}"
        )

        server.log(
            f"Job {job_id}: "
            f"PÁGINAS FINALES -> "
            f"{result['final_pages']}"
        )

        server.log(
            f"Job {job_id}: "
            "PÁGINAS CONSERVADAS -> "
            + ", ".join(
                str(
                    value
                )
                for value in result[
                    "selected_pages"
                ]
            )
        )

        server.log(
            f"Job {job_id}: "
            f"PDF FINAL -> {destination}"
        )

    except Exception as error:

        server.set_job(
            job_id,
            status="error",
            progress=0,
            message=(
                "No se pudo crear "
                "el PDF final"
            ),
            error=str(
                error
            ),
        )

        server.log(
            f"Job {job_id}: "
            f"ERROR FILTRO FINAL -> {error}"
        )

    finally:

        if temporary_directory is not None:

            shutil.rmtree(
                temporary_directory,
                ignore_errors=True,
            )
