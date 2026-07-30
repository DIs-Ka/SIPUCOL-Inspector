
/*
Oculta únicamente la franja obsoleta del panel Fotos:

- Enviar foto a Evaluación
- Destino
- Botones de componentes
- Scroll perteneciente a esos botones

No elimina lógica ni modifica otros módulos.
*/


const TARGET_BUTTONS = new Set([

  "superficie del puente",

  "juntas de dilatacion",

  "bordillo",

  "barandas",

  "aletas",

  "estribos"
])


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


function findObsoleteBar() {

  const possibleTitles = [

    ...document.querySelectorAll(
      "div, span, p, label, strong"
    )
  ]


  const title = possibleTitles.find(

    element =>

      normalizeText(
        element.textContent
      )
      === "enviar foto a evaluacion"
  )


  if (!title) {

    return null
  }


  let current =
    title.parentElement


  for (
    let level = 0;
    level < 7;
    level += 1
  ) {

    if (!current) {

      break
    }


    const text =
      normalizeText(
        current.textContent
      )


    const buttonNames = [

      ...current.querySelectorAll(
        "button"
      )

    ].map(

      button =>

        normalizeText(
          button.textContent
        )
    )


    const matchingButtons =
      buttonNames.filter(

        name =>

          TARGET_BUTTONS.has(
            name
          )
      ).length


    const isCorrectBlock =

      text.includes(
        "enviar foto a evaluacion"
      )

      && text.includes(
        "destino:"
      )

      && matchingButtons >= 4

      && !text.includes(
        "carpeta actual"
      )

      && !text.includes(
        "no hay foto seleccionada"
      )


    if (isCorrectBlock) {

      return current
    }


    current =
      current.parentElement
  }


  return null
}


function hideObsoleteBar() {

  const obsoleteBar =
    findObsoleteBar()


  if (!obsoleteBar) {

    return false
  }


  obsoleteBar.setAttribute(
    "data-sipucol-hidden-photo-evaluation",
    "true"
  )


  obsoleteBar.style.setProperty(
    "display",
    "none",
    "important"
  )


  return true
}


function installStyle() {

  if (
    document.getElementById(
      "sipucol-hide-photo-evaluation-style"
    )
  ) {

    return
  }


  const style =
    document.createElement(
      "style"
    )


  style.id =
    "sipucol-hide-photo-evaluation-style"


  style.textContent = `

    [data-sipucol-hidden-photo-evaluation="true"] {

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
  `


  document.head.appendChild(
    style
  )
}


function start() {

  installStyle()


  if (
    hideObsoleteBar()
  ) {

    return
  }


  let scheduled =
    false


  const observer =
    new MutationObserver(

      () => {

        if (scheduled) {

          return
        }


        scheduled =
          true


        requestAnimationFrame(

          () => {

            scheduled =
              false


            if (
              hideObsoleteBar()
            ) {

              observer.disconnect()
            }
          }
        )
      }
    )


  observer.observe(
    document.body,
    {
      childList:
        true,

      subtree:
        true
    }
  )


  window.setTimeout(

    () => {

      hideObsoleteBar()

      observer.disconnect()
    },

    15000
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
