
/*
============================================================
SIPUCOL — LIMPIEZA VISUAL FINAL DEL PANEL FOTOS
============================================================

Elimina exclusivamente:

1. Enviar foto a Evaluación.
2. Destino: ...
3. Botones Superficie/Juntas/Bordillo/Barandas/Aletas/Estribos.
4. Scroll azul perteneciente a esa franja.
5. Estado: Sin enviar.

No modifica buscador, slider, miniaturas, visor, zoom,
Evaluación, PDF, Excel, backend ni Códigos.
*/


const HIDDEN_SEND_ATTR =
  "data-sipucol-photo-send-area-hidden"


const HIDDEN_STATUS_ATTR =
  "data-sipucol-photo-status-hidden"


const TARGET_BUTTON_NAMES = new Set([

  "superficie del puente",

  "juntas de dilatacion",

  "bordillo",

  "barandas",

  "aletas",

  "estribos"
])


let observedPanel =
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



function findPhotoPanel() {

  const possibleTitles = [

    ...document.querySelectorAll(
      "h1, h2, h3, header, strong, div, span"
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
      level < 10;
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

        return current
      }


      current =
        current.parentElement
    }
  }


  return null
}



function commonAncestor(
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



function hideElement(
  element,
  attribute
) {

  if (
    !element

    || element === observedPanel
  ) {

    return
  }


  if (
    element.getAttribute(
      attribute
    )
    !== "true"
  ) {

    element.setAttribute(
      attribute,
      "true"
    )
  }


  element.style.setProperty(
    "display",
    "none",
    "important"
  )
}



function findExactElement(
  panel,
  expectedText
) {

  const expected =
    normalizeText(
      expectedText
    )


  return [

    ...panel.querySelectorAll(
      "div, span, p, label, strong, small"
    )

  ].find(

    element =>

      normalizeText(
        element.textContent
      )
      === expected
  ) || null
}



function findDestinationElement(
  panel
) {

  return [

    ...panel.querySelectorAll(
      "div, span, p, label, strong, small"
    )

  ].find(

    element =>

      normalizeText(
        element.textContent
      )
      .startsWith(
        "destino:"
      )
  ) || null
}



/*
============================================================
QUITAR FRANJA FOTOS -> EVALUACIÓN
============================================================
*/


function hidePhotoEvaluationArea(
  panel
) {

  const title =
    findExactElement(

      panel,

      "Enviar foto a Evaluación"
    )


  const destination =
    findDestinationElement(
      panel
    )


  const destinationButtons = [

    ...panel.querySelectorAll(
      "button, [role='button']"
    )

  ].filter(

    element =>

      TARGET_BUTTON_NAMES.has(

        normalizeText(
          element.textContent
        )
      )
  )


  /*
  1. Ocultar la cabecera:
     Enviar foto... + Destino...
  */


  if (
    title

    && destination
  ) {

    const headerCommon =
      commonAncestor(

        [
          title,
          destination
        ],

        panel
      )


    if (
      headerCommon

      && headerCommon !== panel
    ) {

      const headerText =
        normalizeText(
          headerCommon.textContent
        )


      const headerButtonCount =
        headerCommon.querySelectorAll(
          "button"
        ).length


      if (
        headerText.includes(
          "enviar foto a evaluacion"
        )

        && headerText.includes(
          "destino:"
        )

        && headerButtonCount === 0
      ) {

        hideElement(

          headerCommon,

          HIDDEN_SEND_ATTR
        )

      } else {

        hideElement(

          title,

          HIDDEN_SEND_ATTR
        )


        hideElement(

          destination,

          HIDDEN_SEND_ATTR
        )
      }
    }

  } else {

    hideElement(

      title,

      HIDDEN_SEND_ATTR
    )


    hideElement(

      destination,

      HIDDEN_SEND_ATTR
    )
  }


  /*
  2. Ocultar la fila completa de botones,
     incluyendo el scroll azul inferior.
  */


  if (
    destinationButtons.length > 0
  ) {

    const buttonContainers =
      destinationButtons
        .map(

          button =>

            button.parentElement
        )
        .filter(
          Boolean
        )


    let rowContainer =
      commonAncestor(

        buttonContainers,

        panel
      )


    /*
    Subimos hasta el contenedor que contiene
    casi todos los botones, pero nunca hasta
    el panel Fotos completo.
    */


    while (
      rowContainer

      && rowContainer.parentElement

      && rowContainer.parentElement !== panel
    ) {

      const parent =
        rowContainer.parentElement


      const matchingButtons = [

        ...parent.querySelectorAll(
          "button, [role='button']"
        )

      ].filter(

        element =>

          TARGET_BUTTON_NAMES.has(

            normalizeText(
              element.textContent
            )
          )
      ).length


      const parentText =
        normalizeText(
          parent.textContent
        )


      if (
        matchingButtons
        < Math.min(
          4,
          destinationButtons.length
        )

        || parentText.includes(
          "carpeta actual"
        )

        || parentText.includes(
          "no hay foto seleccionada"
        )

        || parentText.includes(
          "ver grande"
        )
      ) {

        break
      }


      rowContainer =
        parent
    }


    if (
      rowContainer

      && rowContainer !== panel
    ) {

      hideElement(

        rowContainer,

        HIDDEN_SEND_ATTR
      )

    } else {

      for (
        const button
        of destinationButtons
      ) {

        hideElement(

          button,

          HIDDEN_SEND_ATTR
        )
      }
    }
  }


  /*
  3. Respaldo: cualquier scrollbar horizontal
     inmediatamente relacionado con los botones.
  */


  const scrollCandidates = [

    ...panel.querySelectorAll(
      "div"
    )

  ].filter(

    element => {

      if (
        element.getAttribute(
          HIDDEN_SEND_ATTR
        )
        === "true"
      ) {

        return false
      }


      const style =
        window.getComputedStyle(
          element
        )


      const containsTargetButton = [

        ...element.querySelectorAll(
          "button, [role='button']"
        )

      ].some(

        button =>

          TARGET_BUTTON_NAMES.has(

            normalizeText(
              button.textContent
            )
          )
      )


      return (

        containsTargetButton

        && (
          style.overflowX === "auto"

          || style.overflowX === "scroll"

          || element.scrollWidth
             > element.clientWidth + 2
        )
      )
    }
  )


  for (
    const scrollContainer
    of scrollCandidates
  ) {

    const text =
      normalizeText(
        scrollContainer.textContent
      )


    if (
      !text.includes(
        "carpeta actual"
      )

      && !text.includes(
        "ver grande"
      )
    ) {

      hideElement(

        scrollContainer,

        HIDDEN_SEND_ATTR
      )
    }
  }
}



/*
============================================================
QUITAR ESTADO: SIN ENVIAR
============================================================
*/


function removeNotSentStatus(
  panel
) {

  /*
  Caso 1:
  el texto está solo dentro de un elemento.
  */


  const exactElements = [

    ...panel.querySelectorAll(
      "div, span, p, small, label"
    )

  ].filter(

    element =>

      normalizeText(
        element.textContent
      )
      === "estado: sin enviar"
  )


  for (
    const element
    of exactElements
  ) {

    hideElement(

      element,

      HIDDEN_STATUS_ATTR
    )
  }


  /*
  Caso 2:
  React dejó el texto mezclado dentro de
  otro contenedor junto con nombre y ruta.
  */


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
    const node
    of textNodes
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


    const updated =
      original.replace(

        /(?:\r?\n)?\s*Estado\s*:\s*Sin enviar\s*/gi,

        ""
      )


    if (
      node.nodeValue !== updated
    ) {

      node.nodeValue =
        updated
    }


    const parent =
      node.parentElement


    if (
      parent

      && normalizeText(
        parent.textContent
      )
      === ""
    ) {

      hideElement(

        parent,

        HIDDEN_STATUS_ATTR
      )
    }
  }
}



/*
============================================================
APLICACIÓN
============================================================
*/


function applyVisualCleanup() {

  const panel =
    findPhotoPanel()


  if (!panel) {

    return false
  }


  observedPanel =
    panel


  hidePhotoEvaluationArea(
    panel
  )


  removeNotSentStatus(
    panel
  )


  return true
}



function scheduleCleanup() {

  if (updateScheduled) {

    return
  }


  updateScheduled =
    true


  requestAnimationFrame(

    () => {

      updateScheduled =
        false


      applyVisualCleanup()
    }
  )
}



function attachObserver() {

  if (
    !observedPanel

    || panelObserver
  ) {

    return
  }


  panelObserver =
    new MutationObserver(
      scheduleCleanup
    )


  panelObserver.observe(

    observedPanel,

    {
      childList:
        true,

      subtree:
        true,

      characterData:
        true
    }
  )
}



function installStyles() {

  if (
    document.getElementById(
      "sipucol-photo-visual-cleanup-style"
    )
  ) {

    return
  }


  const style =
    document.createElement(
      "style"
    )


  style.id =
    "sipucol-photo-visual-cleanup-style"


  style.textContent = `

    [${HIDDEN_SEND_ATTR}="true"],

    [${HIDDEN_STATUS_ATTR}="true"] {

      display:
        none !important;

      visibility:
        hidden !important;

      width:
        0 !important;

      height:
        0 !important;

      min-width:
        0 !important;

      min-height:
        0 !important;

      max-width:
        0 !important;

      max-height:
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
  `


  document.head.appendChild(
    style
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
          applyVisualCleanup()
        ) {

          attachObserver()

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
