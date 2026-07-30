
/*
==========================================================
SIPUCOL UI ESTABLE
==========================================================

Objetivos:
- No limpiar datos al iniciar.
- Mantener el autoguardado original de React.
- Botones verdes planos.
- Botón Limpiar todo.
- Ocultar Enviar foto a Evaluación.
- ID Puente:
    solo dígitos;
    máximo físico de 2;
    no convierte texto;
    bloquea antes de insertar.
- Sin observers permanentes pesados.
*/


const MAX_BRIDGE_ID_LENGTH = 2


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
}


function isBridgeIdInput(
  element
) {

  if (
    !(
      element
      instanceof HTMLInputElement
    )
  ) {

    return false
  }


  const identity =

    normalizeText(

      [
        element.id,
        element.name,
        element.placeholder,
        element.getAttribute(
          "aria-label"
        ),
        element.getAttribute(
          "data-field"
        )
      ].join(
        " "
      )
    )


  if (
    identity.includes(
      "idpuente"
    )

    || identity.includes(
      "id puente"
    )
  ) {

    return true
  }


  let current =
    element.parentElement


  for (
    let level = 0;
    level < 5;
    level += 1
  ) {

    if (!current) {
      break
    }


    const labels =
      current.querySelectorAll(
        "label"
      )


    const hasBridgeLabel =

      [...labels].some(

        label => {

          const text =
            normalizeText(
              label.textContent
            )


          return (

            text === "id puente"

            || text.startsWith(
              "id puente"
            )
          )
        }
      )


    if (
      hasBridgeLabel
    ) {

      const inputs =
        current.querySelectorAll(
          "input"
        )


      if (
        inputs.length === 1

        || [...inputs].includes(
          element
        )
      ) {

        return true
      }
    }


    current =
      current.parentElement
  }


  return false
}


function configureBridgeId(
  input
) {

  if (
    !isBridgeIdInput(
      input
    )
  ) {

    return
  }


  /*
  Text is intentional:
  it preserves leading zeroes.
  */

  try {

    input.type =
      "text"

  } catch {

  }


  input.inputMode =
    "numeric"


  input.maxLength =
    MAX_BRIDGE_ID_LENGTH


  input.setAttribute(
    "maxlength",
    String(
      MAX_BRIDGE_ID_LENGTH
    )
  )


  input.setAttribute(
    "pattern",
    "[0-9]{0,2}"
  )


  input.setAttribute(
    "autocomplete",
    "off"
  )


  input.setAttribute(
    "placeholder",
    "Máximo 2 dígitos"
  )


  input.setAttribute(
    "data-sipucol-id-puente",
    "true"
  )
}


function projectedLength(
  input,
  insertedText
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

    + insertedText.length
  )
}


/*
Capture phase:
these handlers run before React changes
the controlled input value.
*/

document.addEventListener(

  "focusin",

  event => {

    if (
      isBridgeIdInput(
        event.target
      )
    ) {

      configureBridgeId(
        event.target
      )
    }
  },

  true
)


document.addEventListener(

  "keydown",

  event => {

    const input =
      event.target


    if (
      !isBridgeIdInput(
        input
      )
    ) {

      return
    }


    configureBridgeId(
      input
    )


    if (
      event.ctrlKey

      || event.metaKey

      || event.altKey
    ) {

      return
    }


    const allowedKeys =
      new Set([

        "Backspace",

        "Delete",

        "Tab",

        "Enter",

        "Escape",

        "ArrowLeft",

        "ArrowRight",

        "ArrowUp",

        "ArrowDown",

        "Home",

        "End"
      ])


    if (
      allowedKeys.has(
        event.key
      )
    ) {

      return
    }


    const isDigit =

      /^[0-9]$/.test(
        event.key
      )


    if (
      !isDigit
    ) {

      event.preventDefault()

      return
    }


    if (
      projectedLength(
        input,
        event.key
      )
      > MAX_BRIDGE_ID_LENGTH
    ) {

      event.preventDefault()
    }
  },

  true
)


document.addEventListener(

  "beforeinput",

  event => {

    const input =
      event.target


    if (
      !isBridgeIdInput(
        input
      )
    ) {

      return
    }


    configureBridgeId(
      input
    )


    if (
      !String(
        event.inputType
        || ""
      ).startsWith(
        "insert"
      )
    ) {

      return
    }


    const inserted =
      event.data


    if (
      inserted === null
    ) {

      return
    }


    if (
      !/^[0-9]+$/.test(
        inserted
      )
    ) {

      event.preventDefault()

      return
    }


    if (
      projectedLength(
        input,
        inserted
      )
      > MAX_BRIDGE_ID_LENGTH
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
      !isBridgeIdInput(
        input
      )
    ) {

      return
    }


    configureBridgeId(
      input
    )


    const pasted =

      event.clipboardData

      ?.getData(
        "text"
      )

      ?? ""


    if (
      !/^[0-9]+$/.test(
        pasted
      )
    ) {

      event.preventDefault()

      return
    }


    if (
      projectedLength(
        input,
        pasted
      )
      > MAX_BRIDGE_ID_LENGTH
    ) {

      event.preventDefault()
    }
  },

  true
)


document.addEventListener(

  "drop",

  event => {

    const input =
      event.target


    if (
      !isBridgeIdInput(
        input
      )
    ) {

      return
    }


    configureBridgeId(
      input
    )


    const dropped =

      event.dataTransfer

      ?.getData(
        "text"
      )

      ?? ""


    if (
      !/^[0-9]+$/.test(
        dropped
      )

      || projectedLength(
        input,
        dropped
      )
      > MAX_BRIDGE_ID_LENGTH
    ) {

      event.preventDefault()
    }
  },

  true
)


function installStyles() {

  if (
    document.getElementById(
      "sipucol-stable-ui-style"
    )
  ) {

    return
  }


  const style =
    document.createElement(
      "style"
    )


  style.id =
    "sipucol-stable-ui-style"


  style.textContent = `

    .sipucol-main-action {

      min-height:
        42px !important;

      padding:
        0 17px !important;

      border-radius:
        10px !important;

      background-image:
        none !important;

      color:
        #effff8 !important;

      font-size:
        12.5px !important;

      font-weight:
        760 !important;

      text-shadow:
        none !important;

      transition:
        transform 150ms ease,
        filter 150ms ease,
        border-color 150ms ease,
        box-shadow 150ms ease
        !important;
    }


    .sipucol-main-action:hover {

      transform:
        translateY(
          -1px
        )
        !important;

      filter:
        brightness(
          1.1
        )
        !important;

      box-shadow:
        0 0 18px
        rgba(
          46,
          224,
          163,
          0.23
        )
        !important;
    }


    .sipucol-main-action:active {

      transform:
        scale(
          0.985
        )
        !important;
    }


    .sipucol-save {

      background:
        rgba(
          18,
          112,
          78,
          0.84
        )
        !important;

      border:
        1px solid
        rgba(
          61,
          239,
          174,
          0.84
        )
        !important;
    }


    .sipucol-load {

      background:
        rgba(
          13,
          83,
          65,
          0.88
        )
        !important;

      border:
        1px solid
        rgba(
          48,
          203,
          156,
          0.74
        )
        !important;
    }


    .sipucol-excel {

      background:
        rgba(
          17,
          124,
          82,
          0.84
        )
        !important;

      border:
        1px solid
        rgba(
          73,
          229,
          165,
          0.8
        )
        !important;
    }


    .sipucol-pdf {

      background:
        rgba(
          9,
          101,
          79,
          0.88
        )
        !important;

      border:
        1px solid
        rgba(
          43,
          221,
          169,
          0.82
        )
        !important;
    }


    input[
      data-sipucol-id-puente="true"
    ] {

      appearance:
        none !important;

      -webkit-appearance:
        none !important;

      font-variant-numeric:
        tabular-nums;
    }


    [
      data-sipucol-hide-photo-evaluation="true"
    ] {

      display:
        none !important;
    }


    #sipucol-autosave-tools {

      position:
        fixed;

      right:
        16px;

      bottom:
        16px;

      z-index:
        999999;

      display:
        flex;

      align-items:
        center;

      gap:
        8px;

      padding:
        7px;

      border:
        1px solid
        rgba(
          51,
          211,
          157,
          0.28
        );

      border-radius:
        13px;

      background:
        rgba(
          7,
          20,
          34,
          0.97
        );

      box-shadow:
        0 15px 38px
        rgba(
          0,
          0,
          0,
          0.4
        );

      backdrop-filter:
        blur(
          14px
        );
    }


    .sipucol-autosave-label {

      display:
        flex;

      align-items:
        center;

      gap:
        7px;

      padding:
        0 9px;

      color:
        #bfe4d5;

      font-size:
        11px;

      font-weight:
        700;
    }


    .sipucol-autosave-dot {

      width:
        8px;

      height:
        8px;

      border-radius:
        999px;

      background:
        #49d898;

      box-shadow:
        0 0 10px
        rgba(
          73,
          216,
          152,
          0.55
        );
    }


    .sipucol-clear-all {

      min-height:
        34px;

      padding:
        0 12px;

      border:
        1px solid
        rgba(
          255,
          111,
          131,
          0.42
        );

      border-radius:
        9px;

      background:
        rgba(
          153,
          42,
          61,
          0.17
        );

      color:
        #ffbac5;

      cursor:
        pointer;

      font-size:
        11px;

      font-weight:
        780;
    }


    .sipucol-clear-all:hover {

      background:
        rgba(
          178,
          49,
          71,
          0.29
        );
    }
  `


  document.head.appendChild(
    style
  )
}


function styleButtons() {

  const buttons =
    document.querySelectorAll(
      "button"
    )


  let found =
    0


  for (
    const button
    of buttons
  ) {

    const text =
      normalizeText(
        button.textContent
      )


    let className =
      null


    if (
      text.includes(
        "guardar proyecto"
      )
    ) {

      className =
        "sipucol-save"

    } else if (

      text.includes(
        "cargar proyecto"
      )

    ) {

      className =
        "sipucol-load"

    } else if (

      text.includes(
        "guardar excel"
      )

    ) {

      className =
        "sipucol-excel"

    } else if (

      text.includes(
        "guardar pdf"
      )

    ) {

      className =
        "sipucol-pdf"
    }


    if (
      className
    ) {

      button.classList.add(
        "sipucol-main-action",
        className
      )

      found++
    }
  }


  return found
}


function configureVisibleBridgeId() {

  const inputs =
    document.querySelectorAll(
      "input"
    )


  for (
    const input
    of inputs
  ) {

    if (
      isBridgeIdInput(
        input
      )
    ) {

      configureBridgeId(
        input
      )

      return true
    }
  }


  return false
}


function hidePhotoEvaluation() {

  const elements =
    document.querySelectorAll(
      "div, section, header, span"
    )


  for (
    const element
    of elements
  ) {

    const text =
      normalizeText(
        element.textContent
      )


    if (
      text
      !== "enviar foto a evaluacion"
    ) {

      continue
    }


    let current =
      element.parentElement


    for (
      let level = 0;
      level < 5;
      level += 1
    ) {

      if (
        !current
      ) {

        break
      }


      const currentText =
        normalizeText(
          current.textContent
        )


      if (

        currentText.includes(
          "destino:"
        )

        && currentText.length
        < 350

        && current.querySelectorAll(
          "button"
        ).length > 0

      ) {

        current.setAttribute(

          "data-sipucol-hide-photo-evaluation",

          "true"
        )


        return true
      }


      current =
        current.parentElement
    }
  }


  return false
}


function installAutosaveTools() {

  if (
    document.getElementById(
      "sipucol-autosave-tools"
    )
  ) {

    return
  }


  const root =
    document.createElement(
      "div"
    )


  root.id =
    "sipucol-autosave-tools"


  root.innerHTML = `

    <div
      class="
        sipucol-autosave-label
      "
    >

      <span
        class="
          sipucol-autosave-dot
        "
      ></span>

      Autoguardado activo

    </div>


    <button
      type="button"
      class="
        sipucol-clear-all
      "
    >

      Limpiar todo

    </button>
  `


  root
    .querySelector(
      ".sipucol-clear-all"
    )
    .addEventListener(

      "click",

      () => {

        const accepted =
          window.confirm(

            "Se borrarán los datos "
            + "autoguardados de la "
            + "interfaz.\n\n"

            + "Los Excel y proyectos "
            + "guardados en Windows "
            + "no se eliminarán."
          )


        if (
          !accepted
        ) {

          return
        }


        localStorage.clear()

        sessionStorage.clear()

        window.location.reload()
      }
    )


  document.body.appendChild(
    root
  )
}


function applyStableUi() {

  installStyles()

  const buttonCount =
    styleButtons()


  const idReady =
    configureVisibleBridgeId()


  const photoReady =
    hidePhotoEvaluation()


  installAutosaveTools()


  return {

    buttonCount,

    idReady,

    photoReady
  }
}


function startStableUi() {

  /*
  Bounded retries:
  React can mount a few milliseconds later,
  but this stops completely after 5 seconds.
  There is no permanent MutationObserver.
  */

  let attempts =
    0


  const timer =
    window.setInterval(

      () => {

        attempts++


        const result =
          applyStableUi()


        const complete =

          result.buttonCount >= 4

          && result.idReady

          && result.photoReady


        if (
          complete

          || attempts >= 20
        ) {

          window.clearInterval(
            timer
          )
        }
      },

      250
    )


  applyStableUi()
}


if (
  document.readyState
  === "loading"
) {

  document.addEventListener(

    "DOMContentLoaded",

    startStableUi,

    {
      once:
        true
    }
  )

} else {

  startStableUi()
}
