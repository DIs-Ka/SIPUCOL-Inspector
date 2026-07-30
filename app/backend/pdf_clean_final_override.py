from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from backend import (
    pdf_final_page_filter_worker
    as functional_worker
)


def _fold(
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


def _real_component(
    page_text: str,
    component_names: list[str],
) -> str | None:
    """
    Reconoce únicamente una hoja real del formato
    de inspección.

    El índice y el catálogo no cumplen todos estos
    requisitos simultáneamente.
    """

    folded = _fold(
        page_text
    )

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

        folded_name = _fold(
            clean_name
        )

        if not folded_name:
            continue

        exact_header = re.compile(
            r"\bcomponente\s*:\s*"
            + re.escape(
                folded_name
            )
            + r"(?=\s|$)",
            flags=re.IGNORECASE,
        )

        if exact_header.search(
            folded
        ):

            matches.append(
                clean_name
            )

    if not matches:

        return None

    matches.sort(
        key=lambda name: len(
            _fold(
                name
            )
        ),
        reverse=True,
    )

    return matches[0]


def _calculo_score(
    page_text: str,
) -> tuple[int, int]:
    """
    Puntúa una página de CALCULO IC.

    Se seleccionará una única página: la que tenga
    más señales y mayor cantidad de contenido.
    """

    folded = _fold(
        page_text
    )

    markers = [
        "indicaciones consideraciones",
        "categoria de la via",
        "ponderados por area de evaluacion",
        "ponderados por componentes",
        "ponderados por grupo",
        "calificacion ponderada del componente",
        "calificacion ponderada del grupo",
        "calificacion ponderada del puente",
        "indice de condicion",
        "descripcion del estado del puente",
        "elegir caso",
        "seleccionar categoria de la via",
    ]

    score = sum(
        1
        for marker in markers
        if marker in folded
    )

    return (
        score,
        len(
            folded
        ),
    )


def _is_calculo_ic(
    page_text: str,
) -> bool:

    score, text_length = (
        _calculo_score(
            page_text
        )
    )

    return (
        score >= 4
        and text_length >= 500
    )


def filtrar_paginas_pdf(
    full_pdf: Path,
    final_pdf: Path,
    component_names: list[str],
) -> dict:
    """
    Resultado final:

    - componentes reales;
    - una página original completa de CALCULO IC;
    - nada de mosaicos;
    - nada de recortes;
    - nada de índice;
    - nada de catálogo.
    """

    reader = PdfReader(
        str(
            full_pdf
        )
    )

    component_pages = []

    found_components = set()

    calculation_candidates = []

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


        component = _real_component(
            page_text,
            component_names,
        )


        if component is not None:

            component_pages.append(
                page_index
            )

            found_components.add(
                _fold(
                    component
                )
            )

            debug.append((
                page_index + 1,
                "COMPONENTE_REAL",
                component,
            ))

            continue


        if _is_calculo_ic(
            page_text
        ):

            score = _calculo_score(
                page_text
            )

            calculation_candidates.append({
                "index":
                    page_index,

                "score":
                    score,
            })

            debug.append((
                page_index + 1,
                "CANDIDATO_CALCULO_IC",
                (
                    f"score={score[0]}, "
                    f"texto={score[1]}"
                ),
            ))


    expected_components = {
        _fold(
            name
        )
        for name in component_names
        if _fold(
            name
        )
    }


    missing_components = (
        expected_components
        - found_components
    )


    if missing_components:

        raise RuntimeError(
            "No pude localizar las hojas reales "
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


    if not calculation_candidates:

        raise RuntimeError(
            "No se encontró la página original "
            "de CALCULO IC."
        )


    # ========================================================
    # UNA SOLA PÁGINA ORIGINAL DE CALCULO IC
    # ========================================================

    best_calculation = max(
        calculation_candidates,
        key=lambda item: (
            item[
                "score"
            ][0],
            item[
                "score"
            ][1],
        ),
    )


    calculation_page = (
        best_calculation[
            "index"
        ]
    )


    component_pages = list(
        dict.fromkeys(
            sorted(
                component_pages
            )
        )
    )


    selected_pages = (
        component_pages
        + [
            calculation_page
        ]
    )


    writer = PdfWriter()


    # Copia exacta de cada página.
    #
    # No se toca:
    # - mediabox;
    # - cropbox;
    # - escala;
    # - orientación;
    # - contenido;
    # - vectores;
    # - imágenes.
    for page_index in selected_pages:

        writer.add_page(
            reader.pages[
                page_index
            ]
        )


    final_pdf.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    temporary_output = (
        final_pdf.parent
        / (
            final_pdf.stem
            + ".sipucol_limpiando.tmp.pdf"
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


    debug.append((
        calculation_page + 1,
        "CALCULO_IC_ELEGIDO",
        "página original completa",
    ))


    return {
        "original_pages":
            len(
                reader.pages
            ),

        "final_pages":
            len(
                selected_pages
            ),

        "component_pages":
            [
                page + 1
                for page in component_pages
            ],

        "condition_pages":
            [
                calculation_page + 1
            ],

        "selected_pages":
            [
                page + 1
                for page in selected_pages
            ],

        "condition_output_pages":
            1,

        "tiled_condition_pages":
            [],

        "debug":
            debug,
    }


def convertir_excel_seleccionado_job(
    *args,
    **kwargs,
):
    """
    Conserva todo el flujo funcional anterior.

    Solo sustituye temporalmente el último filtro,
    evitando la división de CALCULO IC.
    """

    original_filter = (
        functional_worker
        .filtrar_paginas_pdf
    )

    try:

        functional_worker.filtrar_paginas_pdf = (
            filtrar_paginas_pdf
        )

        return (
            functional_worker
            .convertir_excel_seleccionado_job(
                *args,
                **kwargs,
            )
        )

    finally:

        functional_worker.filtrar_paginas_pdf = (
            original_filter
        )
