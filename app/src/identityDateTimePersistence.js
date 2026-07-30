
/*
============================================================
SIPUCOL — PERSISTENCIA DE FECHA Y HORA
============================================================

Responsabilidad única:

- Fecha de levantamiento siempre es input type="date".
- Hora siempre es input type="time".
- Reaplica los tipos cuando Identificación se oculta y
  React vuelve a montar los campos.
- No modifica valores, datos ni otros módulos.
*/


const DATE_FIELD_ATTRIBUTE =
  "data-sipucol-date-field-stable"


const TIME_FIELD_ATTRIBUTE =
  "data-sipucol-time-field-stable"


const STYLE_ID =
  "sipucol-date-time-persistence-style"


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



function findEvaluationPanel() {

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
      !== "evaluacion"
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


      const buttonTexts = [

        ...current.querySelectorAll(
          "button"
        )

      ].map(

        button =>

          normalizeText(
            button.textContent
          )
      )


      const hasProjectControls =

        buttonTexts.includes(
          "guardar proyecto"
        )

        || buttonTexts.includes(
          "guardar excel"
        )

        || buttonTexts.includes(
          "limpiar todo"
        )


      if (hasProjectControls) {

        return current
      }


      current =
        current.parentElement
    }
  }


  return document.body
}



function findInputByCaption(
  root,
  caption
) {

  const expected =
    normalizeText(
      caption
    )


  const captions = [

    ...root.querySelectorAll(
      "label, span, p, small, div"
    )

  ].filter(

    element =>

      normalizeText(
        element.textContent
      )
      === expected
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

      const linkedInput =
        document.getElementById(
          captionElement.htmlFor
        )


      if (
        linkedInput
        instanceof HTMLInputElement
      ) {

        return linkedInput
      }
    }


    const internalInput =
      captionElement.querySelector(
        "input"
      )


    if (
      internalInput
      instanceof HTMLInputElement
    ) {

      return internalInput
    }


    let current =
      captionElement.parentElement


    for (
      let level = 0;
      level < 4;
      level += 1
    ) {

      if (!current) {

        break
      }


      const inputs = [

        ...current.querySelectorAll(
          "input"
        )

      ].filter(

        input =>

          input.type !== "hidden"
          && input.type !== "file"
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



function setInputTypeSafely(
  input,
  type,
  marker
) {

  if (
    !(
      input
      instanceof HTMLInputElement
    )
  ) {

    return false
  }


  const previousValue =
    input.value


  if (
    input.type !== type
  ) {

    try {

      input.type =
        type

    } catch {

      input.setAttribute(
        "type",
        type
      )
    }
  }


  if (
    input.getAttribute(
      "type"
    )
    !== type
  ) {

    input.setAttribute(
      "type",
      type
    )
  }


  input.setAttribute(
    marker,
    "true"
  )


  input.style.colorScheme =
    "dark"


  input.removeAttribute(
    "inputmode"
  )


  input.removeAttribute(
    "pattern"
  )


  input.removeAttribute(
    "maxlength"
  )


  /*
  Normalmente React vuelve a colocar el valor guardado.
  Este respaldo evita que el navegador lo pierda durante
  el cambio de text a date/time cuando ya era válido.
  */


  if (
    !input.value
    && previousValue
  ) {

    const validDate =

      type === "date"

      && /^\d{4}-\d{2}-\d{2}$/.test(
        previousValue
      )


    const validTime =

      type === "time"

      && /^\d{2}:\d{2}(?::\d{2})?$/.test(
        previousValue
      )


    if (
      validDate
      || validTime
    ) {

      input.value =
        previousValue
    }
  }


  if (
    type === "time"
  ) {

    input.step =
      "60"
  }


  return true
}



function applyDateTimeTypes() {

  const panel =
    findEvaluationPanel()


  const dateInput =
    findInputByCaption(
      panel,
      "Fecha de levantamiento"
    )


  const timeInput =
    findInputByCaption(
      panel,
      "Hora"
    )


  setInputTypeSafely(

    dateInput,

    "date",

    DATE_FIELD_ATTRIBUTE
  )


  setInputTypeSafely(

    timeInput,

    "time",

    TIME_FIELD_ATTRIBUTE
  )


  return Boolean(
    dateInput
    || timeInput
  )
}



function scheduleApply() {

  if (updateScheduled) {

    return
  }


  updateScheduled =
    true


  requestAnimationFrame(

    () => {

      updateScheduled =
        false


      applyDateTimeTypes()
    }
  )
}



function runAfterToggle() {

  scheduleApply()


  window.setTimeout(
    scheduleApply,
    0
  )


  window.setTimeout(
    scheduleApply,
    60
  )


  window.setTimeout(
    scheduleApply,
    180
  )


  window.setTimeout(
    scheduleApply,
    450
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


    const text =
      normalizeText(
        button.textContent
      )


    if (
      text.includes(
        "mostrar"
      )

      || text.includes(
        "ocultar"
      )

      || text.includes(
        "identificacion"
      )
    ) {

      runAfterToggle()
    }
  },

  true
)



document.addEventListener(

  "focusin",

  event => {

    const input =
      event.target


    if (
      !(
        input
        instanceof HTMLInputElement
      )
    ) {

      return
    }


    const marker =

      input.getAttribute(
        DATE_FIELD_ATTRIBUTE
      )

      || input.getAttribute(
        TIME_FIELD_ATTRIBUTE
      )


    if (marker) {

      scheduleApply()
    }
  },

  true
)



function installStyles() {

  if (
    document.getElementById(
      STYLE_ID
    )
  ) {

    return
  }


  const style =
    document.createElement(
      "style"
    )


  style.id =
    STYLE_ID


  style.textContent = `

    input[${DATE_FIELD_ATTRIBUTE}="true"],

    input[${TIME_FIELD_ATTRIBUTE}="true"] {

      color-scheme:
        dark !important;
    }


    input[${DATE_FIELD_ATTRIBUTE}="true"]
   ::-webkit-calendar-picker-indicator,

    input[${TIME_FIELD_ATTRIBUTE}="true"]
   ::-webkit-calendar-picker-indicator {

      display:
        block !important;

      visibility:
        visible !important;

      opacity:
        0.92 !important;

      cursor:
        pointer !important;
    }
  `


  document.head.appendChild(
    style
  )
}



function start() {

  installStyles()


  applyDateTimeTypes()


  /*
  Detecta cuando React desmonta y vuelve a crear
  la sección Identificación.
  */


  const observer =
    new MutationObserver(
      scheduleApply
    )


  observer.observe(

    document.body,

    {
      childList:
        true,

      subtree:
        true,

      attributes:
        true,

      attributeFilter: [

        "type",

        "hidden",

        "class",

        "style"
      ]
    }
  )


  /*
  Pasadas iniciales para cubrir carga de proyecto,
  autoguardado y montaje tardío.
  */


  const delays = [

    0,

    50,

    150,

    350,

    700,

    1200
  ]


  for (
    const delay
    of delays
  ) {

    window.setTimeout(
      scheduleApply,
      delay
    )
  }
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
