from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path.cwd().resolve()
SRC = ROOT / "src"
MAIN = SRC / "main.jsx"
MODULE = SRC / "photoPanelFinalPolish.js"
BACKUPS = ROOT / "backups"

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

EXCLUDED = {
    "node_modules",
    ".git",
    "dist",
    "__pycache__",
    ".venv",
    ".sipucol_runtime",
    "backups",
}

BACKUPS.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# 1. VALIDACIONES
# =========================================================

if not MAIN.exists():

    raise SystemExit(
        "ERROR: no encontré src/main.jsx"
    )


def create_project_backup(
    name: str,
) -> Path:

    destination = (
        BACKUPS
        / f"{name}_{STAMP}.zip"
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
                part in EXCLUDED
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


# =========================================================
# 2. BACKUP DE LA VERSIÓN FUNCIONAL
# =========================================================

backup_before = create_project_backup(
    "SIPUCOL_FUNCIONAL_ANTES_RETOQUES_PANEL_FOTOS"
)

print()
print("=" * 72)
print("BACKUP DE LA VERSIÓN FUNCIONAL")
print("=" * 72)
print(backup_before)


main_original = MAIN.read_bytes()

module_existed = MODULE.exists()

module_original = (
    MODULE.read_bytes()
    if module_existed
    else None
)


# =========================================================
# 3. MÓDULO FINAL EXCLUSIVO PARA FOTOS
# =========================================================

module_code = r'''
/*
===========================================================
SIPUCOL — PANEL FOTOS FINAL
===========================================================

Este módulo actúa exclusivamente dentro del panel Fotos.

Corrige:
- Buscador bloqueado a 2 dígitos.
- Slider de tamaño.
- Grid de miniaturas al reducir el tamaño.
- Estado "Sin enviar".
- Modal "Ver grande" con imagen original.
- Zoom y ajuste sin pérdida de calidad.
- Franja obsoleta Fotos -> Evaluación.

No toca:
- Evaluación.
- Códigos de daño.
- Excel.
- PDF.
- Backend.
*/


const PHOTO_SEARCH_ATTRIBUTE =
  "data-sipucol-photo-search"


const PHOTO_PANEL_ATTRIBUTE =
  "data-sipucol-photo-panel"


const THUMB_GRID_ATTRIBUTE =
  "data-sipucol-photo-thumb-grid"


const THUMB_CARD_ATTRIBUTE =
  "data-sipucol-photo-thumb-card"


const THUMB_SLIDER_ATTRIBUTE =
  "data-sipucol-photo-thumb-slider"


const STORAGE_THUMB_SIZE =
  "sipucol-photo-thumbnail-size"


const THUMB_MIN =
  72


const THUMB_MAX =
  240


const THUMB_STEP =
  4


let currentPhotoPanel =
  null


let panelObserver =
  null


let updateScheduled =
  false


function normalizeText(
  value
) {

  return String(
    value || ""
  )
    .trim()
    .toLowerCase()
    .normalize(
      "NFD"
    )
    .replace(
      /[\u0300-\u036f]/g,
      ""
    )
    .replace(
      /\s+/g,
      " "
    )
}


function isVisible(
  element
) {

  if (!element) {

    return false
  }


  const style =
    window.getComputedStyle(
      element
    )


  if (
    style.display === "none"
    || style.visibility === "hidden"
  ) {

    return false
  }


  const rectangle =
    element.getBoundingClientRect()


  return (
    rectangle.width > 1
    && rectangle.height > 1
  )
}


function findPhotoPanel() {

  const titles = [

    ...document.querySelectorAll(
      "h1, h2, h3, header, div, span"
    )
  ]


  for (
    const title
    of titles
  ) {

    if (
      normalizeText(
        title.textContent
      )
      !== "fotos"
    ) {

      continue
    }


    let current =
      title.parentElement


    for (
      let level = 0;
      level < 9;
      level += 1
    ) {

      if (!current) {

        break
      }


      const buttons = [

        ...current.querySelectorAll(
          "button"
        )
      ]


      const hasLoadButton =
        buttons.some(

          button =>

            normalizeText(
              button.textContent
            )
            === "cargar"
        )


      const text =
        normalizeText(
          current.textContent
        )


      if (
        hasLoadButton
        && text.includes(
          "cargadas"
        )
      ) {

        current.setAttribute(
          PHOTO_PANEL_ATTRIBUTE,
          "true"
        )


        return current
      }


      current =
        current.parentElement
    }
  }


  return null
}


/*
===========================================================
BUSCADOR DE FOTOS
===========================================================
*/


function findPhotoSearch(
  panel
) {

  const inputs = [

    ...panel.querySelectorAll(
      "input"
    )
  ]


  const candidates =
    inputs.filter(

      input => {

        const type =
          normalizeText(
            input.type
          )


        return (
          type !== "file"
          && type !== "range"
          && type !== "checkbox"
          && type !== "radio"
        )
      }
    )


  const preferred =
    candidates.find(

      input => {

        const placeholder =
          normalizeText(
            input.placeholder
          )


        return (
          placeholder.includes(
            "maximo 2 digitos"
          )
          || placeholder.includes(
            "buscar foto"
          )
        )
      }
    )


  if (preferred) {

    return preferred
  }


  const panelRectangle =
    panel.getBoundingClientRect()


  return candidates.find(

    input => {

      const rectangle =
        input.getBoundingClientRect()


      return (
        rectangle.top
        <
        panelRectangle.top + 180
      )
    }
  ) || null
}


function fixPhotoSearch(
  panel
) {

  const input =
    findPhotoSearch(
      panel
    )


  if (!input) {

    return null
  }


  input.setAttribute(
    PHOTO_SEARCH_ATTRIBUTE,
    "true"
  )


  try {

    input.type =
      "text"

  } catch {

  }


  input.placeholder =
    "Buscar foto..."


  input.removeAttribute(
    "maxlength"
  )


  input.removeAttribute(
    "pattern"
  )


  input.removeAttribute(
    "inputmode"
  )


  input.removeAttribute(
    "data-sipucol-real-id"
  )


  input.removeAttribute(
    "data-sipucol-id-puente"
  )


  input.removeAttribute(
    "data-sipucol-bridge-id"
  )


  input.removeAttribute(
    "data-sipucol-id-guard"
  )


  input.autocomplete =
    "off"


  return input
}


/*
Los controles antiguos del ID Puente estaban capturando
eventos del buscador de Fotos.

El listener se instala en window capture, antes de document,
para que esos controles no reciban keydown, beforeinput o paste.

No se bloquea el evento input posterior, por lo que React
sigue recibiendo el valor escrito.
*/


function releasePhotoSearchEvent(
  event
) {

  const target =
    event.target


  if (
    !(
      target
      instanceof HTMLInputElement
    )
  ) {

    return
  }


  if (
    target.getAttribute(
      PHOTO_SEARCH_ATTRIBUTE
    )
    !== "true"
  ) {

    return
  }


  event.stopPropagation()
}


window.addEventListener(
  "keydown",
  releasePhotoSearchEvent,
  true
)


window.addEventListener(
  "beforeinput",
  releasePhotoSearchEvent,
  true
)


window.addEventListener(
  "paste",
  releasePhotoSearchEvent,
  true
)


/*
===========================================================
ELIMINAR ESTADO "SIN ENVIAR"
===========================================================
*/


function removeNotSentStatus(
  panel
) {

  const walker =
    document.createTreeWalker(

      panel,

      NodeFilter.SHOW_TEXT
    )


  const textNodes = []


  while (
    walker.nextNode()
  ) {

    textNodes.push(
      walker.currentNode
    )
  }


  for (
    const textNode
    of textNodes
  ) {

    const original =
      textNode.nodeValue || ""


    const updated =
      original.replace(

        /Estado\s*:\s*Sin enviar/gi,

        ""
      )


    if (
      updated !== original
    ) {

      textNode.nodeValue =
        updated


      const parent =
        textNode.parentElement


      if (
        parent
        && !normalizeText(
          parent.textContent
        )
      ) {

        parent.style.display =
          "none"
      }
    }
  }
}


/*
===========================================================
OCULTAR FRANJA OBSOLETA FOTOS -> EVALUACIÓN
===========================================================
*/


function hideOldEvaluationBar(
  panel
) {

  const elements = [

    ...panel.querySelectorAll(
      "div, section, nav, header"
    )
  ]


  const candidates = []


  for (
    const element
    of elements
  ) {

    const text =
      normalizeText(
        element.textContent
      )


    const buttons = [

      ...element.querySelectorAll(
        "button"
      )

    ].map(

      button =>

        normalizeText(
          button.textContent
        )
    )


    const destinationButtonCount =
      buttons.filter(

        name => [

          "superficie del puente",

          "juntas de dilatacion",

          "bordillo",

          "barandas",

          "aletas",

          "estribos"

        ].includes(
          name
        )
      ).length


    const score =

      (
        text.includes(
          "enviar foto a evaluacion"
        )
        ? 100
        : 0
      )

      + (
        text.includes(
          "destino:"
        )
        ? 60
        : 0
      )

      + destinationButtonCount * 10


    if (
      score >= 40
      && !text.includes(
        "carpeta actual"
      )
      && !text.includes(
        "no hay foto seleccionada"
      )
    ) {

      candidates.push({

        element,

        score,

        size:
          element.outerHTML.length
      })
    }
  }


  candidates.sort(

    (
      first,
      second
    ) =>

      second.score
      - first.score

      || first.size
      - second.size
  )


  const selected =
    candidates[0]
      ?.element


  if (!selected) {

    return false
  }


  selected.setAttribute(
    "data-sipucol-old-photo-evaluation",
    "true"
  )


  selected.style.setProperty(
    "display",
    "none",
    "important"
  )


  return true
}


/*
===========================================================
IMAGEN PRINCIPAL
===========================================================
*/


function findMainViewerImage(
  panel
) {

  const images = [

    ...panel.querySelectorAll(
      "img"
    )

  ].filter(

    image => {

      if (!isVisible(image)) {

        return false
      }


      const rectangle =
        image.getBoundingClientRect()


      return (
        rectangle.width > 40
        && rectangle.height > 40
      )
    }
  )


  images.sort(

    (
      first,
      second
    ) => {

      const firstRectangle =
        first.getBoundingClientRect()


      const secondRectangle =
        second.getBoundingClientRect()


      return (

        secondRectangle.width
        * secondRectangle.height

        -

        firstRectangle.width
        * firstRectangle.height
      )
    }
  )


  return images[0] || null
}


/*
===========================================================
SLIDER DE MINIATURAS
===========================================================
*/


function clampThumbSize(
  value
) {

  const number =
    Number(
      value
    )


  if (
    !Number.isFinite(
      number
    )
  ) {

    return 128
  }


  return Math.min(

    THUMB_MAX,

    Math.max(

      THUMB_MIN,

      number
    )
  )
}


function findThumbSlider(
  panel
) {

  const inputs = [

    ...panel.querySelectorAll(
      "input"
    )
  ]


  const existing =
    inputs.find(

      input =>

        input.getAttribute(
          THUMB_SLIDER_ATTRIBUTE
        )
        === "true"
    )


  if (existing) {

    return existing
  }


  const labels = [

    ...panel.querySelectorAll(
      "label, span, div"
    )

  ].filter(

    element =>

      normalizeText(
        element.textContent
      )
      === "tamano"
  )


  for (
    const label
    of labels
  ) {

    let current =
      label.parentElement


    for (
      let level = 0;
      level < 4;
      level += 1
    ) {

      if (!current) {

        break
      }


      const input = [

        ...current.querySelectorAll(
          "input"
        )

      ].find(

        candidate =>

          candidate.getAttribute(
            PHOTO_SEARCH_ATTRIBUTE
          )
          !== "true"

          && candidate.type !== "file"
      )


      if (input) {

        return input
      }


      current =
        current.parentElement
    }
  }


  return inputs.find(

    input =>

      input.type === "range"

  ) || null
}


function findThumbnailGrid(
  panel,
  mainImage
) {

  const thumbnailImages = [

    ...panel.querySelectorAll(
      "img"
    )

  ].filter(

    image => {

      if (
        image === mainImage
        || !isVisible(image)
      ) {

        return false
      }


      const rectangle =
        image.getBoundingClientRect()


      const mainRectangle =
        mainImage
          ?.getBoundingClientRect()


      return (

        rectangle.width >= 20

        && rectangle.height >= 20

        && (
          !mainRectangle

          || rectangle.top
             >
             mainRectangle.bottom - 10
        )
      )
    }
  )


  if (
    thumbnailImages.length < 2
  ) {

    return null
  }


  const candidateScores = []


  for (
    const image
    of thumbnailImages
  ) {

    let current =
      image.parentElement


    for (
      let level = 0;
      level < 7;
      level += 1
    ) {

      if (
        !current
        || current === panel
      ) {

        break
      }


      if (
        mainImage
        && current.contains(
          mainImage
        )
      ) {

        current =
          current.parentElement

        continue
      }


      const imageCount =
        current.querySelectorAll(
          "img"
        ).length


      if (
        imageCount >= 2
      ) {

        candidateScores.push({

          element:
            current,

          imageCount,

          size:
            current.outerHTML.length
        })
      }


      current =
        current.parentElement
    }
  }


  candidateScores.sort(

    (
      first,
      second
    ) =>

      second.imageCount
      - first.imageCount

      || first.size
      - second.size
  )


  return (
    candidateScores[0]
      ?.element
    || null
  )
}


function markThumbCards(
  grid
) {

  const images = [

    ...grid.querySelectorAll(
      "img"
    )
  ]


  for (
    const image
    of images
  ) {

    let card =
      image


    while (
      card.parentElement
      && card.parentElement !== grid
    ) {

      card =
        card.parentElement
    }


    if (
      card
      && card !== grid
    ) {

      card.setAttribute(
        THUMB_CARD_ATTRIBUTE,
        "true"
      )
    }
  }
}


function applyThumbnailSize(
  panel,
  size
) {

  const safeSize =
    clampThumbSize(
      size
    )


  const mainImage =
    findMainViewerImage(
      panel
    )


  const grid =
    findThumbnailGrid(

      panel,

      mainImage
    )


  if (!grid) {

    return
  }


  grid.setAttribute(
    THUMB_GRID_ATTRIBUTE,
    "true"
  )


  grid.style.setProperty(

    "--sipucol-photo-thumb-size",

    `${safeSize}px`
  )


  markThumbCards(
    grid
  )
}


function fixThumbnailSlider(
  panel
) {

  const slider =
    findThumbSlider(
      panel
    )


  if (!slider) {

    return null
  }


  slider.setAttribute(
    THUMB_SLIDER_ATTRIBUTE,
    "true"
  )


  try {

    slider.type =
      "range"

  } catch {

  }


  slider.min =
    String(
      THUMB_MIN
    )


  slider.max =
    String(
      THUMB_MAX
    )


  slider.step =
    String(
      THUMB_STEP
    )


  slider.removeAttribute(
    "list"
  )


  slider.removeAttribute(
    "pattern"
  )


  const stored =
    localStorage.getItem(
      STORAGE_THUMB_SIZE
    )


  const selectedSize =
    clampThumbSize(

      stored

      || slider.value

      || 128
    )


  slider.value =
    String(
      selectedSize
    )


  applyThumbnailSize(

    panel,

    selectedSize
  )


  if (
    slider.dataset
      .sipucolSliderReady
    !== "true"
  ) {

    slider.dataset
      .sipucolSliderReady =
        "true"


    slider.addEventListener(

      "input",

      () => {

        const size =
          clampThumbSize(
            slider.value
          )


        localStorage.setItem(

          STORAGE_THUMB_SIZE,

          String(
            size
          )
        )


        applyThumbnailSize(

          panel,

          size
        )
      }
    )


    slider.addEventListener(

      "change",

      () => {

        applyThumbnailSize(

          panel,

          slider.value
        )
      }
    )
  }


  return slider
}


/*
===========================================================
MODAL DE IMAGEN ORIGINAL
===========================================================
*/


function getBestOriginalSource(
  image
) {

  const dataSource =

    image.getAttribute(
      "data-full-src"
    )

    || image.getAttribute(
      "data-original-src"
    )

    || image.getAttribute(
      "data-original"
    )


  if (dataSource) {

    return dataSource
  }


  const anchor =
    image.closest(
      "a[href]"
    )


  if (anchor) {

    const href =
      anchor.href


    if (
      href.startsWith(
        "blob:"
      )

      || href.startsWith(
        "data:image/"
      )

      || /\.(png|jpe?g|webp|gif|bmp|svg)(\?|#|$)/i
        .test(
          href
        )
    ) {

      return href
    }
  }


  return (

    image.currentSrc

    || image.src
  )
}


function ensureImageModal() {

  let modal =
    document.getElementById(
      "sipucol-original-photo-modal"
    )


  if (modal) {

    return modal
  }


  modal =
    document.createElement(
      "div"
    )


  modal.id =
    "sipucol-original-photo-modal"


  modal.innerHTML = `

    <div
      class="sipucol-photo-modal-toolbar"
    >

      <div
        class="sipucol-photo-modal-title"
      >
        Imagen original
      </div>


      <div
        class="sipucol-photo-modal-info"
      >
        Cargando...
      </div>


      <div
        class="sipucol-photo-modal-actions"
      >

        <button
          type="button"
          data-action="zoom-out"
          title="Alejar"
        >
          −
        </button>


        <button
          type="button"
          data-action="zoom-reset"
          title="Tamaño original"
        >
          100 %
        </button>


        <button
          type="button"
          data-action="zoom-in"
          title="Acercar"
        >
          +
        </button>


        <button
          type="button"
          data-action="zoom-fit"
          title="Ajustar a la ventana"
        >
          Ajustar
        </button>


        <button
          type="button"
          data-action="close"
          title="Cerrar"
        >
          Cerrar
        </button>

      </div>

    </div>


    <div
      class="sipucol-photo-modal-stage"
    >

      <div
        class="sipucol-photo-modal-content"
      >

        <img
          alt="Fotografía ampliada"
          draggable="false"
        />

      </div>

    </div>
  `


  document.body.appendChild(
    modal
  )


  const stage =
    modal.querySelector(
      ".sipucol-photo-modal-stage"
    )


  const image =
    modal.querySelector(
      "img"
    )


  const info =
    modal.querySelector(
      ".sipucol-photo-modal-info"
    )


  modal._sipucolPhotoState = {

    zoom:
      1,

    naturalWidth:
      1,

    naturalHeight:
      1,

    image,

    stage,

    info
  }


  function renderZoom() {

    const state =
      modal._sipucolPhotoState


    const width =

      state.naturalWidth

      * state.zoom


    const height =

      state.naturalHeight

      * state.zoom


    state.image.style.width =
      `${Math.max(1, width)}px`


    state.image.style.height =
      `${Math.max(1, height)}px`


    state.image.style.maxWidth =
      "none"


    state.image.style.maxHeight =
      "none"


    state.image.style.objectFit =
      "contain"


    state.image.style.imageRendering =
      "auto"


    state.info.textContent =

      `${state.naturalWidth}`

      + " × "

      + `${state.naturalHeight}`

      + " · "

      + `${Math.round(
          state.zoom * 100
        )} %`
  }


  function setZoom(
    value
  ) {

    const state =
      modal._sipucolPhotoState


    state.zoom =
      Math.min(

        8,

        Math.max(

          0.1,

          value
        )
      )


    renderZoom()
  }


  function fitImage() {

    const state =
      modal._sipucolPhotoState


    const availableWidth =

      state.stage.clientWidth

      - 48


    const availableHeight =

      state.stage.clientHeight

      - 48


    const fitZoom =
      Math.min(

        1,

        availableWidth
        / state.naturalWidth,

        availableHeight
        / state.naturalHeight
      )


    setZoom(
      fitZoom
    )


    state.stage.scrollTo(
      0,
      0
    )
  }


  modal.querySelector(

    '[data-action="zoom-out"]'

  ).addEventListener(

    "click",

    () => {

      setZoom(

        modal
          ._sipucolPhotoState
          .zoom

        / 1.2
      )
    }
  )


  modal.querySelector(

    '[data-action="zoom-in"]'

  ).addEventListener(

    "click",

    () => {

      setZoom(

        modal
          ._sipucolPhotoState
          .zoom

        * 1.2
      )
    }
  )


  modal.querySelector(

    '[data-action="zoom-reset"]'

  ).addEventListener(

    "click",

    () => {

      setZoom(
        1
      )


      stage.scrollTo(
        0,
        0
      )
    }
  )


  modal.querySelector(

    '[data-action="zoom-fit"]'

  ).addEventListener(

    "click",

    fitImage
  )


  modal.querySelector(

    '[data-action="close"]'

  ).addEventListener(

    "click",

    () => {

      modal.classList.remove(
        "is-open"
      )


      image.removeAttribute(
        "src"
      )
    }
  )


  modal.addEventListener(

    "click",

    event => {

      if (
        event.target === modal
      ) {

        modal.classList.remove(
          "is-open"
        )


        image.removeAttribute(
          "src"
        )
      }
    }
  )


  stage.addEventListener(

    "wheel",

    event => {

      if (
        !event.ctrlKey
        && !event.metaKey
      ) {

        return
      }


      event.preventDefault()


      const multiplier =

        event.deltaY < 0

        ? 1.12

        : 1 / 1.12


      setZoom(

        modal
          ._sipucolPhotoState
          .zoom

        * multiplier
      )
    },

    {
      passive:
        false
    }
  )


  image.addEventListener(

    "dblclick",

    () => {

      const state =
        modal._sipucolPhotoState


      if (
        Math.abs(
          state.zoom - 1
        )
        < 0.01
      ) {

        fitImage()

      } else {

        setZoom(
          1
        )
      }
    }
  )


  document.addEventListener(

    "keydown",

    event => {

      if (
        event.key === "Escape"
        && modal.classList.contains(
          "is-open"
        )
      ) {

        modal.classList.remove(
          "is-open"
        )


        image.removeAttribute(
          "src"
        )
      }
    }
  )


  modal._sipucolRenderZoom =
    renderZoom


  return modal
}


function openOriginalImage(
  sourceImage
) {

  const source =
    getBestOriginalSource(
      sourceImage
    )


  if (!source) {

    return
  }


  const modal =
    ensureImageModal()


  const state =
    modal._sipucolPhotoState


  state.info.textContent =
    "Cargando imagen original..."


  state.zoom =
    1


  state.image.onload =
    () => {

      state.naturalWidth =

        state.image.naturalWidth

        || sourceImage.naturalWidth

        || 1


      state.naturalHeight =

        state.image.naturalHeight

        || sourceImage.naturalHeight

        || 1


      state.zoom =
        1


      modal._sipucolRenderZoom()


      state.stage.scrollTo(
        0,
        0
      )
    }


  state.image.onerror =
    () => {

      state.info.textContent =
        "No se pudo abrir la imagen original."
    }


  state.image.src =
    source


  modal.classList.add(
    "is-open"
  )
}


document.addEventListener(

  "click",

  event => {

    const button =
      event.target.closest(
        "button"
      )


    if (!button) {

      return
    }


    if (
      normalizeText(
        button.textContent
      )
      !== "ver grande"
    ) {

      return
    }


    const panel =
      findPhotoPanel()


    if (
      !panel
      || !panel.contains(
        button
      )
    ) {

      return
    }


    const image =
      findMainViewerImage(
        panel
      )


    if (!image) {

      return
    }


    event.preventDefault()

    event.stopImmediatePropagation()


    openOriginalImage(
      image
    )
  },

  true
)


/*
===========================================================
ESTILOS EXCLUSIVOS DE FOTOS
===========================================================
*/


function installStyles() {

  if (
    document.getElementById(
      "sipucol-photo-final-polish-style"
    )
  ) {

    return
  }


  const style =
    document.createElement(
      "style"
    )


  style.id =
    "sipucol-photo-final-polish-style"


  style.textContent = `

    [${PHOTO_PANEL_ATTRIBUTE}="true"]
    input[${PHOTO_SEARCH_ATTRIBUTE}="true"] {

      appearance:
        auto !important;

      -webkit-appearance:
        auto !important;
    }


    [${PHOTO_PANEL_ATTRIBUTE}="true"]
    input[${THUMB_SLIDER_ATTRIBUTE}="true"] {

      appearance:
        auto !important;

      -webkit-appearance:
        auto !important;

      width:
        min(180px, 42%) !important;

      min-width:
        110px !important;

      height:
        22px !important;

      padding:
        0 !important;

      cursor:
        pointer !important;
    }


    [${THUMB_GRID_ATTRIBUTE}="true"] {

      display:
        grid !important;

      grid-template-columns:
        repeat(
          auto-fill,
          minmax(
            var(
              --sipucol-photo-thumb-size,
              128px
            ),
            var(
              --sipucol-photo-thumb-size,
              128px
            )
          )
        )
        !important;

      align-items:
        start !important;

      justify-content:
        start !important;

      gap:
        10px !important;

      overflow-x:
        hidden !important;
    }


    [${THUMB_CARD_ATTRIBUTE}="true"] {

      width:
        var(
          --sipucol-photo-thumb-size,
          128px
        )
        !important;

      min-width:
        0 !important;

      max-width:
        var(
          --sipucol-photo-thumb-size,
          128px
        )
        !important;

      overflow:
        hidden !important;

      box-sizing:
        border-box !important;
    }


    [${THUMB_CARD_ATTRIBUTE}="true"]
    img {

      display:
        block !important;

      width:
        100% !important;

      max-width:
        100% !important;

      height:
        auto !important;

      max-height:
        calc(
          var(
            --sipucol-photo-thumb-size,
            128px
          )
          * 0.78
        )
        !important;

      object-fit:
        cover !important;
    }


    [data-sipucol-old-photo-evaluation="true"] {

      display:
        none !important;

      visibility:
        hidden !important;

      height:
        0 !important;

      min-height:
        0 !important;

      margin:
        0 !important;

      padding:
        0 !important;

      border:
        0 !important;

      overflow:
        hidden !important;
    }


    #sipucol-original-photo-modal {

      position:
        fixed;

      inset:
        0;

      z-index:
        2147483000;

      display:
        none;

      grid-template-rows:
        auto 1fr;

      background:
        rgba(
          3,
          8,
          18,
          0.97
        );

      color:
        #eafff6;
    }


    #sipucol-original-photo-modal.is-open {

      display:
        grid;
    }


    .sipucol-photo-modal-toolbar {

      display:
        flex;

      align-items:
        center;

      gap:
        14px;

      min-height:
        58px;

      padding:
        8px 14px;

      border-bottom:
        1px solid
        rgba(
          48,
          226,
          165,
          0.35
        );

      background:
        rgba(
          5,
          21,
          31,
          0.98
        );
    }


    .sipucol-photo-modal-title {

      font-size:
        15px;

      font-weight:
        800;

      color:
        #52e4aa;
    }


    .sipucol-photo-modal-info {

      flex:
        1;

      min-width:
        0;

      color:
        #a8cabe;

      font-size:
        12px;

      font-variant-numeric:
        tabular-nums;
    }


    .sipucol-photo-modal-actions {

      display:
        flex;

      align-items:
        center;

      gap:
        7px;
    }


    .sipucol-photo-modal-actions
    button {

      min-width:
        38px;

      height:
        34px;

      padding:
        0 11px;

      border:
        1px solid
        rgba(
          54,
          226,
          167,
          0.48
        );

      border-radius:
        8px;

      background:
        rgba(
          12,
          87,
          67,
          0.72
        );

      color:
        #effff8;

      cursor:
        pointer;

      font-weight:
        750;
    }


    .sipucol-photo-modal-actions
    button:hover {

      background:
        rgba(
          18,
          122,
          89,
          0.86
        );

      box-shadow:
        0 0 15px
        rgba(
          45,
          225,
          163,
          0.2
        );
    }


    .sipucol-photo-modal-stage {

      position:
        relative;

      overflow:
        auto;

      min-width:
        0;

      min-height:
        0;

      overscroll-behavior:
        contain;

      background:

        linear-gradient(
          45deg,
          rgba(
            255,
            255,
            255,
            0.028
          )
          25%,
          transparent
          25%
        ),

        linear-gradient(
          -45deg,
          rgba(
            255,
            255,
            255,
            0.028
          )
          25%,
          transparent
          25%
        ),

        linear-gradient(
          45deg,
          transparent
          75%,
          rgba(
            255,
            255,
            255,
            0.028
          )
          75%
        ),

        linear-gradient(
          -45deg,
          transparent
          75%,
          rgba(
            255,
            255,
            255,
            0.028
          )
          75%
        );

      background-size:
        24px 24px;

      background-position:
        0 0,
        0 12px,
        12px -12px,
        -12px 0;
    }


    .sipucol-photo-modal-content {

      display:
        flex;

      align-items:
        flex-start;

      justify-content:
        center;

      min-width:
        100%;

      min-height:
        100%;

      padding:
        24px;

      box-sizing:
        border-box;
    }


    .sipucol-photo-modal-content
    img {

      flex:
        0 0 auto;

      display:
        block;

      max-width:
        none;

      max-height:
        none;

      object-fit:
        contain;

      image-rendering:
        auto;

      box-shadow:
        0 20px 70px
        rgba(
          0,
          0,
          0,
          0.6
        );

      user-select:
        none;
    }


    @media (
      max-width: 760px
    ) {

      .sipucol-photo-modal-toolbar {

        align-items:
          flex-start;

        flex-wrap:
          wrap;
      }


      .sipucol-photo-modal-info {

        order:
          3;

        flex-basis:
          100%;
      }
    }
  `


  document.head.appendChild(
    style
  )
}


/*
===========================================================
APLICACIÓN Y OBSERVADOR LIMITADO AL PANEL FOTOS
===========================================================
*/


function polishPhotoPanel() {

  const panel =
    findPhotoPanel()


  if (!panel) {

    return false
  }


  currentPhotoPanel =
    panel


  fixPhotoSearch(
    panel
  )


  removeNotSentStatus(
    panel
  )


  hideOldEvaluationBar(
    panel
  )


  fixThumbnailSlider(
    panel
  )


  return true
}


function schedulePolish() {

  if (updateScheduled) {

    return
  }


  updateScheduled =
    true


  requestAnimationFrame(

    () => {

      updateScheduled =
        false


      polishPhotoPanel()
    }
  )
}


function startPhotoPanelPolish() {

  installStyles()


  const ready =
    polishPhotoPanel()


  if (
    currentPhotoPanel
    && !panelObserver
  ) {

    panelObserver =
      new MutationObserver(
        schedulePolish
      )


    panelObserver.observe(

      currentPhotoPanel,

      {
        childList:
          true,

        subtree:
          true,

        attributes:
          true,

        attributeFilter: [

          "placeholder",

          "maxlength",

          "pattern",

          "inputmode",

          "type"
        ]
      }
    )
  }


  if (!ready) {

    let attempts =
      0


    const timer =
      window.setInterval(

        () => {

          attempts += 1


          if (
            polishPhotoPanel()
            || attempts >= 30
          ) {

            window.clearInterval(
              timer
            )


            if (
              currentPhotoPanel
              && !panelObserver
            ) {

              panelObserver =
                new MutationObserver(
                  schedulePolish
                )


              panelObserver.observe(

                currentPhotoPanel,

                {
                  childList:
                    true,

                  subtree:
                    true,

                  attributes:
                    true,

                  attributeFilter: [

                    "placeholder",

                    "maxlength",

                    "pattern",

                    "inputmode",

                    "type"
                  ]
                }
              )
            }
          }
        },

        250
      )
  }
}


if (
  document.readyState
  === "loading"
) {

  document.addEventListener(

    "DOMContentLoaded",

    startPhotoPanelPolish,

    {
      once:
        true
    }
  )

} else {

  startPhotoPanelPolish()
}
'''


MODULE.write_text(
    module_code,
    encoding="utf-8",
)


# =========================================================
# 4. DEJAR UN SOLO MÓDULO ESPECÍFICO DE FOTOS
# =========================================================

main_code = MAIN.read_text(
    encoding="utf-8",
)


old_photo_modules = [
    "hidePhotoEvaluationBar.js",
    "removePhotoReview.js",
    "photoPanelFinalPolish.js",
]


for module_name in old_photo_modules:

    main_code = re.sub(

        r'^\s*import\s+["\']'
        r'\./'
        + re.escape(
            module_name
        )
        + r'["\'];?\s*$',

        "",

        main_code,

        flags=re.MULTILINE,
    )


main_code = (
    main_code.rstrip()
    + "\n"
)


lines = main_code.splitlines()

last_import_index = -1


for index, line in enumerate(
    lines
):

    if line.strip().startswith(
        "import "
    ):

        last_import_index =
          index


new_import = (
    'import "./photoPanelFinalPolish.js";'
)


if last_import_index >= 0:

    lines.insert(
        last_import_index + 1,
        new_import,
    )

else:

    lines.insert(
        0,
        new_import,
    )


MAIN.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)


# =========================================================
# 5. VALIDAR FRONTEND
# =========================================================

npm = (
    shutil.which(
        "npm.cmd"
    )
    or shutil.which(
        "npm"
    )
)


if not npm:

    MAIN.write_bytes(
        main_original
    )

    if module_existed:

        MODULE.write_bytes(
            module_original
        )

    elif MODULE.exists():

        MODULE.unlink()

    raise SystemExit(
        "ERROR: no encontré npm."
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


print(
    build.stdout
)


if build.returncode != 0:

    MAIN.write_bytes(
        main_original
    )

    if module_existed:

        MODULE.write_bytes(
            module_original
        )

    elif MODULE.exists():

        MODULE.unlink()


    print()
    print("=" * 72)
    print("PARCHE REVERTIDO AUTOMÁTICAMENTE")
    print("=" * 72)
    print(build.stderr)

    raise SystemExit(1)


# =========================================================
# 6. LIMPIAR CACHÉ VITE
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
# 7. BACKUP FINAL
# =========================================================

backup_after = create_project_backup(
    "SIPUCOL_FUNCIONAL_PANEL_FOTOS_FINAL"
)


print()
print("=" * 72)
print("PANEL FOTOS CORREGIDO Y VALIDADO")
print("=" * 72)

print()
print("Corregido:")
print("- Ver grande usa la imagen original.")
print("- Calidad original conservada.")
print("- Tamaño inicial real: 100 %.")
print("- Imágenes pequeñas no se agrandan.")
print("- Zoom, ajustar y 100 % disponibles.")
print("- Estado: Sin enviar eliminado.")
print("- Tamaño de miniaturas convertido en slider.")
print("- Grid estable incluso en tamaños pequeños.")
print("- Buscador restaurado para texto y números.")
print("- Límite de 2 dígitos eliminado del buscador.")
print("- Franja Fotos -> Evaluación oculta.")

print()
print("No modificado:")
print("- Panel Evaluación.")
print("- Códigos de daño.")
print("- Motor PDF.")
print("- Exportador Excel.")
print("- Backend.")
print("- Autoguardado.")

print()
print("BACKUP ANTERIOR:")
print(backup_before)

print()
print("BACKUP FINAL:")
print(backup_after)
