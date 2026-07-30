
/*
============================================================
SIPUCOL — UI FINAL LIMPIA
============================================================

Única capa activa para:
- ID Puente correcto.
- Fecha y hora.
- Panel Fotos.
- Visor original.
- Ocultar Fotos -> Evaluación.

No toca:
- Backend.
- Excel.
- PDF.
- Códigos.
- Datos de Evaluación.
*/


const PHOTO_PANEL_ATTR =
  "data-sipucol-photo-panel-final"


const PHOTO_SEARCH_ATTR =
  "data-sipucol-photo-search-final"


const BRIDGE_ID_ATTR =
  "data-sipucol-bridge-id-final"


const PHOTO_SEND_ATTR =
  "data-sipucol-photo-send-hidden-final"


const ZOOM_MIN =
  0.25


const ZOOM_MAX =
  1.50


let photoPanelObserver =
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



function setAttributeIfDifferent(
  element,
  name,
  value
) {

  if (
    element.getAttribute(
      name
    )
    !== String(
      value
    )
  ) {

    element.setAttribute(
      name,
      String(
        value
      )
    )
  }
}



function findPanelByTitle(
  titleText,
  requiredButton
) {

  const wantedTitle =
    normalizeText(
      titleText
    )


  const wantedButton =
    normalizeText(
      requiredButton
    )


  const titles = [

    ...document.querySelectorAll(
      "h1, h2, h3, header, strong, div, span"
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
      !== wantedTitle
    ) {

      continue
    }


    let current =
      title.parentElement


    for (
      let level = 0;
      level < 10;
      level += 1
    ) {

      if (!current) {
        break
      }


      const hasRequiredButton = [

        ...current.querySelectorAll(
          "button"
        )

      ].some(

        button =>

          normalizeText(
            button.textContent
          )
          === wantedButton
      )


      if (
        hasRequiredButton
      ) {

        return current
      }


      current =
        current.parentElement
    }
  }


  return null
}



/*
============================================================
ID PUENTE / FECHA / HORA
============================================================
*/


function findInputByCaption(
  panel,
  caption
) {

  if (!panel) {
    return null
  }


  const wanted =
    normalizeText(
      caption
    )


  const captions = [

    ...panel.querySelectorAll(
      "label, span, div, p"
    )

  ].filter(

    element =>

      normalizeText(
        element.textContent
      )
      === wanted
  )


  captions.sort(

    (
      first,
      second
    ) =>

      first.children.length
      - second.children.length
  )


  for (
    const captionElement
    of captions
  ) {

    if (
      captionElement
      instanceof HTMLLabelElement

      && captionElement.htmlFor
    ) {

      const linked =
        document.getElementById(
          captionElement.htmlFor
        )


      if (
        linked
        instanceof HTMLInputElement
      ) {

        return linked
      }
    }


    const internal =
      captionElement.querySelector(
        "input"
      )


    if (
      internal
      instanceof HTMLInputElement
    ) {

      return internal
    }


    let current =
      captionElement.parentElement


    for (
      let level = 0;
      level < 3;
      level += 1
    ) {

      if (!current) {
        break
      }


      const inputs =
        current.querySelectorAll(
          "input"
        )


      if (
        inputs.length === 1
      ) {

        return inputs[0]
      }


      current =
        current.parentElement
    }
  }


  return null
}



function configureEvaluationFields() {

  const evaluationPanel =
    findPanelByTitle(
      "Evaluación",
      "Guardar proyecto"
    )


  if (!evaluationPanel) {

    return
  }


  const bridgeId =
    findInputByCaption(
      evaluationPanel,
      "ID Puente"
    )


  if (bridgeId) {

    try {

      bridgeId.type =
        "text"

    } catch {

    }


    setAttributeIfDifferent(
      bridgeId,
      BRIDGE_ID_ATTR,
      "true"
    )


    setAttributeIfDifferent(
      bridgeId,
      "maxlength",
      "2"
    )


    setAttributeIfDifferent(
      bridgeId,
      "inputmode",
      "numeric"
    )


    setAttributeIfDifferent(
      bridgeId,
      "pattern",
      "[0-9]{0,2}"
    )


    if (
      bridgeId.placeholder
      !== "00"
    ) {

      bridgeId.placeholder =
        "00"
    }
  }


  const dateInput =
    findInputByCaption(
      evaluationPanel,
      "Fecha de levantamiento"
    )


  if (dateInput) {

    try {

      dateInput.type =
        "date"

    } catch {

    }


    dateInput.style.colorScheme =
      "dark"
  }


  const timeInput =
    findInputByCaption(
      evaluationPanel,
      "Hora"
    )


  if (timeInput) {

    try {

      timeInput.type =
        "time"

    } catch {

    }


    timeInput.step =
      "60"


    timeInput.style.colorScheme =
      "dark"
  }
}



function projectedLength(
  input,
  inserted
) {

  const start =

    input.selectionStart

    ?? input.value.length


  const end =

    input.selectionEnd

    ?? start


  return (

    input.value.length

    - (
      end
      - start
    )

    + inserted.length
  )
}



document.addEventListener(

  "keydown",

  event => {

    const input =
      event.target


    if (
      !(
        input
        instanceof HTMLInputElement
      )

      || input.getAttribute(
        BRIDGE_ID_ATTR
      )
      !== "true"
    ) {

      return
    }


    if (
      event.ctrlKey
      || event.metaKey
      || event.altKey
    ) {

      return
    }


    const allowed = new Set([

      "Backspace",

      "Delete",

      "Tab",

      "Enter",

      "Escape",

      "ArrowLeft",

      "ArrowRight",

      "Home",

      "End"
    ])


    if (
      allowed.has(
        event.key
      )
    ) {

      return
    }


    if (
      !/^[0-9]$/.test(
        event.key
      )

      || projectedLength(
        input,
        event.key
      ) > 2
    ) {

      event.preventDefault()
    }
  },

  true
)



document.addEventListener(

  "paste",

  event => {

    const input =
      event.target


    if (
      !(
        input
        instanceof HTMLInputElement
      )

      || input.getAttribute(
        BRIDGE_ID_ATTR
      )
      !== "true"
    ) {

      return
    }


    const text =

      event.clipboardData

      ?.getData(
        "text"
      )

      ?? ""


    if (
      !/^[0-9]+$/.test(
        text
      )

      || projectedLength(
        input,
        text
      ) > 2
    ) {

      event.preventDefault()
    }
  },

  true
)



/*
============================================================
PANEL FOTOS
============================================================
*/


function findPhotoPanel() {

  const panel =
    findPanelByTitle(
      "Fotos",
      "Cargar"
    )


  if (panel) {

    setAttributeIfDifferent(
      panel,
      PHOTO_PANEL_ATTR,
      "true"
    )
  }


  return panel
}



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
            "buscar foto"
          )

          || placeholder.includes(
            "maximo 2 digitos"
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

      < panelTop + 180

  ) || null
}



function configurePhotoSearch(
  panel
) {

  const input =
    findPhotoSearch(
      panel
    )


  if (!input) {

    return
  }


  setAttributeIfDifferent(
    input,
    PHOTO_SEARCH_ATTR,
    "true"
  )


  try {

    input.type =
      "text"

  } catch {

  }


  if (
    input.placeholder
    !== "Buscar foto..."
  ) {

    input.placeholder =
      "Buscar foto..."
  }


  const attributesToRemove = [

    "maxlength",

    "pattern",

    "min",

    "max",

    "step",

    "data-sipucol-real-id",

    "data-sipucol-id-puente",

    "data-sipucol-bridge-id",

    "data-sipucol-id-guard",

    "data-sipucol-only-digits"
  ]


  for (
    const attribute
    of attributesToRemove
  ) {

    if (
      input.hasAttribute(
        attribute
      )
    ) {

      input.removeAttribute(
        attribute
      )
    }
  }


  if (
    input.inputMode
    !== "search"
  ) {

    input.inputMode =
      "search"
  }
}



/*
Impide que cualquier listener antiguo del ID
capture el buscador de Fotos.

No usa preventDefault:
el navegador y React siguen recibiendo el texto.
*/


function protectPhotoSearchEvent(
  event
) {

  const input =
    event.target


  if (
    !(
      input
      instanceof HTMLInputElement
    )

    || input.getAttribute(
      PHOTO_SEARCH_ATTR
    )
    !== "true"
  ) {

    return
  }


  event.stopImmediatePropagation()
}



window.addEventListener(
  "keydown",
  protectPhotoSearchEvent,
  true
)


window.addEventListener(
  "beforeinput",
  protectPhotoSearchEvent,
  true
)


window.addEventListener(
  "paste",
  protectPhotoSearchEvent,
  true
)



function configureThumbnailSlider(
  panel
) {

  const captions = [

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
    const caption
    of captions
  ) {

    let current =
      caption.parentElement


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
            PHOTO_SEARCH_ATTR
          )
          !== "true"

          && candidate.type !== "file"
      )


      if (input) {

        try {

          input.type =
            "range"

        } catch {

        }


        setAttributeIfDifferent(
          input,
          "min",
          "60"
        )


        setAttributeIfDifferent(
          input,
          "max",
          "240"
        )


        setAttributeIfDifferent(
          input,
          "step",
          "5"
        )


        input.removeAttribute(
          "pattern"
        )


        input.removeAttribute(
          "maxlength"
        )


        input.style.setProperty(
          "appearance",
          "auto",
          "important"
        )


        input.style.setProperty(
          "-webkit-appearance",
          "auto",
          "important"
        )


        input.style.setProperty(
          "width",
          "150px",
          "important"
        )


        input.style.setProperty(
          "height",
          "22px",
          "important"
        )


        return
      }


      current =
        current.parentElement
    }
  }
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
    elements[0]


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



function hidePhotoSendBar(
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


  const allElements = [

    ...panel.querySelectorAll(
      "div, span, p, label, strong, button, nav, section"
    )
  ]


  const title =
    allElements.find(

      element =>

        normalizeText(
          element.textContent
        )
        === "enviar foto a evaluacion"
    )


  const destination =
    allElements.find(

      element =>

        normalizeText(
          element.textContent
        )
        .startsWith(
          "destino:"
        )
    )


  const targetButtons = [

    ...panel.querySelectorAll(
      "button, [role='button']"
    )

  ].filter(

    element =>

      targetNames.has(

        normalizeText(
          element.textContent
        )
      )
  )


  const relevant = [

    title,

    destination,

    ...targetButtons
  ].filter(
    Boolean
  )


  if (
    relevant.length < 4
  ) {

    return
  }


  let common =
    lowestCommonAncestor(

      relevant,

      panel
    )


  if (
    common
    && common !== panel
  ) {

    const text =
      normalizeText(
        common.textContent
      )


    if (
      !text.includes(
        "carpeta actual"
      )

      && !text.includes(
        "no hay foto seleccionada"
      )
    ) {

      setAttributeIfDifferent(
        common,
        PHOTO_SEND_ATTR,
        "true"
      )


      common.style.setProperty(
        "display",
        "none",
        "important"
      )


      return
    }
  }


  /*
  Fallback visual:
  oculta encabezado y fila de botones
  aunque no compartan un único contenedor.
  */


  if (title) {

    const titleContainer =
      title.parentElement


    if (titleContainer) {

      titleContainer.style.setProperty(
        "display",
        "none",
        "important"
      )
    }
  }


  if (destination) {

    destination.style.setProperty(
      "display",
      "none",
      "important"
    )
  }


  const buttonParents =
    targetButtons
      .map(
        button =>
          button.parentElement
      )
      .filter(
        Boolean
      )


  const buttonsContainer =
    lowestCommonAncestor(

      buttonParents,

      panel
    )


  if (
    buttonsContainer
    && buttonsContainer !== panel
  ) {

    buttonsContainer.style.setProperty(
      "display",
      "none",
      "important"
    )
  }


  for (
    const button
    of targetButtons
  ) {

    button.style.setProperty(
      "display",
      "none",
      "important"
    )
  }
}



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
}



/*
============================================================
VISOR ORIGINAL — 25 % A 150 %
============================================================
*/


function elementIsVisible(
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



function findMainPhoto(
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


    const images = [

      ...current.querySelectorAll(
        "img"
      )

    ].filter(
      elementIsVisible
    )


    if (
      images.length === 1
    ) {

      return images[0]
    }


    current =
      current.parentElement
  }


  const images = [

    ...panel.querySelectorAll(
      "img"
    )

  ].filter(
    elementIsVisible
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



function bestImageSource(
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

    || image.currentSrc

    || image.src
  )
}



function createViewer() {

  let viewer =
    document.getElementById(
      "sipucol-photo-viewer-final"
    )


  if (viewer) {

    return viewer
  }


  viewer =
    document.createElement(
      "div"
    )


  viewer.id =
    "sipucol-photo-viewer-final"


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


  const image =
    viewer.querySelector(
      "img"
    )


  const stage =
    viewer.querySelector(
      "main"
    )


  const slider =
    viewer.querySelector(
      'input[type="range"]'
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

    slider,

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


    const percentage =
      Math.round(
        state.zoom * 100
      )


    state.image.style.width =
      `${Math.round(
        state.naturalWidth
        * state.zoom
      )}px`


    state.image.style.height =
      `${Math.round(
        state.naturalHeight
        * state.zoom
      )}px`


    state.slider.value =
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

    viewer._state.zoom =
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


  function fitImage() {

    const state =
      viewer._state


    const fitted =
      Math.min(

        1,

        (
          state.stage.clientWidth
          - 48
        )
        / state.naturalWidth,

        (
          state.stage.clientHeight
          - 48
        )
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


  slider.addEventListener(

    "input",

    () => {

      setZoom(

        Number(
          slider.value
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

    fitImage
  )


  function closeViewer() {

    viewer.classList.remove(
      "open"
    )


    image.removeAttribute(
      "src"
    )
  }


  viewer.querySelector(
    '[data-action="close"]'
  ).addEventListener(

    "click",

    closeViewer
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


      setZoom(

        viewer._state.zoom

        + (
          event.deltaY < 0
          ? 0.05
          : -0.05
        )
      )
    },

    {
      passive:
        false
    }
  )


  viewer._setZoom =
    setZoom


  viewer._close =
    closeViewer


  return viewer
}



function openOriginalPhoto(
  sourceImage
) {

  const source =
    bestImageSource(
      sourceImage
    )


  if (!source) {

    return
  }


  const viewer =
    createViewer()


  const state =
    viewer._state


  state.resolutionLabel.textContent =
    "Cargando imagen original..."


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


    const photoPanel =
      findPhotoPanel()


    if (
      !photoPanel
      || !photoPanel.contains(
        button
      )
    ) {

      return
    }


    const image =
      findMainPhoto(

        photoPanel,

        button
      )


    if (!image) {

      return
    }


    event.preventDefault()

    event.stopImmediatePropagation()


    openOriginalPhoto(
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
        "sipucol-photo-viewer-final"
      )


    if (
      viewer
      ?.classList
      .contains(
        "open"
      )
    ) {

      viewer._close()
    }
  }
)



/*
============================================================
ESTILOS
============================================================
*/


function installStyles() {

  if (
    document.getElementById(
      "sipucol-final-ui-style"
    )
  ) {

    return
  }


  const style =
    document.createElement(
      "style"
    )


  style.id =
    "sipucol-final-ui-style"


  style.textContent = `

    [${PHOTO_SEND_ATTR}="true"] {

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


    [${PHOTO_PANEL_ATTR}="true"]
    input[type="range"] {

      appearance:
        auto !important;

      -webkit-appearance:
        auto !important;

      cursor:
        pointer !important;
    }


    #sipucol-photo-viewer-final {

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
        #edfff8;
    }


    #sipucol-photo-viewer-final.open {

      display:
        grid;
    }


    #sipucol-photo-viewer-final
    > header {

      display:
        flex;

      align-items:
        center;

      gap:
        8px;

      min-height:
        58px;

      padding:
        8px 14px;

      border-bottom:
        1px solid
        rgba(
          51,
          225,
          167,
          0.4
        );

      background:
        #071722;
    }


    #sipucol-photo-viewer-final
    > header
    > strong {

      color:
        #50e2a7;
    }


    #sipucol-photo-viewer-final
    [data-role="resolution"] {

      flex:
        1;

      color:
        #9fc5b8;

      font-size:
        12px;
    }


    #sipucol-photo-viewer-final
    > header
    input[type="range"] {

      width:
        150px;
    }


    #sipucol-photo-viewer-final
    > header
    button {

      height:
        34px;

      padding:
        0 11px;

      border:
        1px solid
        rgba(
          50,
          225,
          165,
          0.5
        );

      border-radius:
        8px;

      background:
        rgba(
          12,
          92,
          69,
          0.76
        );

      color:
        #effff8;

      cursor:
        pointer;
    }


    #sipucol-photo-viewer-final
    > main {

      min-width:
        0;

      min-height:
        0;

      overflow:
        auto;

      overscroll-behavior:
        contain;
    }


    #sipucol-photo-viewer-final
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


    #sipucol-photo-viewer-final
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
============================================================
APLICACIÓN
============================================================
*/


function applyAllFixes() {

  installStyles()

  configureEvaluationFields()


  const photoPanel =
    findPhotoPanel()


  if (!photoPanel) {

    return false
  }


  configurePhotoSearch(
    photoPanel
  )


  configureThumbnailSlider(
    photoPanel
  )


  hidePhotoSendBar(
    photoPanel
  )


  removeNotSentStatus(
    photoPanel
  )


  return true
}



function scheduleUpdate() {

  if (updateScheduled) {

    return
  }


  updateScheduled =
    true


  requestAnimationFrame(

    () => {

      updateScheduled =
        false


      applyAllFixes()
    }
  )
}



function attachPhotoObserver() {

  const photoPanel =
    findPhotoPanel()


  if (
    !photoPanel
    || photoPanelObserver
  ) {

    return
  }


  photoPanelObserver =
    new MutationObserver(
      scheduleUpdate
    )


  photoPanelObserver.observe(

    photoPanel,

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

        "type",

        "min",

        "max",

        "step"
      ]
    }
  )
}



function start() {

  let attempts =
    0


  const timer =
    window.setInterval(

      () => {

        attempts += 1


        if (
          applyAllFixes()
        ) {

          attachPhotoObserver()

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
