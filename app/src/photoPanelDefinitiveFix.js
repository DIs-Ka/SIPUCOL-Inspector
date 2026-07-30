
/*
===========================================================
SIPUCOL — PANEL FOTOS DEFINITIVO
===========================================================

Actúa solamente dentro del panel Fotos.

- Buscador libre.
- Estado Sin enviar eliminado.
- Slider real de miniaturas.
- Grid estable.
- Imagen original sin recomprimir.
- Zoom real 25 % a 150 %.
- Franja Fotos -> Evaluación oculta.
*/


const PANEL_ATTR =
  "data-sipucol-photo-panel-final"


const SEARCH_ATTR =
  "data-sipucol-photo-search-final"


const ORIGINAL_SIZE_INPUT_ATTR =
  "data-sipucol-original-size-control"


const CUSTOM_SIZE_CONTROL_ID =
  "sipucol-photo-size-control"


const GRID_ATTR =
  "data-sipucol-photo-grid-final"


const CARD_ATTR =
  "data-sipucol-photo-card-final"


const SIZE_STORAGE =
  "sipucol-photo-size-final"


const SIZE_MIN =
  60


const SIZE_MAX =
  240


const SIZE_STEP =
  5


const ZOOM_MIN =
  0.25


const ZOOM_MAX =
  1.5


let currentPanel =
  null


let panelObserver =
  null


let scheduled =
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



function elementVisible(
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

  const possibleTitles = [

    ...document.querySelectorAll(
      "h1, h2, h3, header, div, span"
    )
  ]


  for (
    const title
    of possibleTitles
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


      const hasLoadButton = [

        ...current.querySelectorAll(
          "button"
        )

      ].some(

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
          PANEL_ATTR,
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
BUSCADOR
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


  const compatible = inputs.filter(

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


  const byPlaceholder =
    compatible.find(

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


  if (byPlaceholder) {

    return byPlaceholder
  }


  const panelTop =
    panel.getBoundingClientRect()
      .top


  return compatible.find(

    input =>

      input
        .getBoundingClientRect()
        .top

      < panelTop + 170

  ) || null
}



function releaseSearchInput(
  input
) {

  if (!input) {

    return
  }


  input.setAttribute(
    SEARCH_ATTR,
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
    "min"
  )


  input.removeAttribute(
    "max"
  )


  input.removeAttribute(
    "step"
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


  input.removeAttribute(
    "data-sipucol-only-digits"
  )


  input.inputMode =
    "search"


  input.autocomplete =
    "off"
}



function isPhotoSearch(
  target
) {

  return (
    target
    instanceof HTMLInputElement

    && target.getAttribute(
      SEARCH_ATTR
    )
    === "true"
  )
}



/*
Estos eventos se capturan en window antes
de que los validadores erróneos del ID Puente
los reciban en document.

No se llama preventDefault, así que escribir,
pegar y borrar siguen funcionando normalmente.
*/


function protectSearchEvent(
  event
) {

  if (
    !isPhotoSearch(
      event.target
    )
  ) {

    return
  }


  releaseSearchInput(
    event.target
  )


  event.stopImmediatePropagation()
}



window.addEventListener(
  "keydown",
  protectSearchEvent,
  true
)


window.addEventListener(
  "beforeinput",
  protectSearchEvent,
  true
)


window.addEventListener(
  "paste",
  protectSearchEvent,
  true
)


window.addEventListener(

  "focusin",

  event => {

    if (
      isPhotoSearch(
        event.target
      )
    ) {

      releaseSearchInput(
        event.target
      )
    }
  },

  true
)



/*
===========================================================
QUITAR ESTADO SIN ENVIAR
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


  const nodes = []


  while (
    walker.nextNode()
  ) {

    nodes.push(
      walker.currentNode
    )
  }


  for (
    const node
    of nodes
  ) {

    const original =
      node.nodeValue || ""


    if (
      !/Estado\s*:\s*Sin enviar/i
        .test(
          original
        )
    ) {

      continue
    }


    node.nodeValue =
      original.replace(

        /Estado\s*:\s*Sin enviar/gi,

        ""
      )


    const parent =
      node.parentElement


    if (
      parent
      && normalizeText(
        parent.textContent
      )
      === ""
    ) {

      parent.style.setProperty(
        "display",
        "none",
        "important"
      )
    }
  }


  const elements = [

    ...panel.querySelectorAll(
      "div, span, p, small"
    )
  ]


  for (
    const element
    of elements
  ) {

    if (
      normalizeText(
        element.textContent
      )
      === "estado: sin enviar"
    ) {

      element.style.setProperty(
        "display",
        "none",
        "important"
      )
    }
  }
}



/*
===========================================================
OCULTAR FOTOS -> EVALUACIÓN
===========================================================
*/


function hideOldEvaluationBar(
  panel
) {

  const targetNames = new Set([

    "superficie del puente",

    "juntas de dilatacion",

    "bordillo",

    "barandas",

    "aletas",

    "estribos"
  ])


  const candidates = [

    ...panel.querySelectorAll(
      "div, section, nav, header"
    )
  ]
    .map(

      element => {

        const text =
          normalizeText(
            element.textContent
          )


        const buttonMatches = [

          ...element.querySelectorAll(
            "button"
          )

        ].filter(

          button =>

            targetNames.has(

              normalizeText(
                button.textContent
              )
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

          + buttonMatches * 15


        return {

          element,

          text,

          score,

          size:
            element.outerHTML.length
        }
      }
    )
    .filter(

      candidate =>

        candidate.score >= 60

        && !candidate.text.includes(
          "carpeta actual"
        )

        && !candidate.text.includes(
          "no hay foto seleccionada"
        )
    )
    .sort(

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

    return
  }


  selected.setAttribute(
    "data-sipucol-hide-photo-send",
    "true"
  )


  selected.style.setProperty(
    "display",
    "none",
    "important"
  )
}



/*
===========================================================
SLIDER REAL DE MINIATURAS
===========================================================
*/


function clampSize(
  value
) {

  const parsed =
    Number(
      value
    )


  if (
    !Number.isFinite(
      parsed
    )
  ) {

    return 110
  }


  return Math.min(

    SIZE_MAX,

    Math.max(

      SIZE_MIN,

      parsed
    )
  )
}



function findOriginalSizeControl(
  panel
) {

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
            SEARCH_ATTR
          )
          !== "true"

          && candidate.type !== "file"
      )


      if (input) {

        return {

          input,

          container:
            current,

          label
        }
      }


      current =
        current.parentElement
    }
  }


  return null
}



function nativeSetInputValue(
  input,
  value
) {

  const descriptor =

    Object
      .getOwnPropertyDescriptor(

        HTMLInputElement.prototype,

        "value"
      )


  descriptor
    ?.set
    ?.call(

      input,

      String(
        value
      )
    )


  input.dispatchEvent(

    new Event(

      "input",

      {
        bubbles:
          true
      }
    )
  )


  input.dispatchEvent(

    new Event(

      "change",

      {
        bubbles:
          true
      }
    )
  )
}



function findMainPhoto(
  panel
) {

  const images = [

    ...panel.querySelectorAll(
      "img"
    )

  ].filter(
    elementVisible
  )


  images.sort(

    (
      first,
      second
    ) => {

      const firstRect =
        first.getBoundingClientRect()


      const secondRect =
        second.getBoundingClientRect()


      return (

        secondRect.width
        * secondRect.height

        -

        firstRect.width
        * firstRect.height
      )
    }
  )


  return images[0] || null
}



function findThumbnailCards(
  panel
) {

  const buttons = [

    ...panel.querySelectorAll(
      "button"
    )

  ].filter(

    button =>

      normalizeText(
        button.textContent
      )
      === "sin usar"
  )


  const cards = []


  for (
    const button
    of buttons
  ) {

    let current =
      button.parentElement


    for (
      let level = 0;
      level < 6;
      level += 1
    ) {

      if (
        !current
        || current === panel
      ) {

        break
      }


      if (
        current.querySelectorAll(
          "img"
        ).length === 1
      ) {

        cards.push(
          current
        )

        break
      }


      current =
        current.parentElement
    }
  }


  return [

    ...new Set(
      cards
    )
  ]
}



function lowestCommonAncestor(
  elements,
  limit
) {

  if (
    elements.length === 0
  ) {

    return null
  }


  let current =
    elements[0].parentElement


  while (
    current
    && current !== limit
  ) {

    if (
      elements.every(

        element =>

          current.contains(
            element
          )
      )
    ) {

      return current
    }


    current =
      current.parentElement
  }


  return null
}



function configureThumbnailGrid(
  panel,
  size
) {

  const cards =
    findThumbnailCards(
      panel
    )


  if (
    cards.length < 2
  ) {

    return
  }


  const grid =
    lowestCommonAncestor(

      cards,

      panel
    )


  if (!grid) {

    return
  }


  grid.setAttribute(
    GRID_ATTR,
    "true"
  )


  grid.style.setProperty(

    "--sipucol-thumb-size",

    `${clampSize(
      size
    )}px`
  )


  for (
    const card
    of cards
  ) {

    card.setAttribute(
      CARD_ATTR,
      "true"
    )
  }
}



function installSizeSlider(
  panel
) {

  const found =
    findOriginalSizeControl(
      panel
    )


  if (!found) {

    return
  }


  const {
    input,
    container
  } = found


  input.setAttribute(
    ORIGINAL_SIZE_INPUT_ATTR,
    "true"
  )


  input.style.setProperty(
    "display",
    "none",
    "important"
  )


  let customControl =
    panel.querySelector(

      `#${CUSTOM_SIZE_CONTROL_ID}`
    )


  if (!customControl) {

    customControl =
      document.createElement(
        "div"
      )


    customControl.id =
      CUSTOM_SIZE_CONTROL_ID


    customControl.innerHTML = `

      <input
        type="range"
        min="${SIZE_MIN}"
        max="${SIZE_MAX}"
        step="${SIZE_STEP}"
        aria-label="Tamaño de miniaturas"
      />

      <span></span>
    `


    container.appendChild(
      customControl
    )
  }


  const slider =
    customControl.querySelector(
      'input[type="range"]'
    )


  const valueLabel =
    customControl.querySelector(
      "span"
    )


  const stored =
    localStorage.getItem(
      SIZE_STORAGE
    )


  const initial =
    clampSize(

      stored

      || input.value

      || 110
    )


  slider.value =
    String(
      initial
    )


  valueLabel.textContent =
    `${initial} px`


  configureThumbnailGrid(

    panel,

    initial
  )


  customControl._sipucolOriginalInput =
    input


  if (
    slider.dataset.ready
    !== "true"
  ) {

    slider.dataset.ready =
      "true"


    slider.addEventListener(

      "input",

      () => {

        const size =
          clampSize(
            slider.value
          )


        valueLabel.textContent =
          `${size} px`


        localStorage.setItem(

          SIZE_STORAGE,

          String(
            size
          )
        )


        const originalInput =
          customControl
            ._sipucolOriginalInput


        if (originalInput) {

          nativeSetInputValue(

            originalInput,

            size
          )
        }


        configureThumbnailGrid(

          panel,

          size
        )
      }
    )
  }
}



/*
===========================================================
VISOR ORIGINAL — ZOOM 25 % A 150 %
===========================================================
*/


function findImageNearButton(
  panel,
  button
) {

  let current =
    button.parentElement


  for (
    let level = 0;
    level < 6;
    level += 1
  ) {

    if (
      !current
      || current === panel
    ) {

      break
    }


    const images =
      current.querySelectorAll(
        "img"
      )


    if (
      images.length === 1
    ) {

      return images[0]
    }


    current =
      current.parentElement
  }


  return findMainPhoto(
    panel
  )
}



function sourceFromSrcset(
  image
) {

  const srcset =
    image.getAttribute(
      "srcset"
    )


  if (!srcset) {

    return null
  }


  const entries =
    srcset
      .split(",")
      .map(

        entry => {

          const pieces =
            entry.trim()
              .split(/\s+/)


          const source =
            pieces[0]


          const descriptor =
            pieces[1] || "1x"


          const score =
            parseFloat(
              descriptor
            ) || 1


          return {
            source,
            score
          }
        }
      )
      .sort(

        (
          first,
          second
        ) =>

          second.score
          - first.score
      )


  return (
    entries[0]
      ?.source

    || null
  )
}



function getOriginalSource(
  image
) {

  return (

    image.getAttribute(
      "data-original-src"
    )

    || image.getAttribute(
      "data-full-src"
    )

    || image.getAttribute(
      "data-original"
    )

    || sourceFromSrcset(
      image
    )

    || image.currentSrc

    || image.src
  )
}



function ensureViewer() {

  let viewer =
    document.getElementById(
      "sipucol-original-viewer-final"
    )


  if (viewer) {

    return viewer
  }


  viewer =
    document.createElement(
      "div"
    )


  viewer.id =
    "sipucol-original-viewer-final"


  viewer.innerHTML = `

    <header>

      <strong>
        Imagen original
      </strong>

      <span
        data-role="resolution"
      >
        Cargando...
      </span>

      <div
        class="sipucol-viewer-controls"
      >

        <button
          type="button"
          data-action="minus"
        >
          −
        </button>

        <input
          type="range"
          min="25"
          max="150"
          step="5"
          value="100"
          aria-label="Zoom"
        />

        <span
          data-role="zoom"
        >
          100 %
        </span>

        <button
          type="button"
          data-action="plus"
        >
          +
        </button>

        <button
          type="button"
          data-action="original"
        >
          100 %
        </button>

        <button
          type="button"
          data-action="fit"
        >
          Ajustar
        </button>

        <button
          type="button"
          data-action="close"
        >
          Cerrar
        </button>

      </div>

    </header>


    <main>

      <div>

        <img
          alt="Imagen original"
          draggable="false"
        />

      </div>

    </main>
  `


  document.body.appendChild(
    viewer
  )


  const stage =
    viewer.querySelector(
      "main"
    )


  const image =
    viewer.querySelector(
      "img"
    )


  const zoomSlider =
    viewer.querySelector(
      '.sipucol-viewer-controls input'
    )


  const zoomLabel =
    viewer.querySelector(
      '[data-role="zoom"]'
    )


  const resolutionLabel =
    viewer.querySelector(
      '[data-role="resolution"]'
    )


  viewer._state = {

    image,

    stage,

    zoomSlider,

    zoomLabel,

    resolutionLabel,

    naturalWidth:
      1,

    naturalHeight:
      1,

    zoom:
      1
  }


  function render() {

    const state =
      viewer._state


    const width =

      state.naturalWidth

      * state.zoom


    const height =

      state.naturalHeight

      * state.zoom


    state.image.style.width =
      `${Math.max(
        1,
        Math.round(
          width
        )
      )}px`


    state.image.style.height =
      `${Math.max(
        1,
        Math.round(
          height
        )
      )}px`


    const percentage =
      Math.round(
        state.zoom * 100
      )


    state.zoomSlider.value =
      String(
        percentage
      )


    state.zoomLabel.textContent =
      `${percentage} %`


    state.resolutionLabel.textContent =

      `${state.naturalWidth}`

      + " × "

      + `${state.naturalHeight}`
  }


  function setZoom(
    value
  ) {

    const state =
      viewer._state


    state.zoom =
      Math.min(

        ZOOM_MAX,

        Math.max(

          ZOOM_MIN,

          Number(
            value
          )
        )
      )


    render()
  }


  function fit() {

    const state =
      viewer._state


    const availableWidth =
      state.stage.clientWidth - 50


    const availableHeight =
      state.stage.clientHeight - 50


    const fitted =
      Math.min(

        1,

        availableWidth
        / state.naturalWidth,

        availableHeight
        / state.naturalHeight
      )


    setZoom(
      Math.max(
        ZOOM_MIN,
        fitted
      )
    )


    state.stage.scrollTo(
      0,
      0
    )
  }


  zoomSlider.addEventListener(

    "input",

    () => {

      setZoom(

        Number(
          zoomSlider.value
        )

        / 100
      )
    }
  )


  viewer.querySelector(

    '[data-action="minus"]'

  ).addEventListener(

    "click",

    () => {

      setZoom(

        viewer._state.zoom

        - 0.05
      )
    }
  )


  viewer.querySelector(

    '[data-action="plus"]'

  ).addEventListener(

    "click",

    () => {

      setZoom(

        viewer._state.zoom

        + 0.05
      )
    }
  )


  viewer.querySelector(

    '[data-action="original"]'

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


  viewer.querySelector(

    '[data-action="fit"]'

  ).addEventListener(

    "click",

    fit
  )


  viewer.querySelector(

    '[data-action="close"]'

  ).addEventListener(

    "click",

    () => {

      viewer.classList.remove(
        "open"
      )


      image.removeAttribute(
        "src"
      )
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


      const delta =

        event.deltaY < 0

        ? 0.05

        : -0.05


      setZoom(

        viewer._state.zoom

        + delta
      )
    },

    {
      passive:
        false
    }
  )


  viewer._setZoom =
    setZoom


  viewer._fit =
    fit


  return viewer
}



function openOriginalViewer(
  sourceImage
) {

  const source =
    getOriginalSource(
      sourceImage
    )


  if (!source) {

    return
  }


  const viewer =
    ensureViewer()


  const state =
    viewer._state


  state.resolutionLabel.textContent =
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


      viewer._setZoom(
        1
      )


      state.stage.scrollTo(
        0,
        0
      )
    }


  state.image.onerror =
    () => {

      state.resolutionLabel.textContent =
        "No se pudo cargar la imagen original."
    }


  state.image.src =
    source


  viewer.classList.add(
    "open"
  )
}



document.addEventListener(

  "click",

  event => {

    const button =
      event.target.closest(
        "button"
      )


    if (
      !button
      || normalizeText(
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
      findImageNearButton(

        panel,

        button
      )


    if (!image) {

      return
    }


    event.preventDefault()

    event.stopImmediatePropagation()


    openOriginalViewer(
      image
    )
  },

  true
)



document.addEventListener(

  "keydown",

  event => {

    if (
      event.key !== "Escape"
    ) {

      return
    }


    const viewer =
      document.getElementById(
        "sipucol-original-viewer-final"
      )


    if (
      viewer
      ?.classList
      .contains(
        "open"
      )
    ) {

      viewer.classList.remove(
        "open"
      )


      viewer
        .querySelector(
          "img"
        )
        ?.removeAttribute(
          "src"
        )
    }
  }
)



/*
===========================================================
ESTILOS
===========================================================
*/


function installStyles() {

  if (
    document.getElementById(
      "sipucol-photo-definitive-styles"
    )
  ) {

    return
  }


  const style =
    document.createElement(
      "style"
    )


  style.id =
    "sipucol-photo-definitive-styles"


  style.textContent = `

    [data-sipucol-hide-photo-send="true"] {

      display:
        none !important;

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


    [${ORIGINAL_SIZE_INPUT_ATTR}="true"] {

      display:
        none !important;
    }


    #${CUSTOM_SIZE_CONTROL_ID} {

      display:
        flex !important;

      align-items:
        center !important;

      justify-content:
        flex-end !important;

      gap:
        9px !important;

      flex:
        1 !important;

      min-width:
        125px !important;
    }


    #${CUSTOM_SIZE_CONTROL_ID}
    input[type="range"] {

      appearance:
        auto !important;

      -webkit-appearance:
        auto !important;

      display:
        block !important;

      width:
        min(170px, 100%) !important;

      min-width:
        100px !important;

      height:
        22px !important;

      padding:
        0 !important;

      cursor:
        pointer !important;
    }


    #${CUSTOM_SIZE_CONTROL_ID}
    span {

      min-width:
        43px;

      color:
        #86abc0;

      font-size:
        11px;

      text-align:
        right;

      font-variant-numeric:
        tabular-nums;
    }


    [${GRID_ATTR}="true"] {

      display:
        grid !important;

      grid-template-columns:
        repeat(
          auto-fill,
          minmax(
            var(
              --sipucol-thumb-size,
              110px
            ),
            var(
              --sipucol-thumb-size,
              110px
            )
          )
        )
        !important;

      justify-content:
        start !important;

      align-items:
        start !important;

      gap:
        10px !important;

      overflow-x:
        hidden !important;
    }


    [${CARD_ATTR}="true"] {

      width:
        var(
          --sipucol-thumb-size,
          110px
        )
        !important;

      min-width:
        var(
          --sipucol-thumb-size,
          110px
        )
        !important;

      max-width:
        var(
          --sipucol-thumb-size,
          110px
        )
        !important;

      height:
        auto !important;

      min-height:
        0 !important;

      overflow:
        hidden !important;

      box-sizing:
        border-box !important;
    }


    [${CARD_ATTR}="true"]
    img {

      display:
        block !important;

      width:
        100% !important;

      height:
        auto !important;

      aspect-ratio:
        4 / 3 !important;

      object-fit:
        cover !important;

      max-width:
        100% !important;

      max-height:
        none !important;
    }


    #sipucol-original-viewer-final {

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
          0.98
        );

      color:
        #ecfff7;
    }


    #sipucol-original-viewer-final.open {

      display:
        grid;
    }


    #sipucol-original-viewer-final
    > header {

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
          49,
          223,
          164,
          0.38
        );

      background:
        rgba(
          5,
          20,
          31,
          0.99
        );
    }


    #sipucol-original-viewer-final
    > header
    > strong {

      color:
        #51e3a8;
    }


    #sipucol-original-viewer-final
    [data-role="resolution"] {

      flex:
        1;

      min-width:
        0;

      color:
        #9ec4b7;

      font-size:
        12px;
    }


    .sipucol-viewer-controls {

      display:
        flex;

      align-items:
        center;

      gap:
        7px;
    }


    .sipucol-viewer-controls
    input[type="range"] {

      width:
        140px;

      cursor:
        pointer;
    }


    .sipucol-viewer-controls
    [data-role="zoom"] {

      min-width:
        47px;

      text-align:
        center;

      font-size:
        12px;

      font-variant-numeric:
        tabular-nums;
    }


    .sipucol-viewer-controls
    button {

      height:
        34px;

      padding:
        0 11px;

      border:
        1px solid
        rgba(
          52,
          225,
          166,
          0.5
        );

      border-radius:
        8px;

      background:
        rgba(
          12,
          91,
          68,
          0.76
        );

      color:
        #effff8;

      cursor:
        pointer;

      font-weight:
        750;
    }


    #sipucol-original-viewer-final
    > main {

      position:
        relative;

      min-width:
        0;

      min-height:
        0;

      overflow:
        auto;

      overscroll-behavior:
        contain;
    }


    #sipucol-original-viewer-final
    > main
    > div {

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


    #sipucol-original-viewer-final
    img {

      display:
        block;

      flex:
        0 0 auto;

      max-width:
        none;

      max-height:
        none;

      object-fit:
        contain;

      image-rendering:
        auto;

      user-select:
        none;

      box-shadow:
        0 20px 70px
        rgba(
          0,
          0,
          0,
          0.65
        );
    }
  `


  document.head.appendChild(
    style
  )
}



/*
===========================================================
APLICACIÓN CONTINUA, LIMITADA AL PANEL FOTOS
===========================================================
*/


function applyFixes() {

  const panel =
    findPhotoPanel()


  if (!panel) {

    return false
  }


  currentPanel =
    panel


  const search =
    findPhotoSearch(
      panel
    )


  releaseSearchInput(
    search
  )


  removeNotSentStatus(
    panel
  )


  hideOldEvaluationBar(
    panel
  )


  installSizeSlider(
    panel
  )


  return true
}



function scheduleApply() {

  if (scheduled) {

    return
  }


  scheduled =
    true


  requestAnimationFrame(

    () => {

      scheduled =
        false


      applyFixes()
    }
  )
}



function attachPanelObserver() {

  if (
    !currentPanel
    || panelObserver
  ) {

    return
  }


  panelObserver =
    new MutationObserver(
      scheduleApply
    )


  panelObserver.observe(

    currentPanel,

    {
      childList:
        true,

      subtree:
        true,

      characterData:
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



function start() {

  installStyles()


  let attempts =
    0


  const timer =
    window.setInterval(

      () => {

        attempts += 1


        if (
          applyFixes()
        ) {

          attachPanelObserver()

          window.clearInterval(
            timer
          )

          return
        }


        if (
          attempts >= 40
        ) {

          window.clearInterval(
            timer
          )
        }
      },

      200
    )
}



if (
  document.readyState
  === "loading"
) {

  document.addEventListener(

    "DOMContentLoaded",

    start,

    {
      once:
        true
    }
  )

} else {

  start()
}
