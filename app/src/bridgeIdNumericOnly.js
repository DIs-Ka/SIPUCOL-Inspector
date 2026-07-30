
/*
============================================================
SIPUCOL — ID PUENTE SOLO NUMÉRICO
============================================================

Responsabilidad única:

- Campo ID Puente acepta únicamente números.
- Máximo 2 dígitos.
- Bloquea letras, símbolos, espacios, pegado y arrastre.
- Se reaplica cuando React vuelve a montar Identificación.

No modifica ningún otro campo o módulo.
*/


const FIELD_ATTRIBUTE =
  "data-sipucol-bridge-id-numeric"


const MAX_LENGTH =
  2


let updateScheduled =
  false


const updatingInputs =
  new WeakSet()



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



function findBridgeIdInput() {

  const possibleLabels = [

    ...document.querySelectorAll(
      "label, span, p, small, strong, div"
    )

  ].filter(

    element =>

      normalizeText(
        element.textContent
      )
      === "id puente"
  )


  possibleLabels.sort(

    (
      first,
      second
    ) =>

      first.children.length
      - second.children.length
  )


  for (
    const label
    of possibleLabels
  ) {

    if (
      label instanceof HTMLLabelElement
      && label.htmlFor
    ) {

      const linked =
        document.getElementById(
          label.htmlFor
        )


      if (
        linked
        instanceof HTMLInputElement
      ) {

        return linked
      }
    }


    const internal =
      label.querySelector(
        "input"
      )


    if (
      internal
      instanceof HTMLInputElement
    ) {

      return internal
    }


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



function setNativeValue(
  input,
  value
) {

  const descriptor =
    Object.getOwnPropertyDescriptor(

      HTMLInputElement.prototype,

      "value"
    )


  if (
    descriptor
    ?.set
  ) {

    descriptor.set.call(
      input,
      value
    )

  } else {

    input.value =
      value
  }
}



function sanitizeValue(
  input,
  notifyReact = false
) {

  if (
    !(
      input
      instanceof HTMLInputElement
    )

    || updatingInputs.has(
      input
    )
  ) {

    return
  }


  const cleanValue =
    String(
      input.value || ""
    )
      .replace(
        /\D/g,
        ""
      )
      .slice(
        0,
        MAX_LENGTH
      )


  if (
    cleanValue === input.value
  ) {

    return
  }


  updatingInputs.add(
    input
  )


  setNativeValue(
    input,
    cleanValue
  )


  if (
    notifyReact
  ) {

    input.dispatchEvent(

      new InputEvent(

        "input",

        {
          bubbles:
            true,

          inputType:
            "insertReplacementText",

          data:
            cleanValue
        }
      )
    )
  }


  updatingInputs.delete(
    input
  )
}



function configureBridgeId() {

  const input =
    findBridgeIdInput()


  if (!input) {

    return false
  }


  try {

    input.type =
      "text"

  } catch {

    input.setAttribute(
      "type",
      "text"
    )
  }


  input.setAttribute(
    FIELD_ATTRIBUTE,
    "true"
  )


  input.setAttribute(
    "inputmode",
    "numeric"
  )


  input.setAttribute(
    "pattern",
    "[0-9]*"
  )


  input.setAttribute(
    "maxlength",
    String(
      MAX_LENGTH
    )
  )


  input.setAttribute(
    "autocomplete",
    "off"
  )


  input.setAttribute(
    "aria-label",
    "ID Puente, máximo 2 números"
  )


  sanitizeValue(
    input,
    false
  )


  return true
}



function isBridgeIdInput(
  target
) {

  return (

    target
    instanceof HTMLInputElement

    && target.getAttribute(
      FIELD_ATTRIBUTE
    )
    === "true"
  )
}



function projectedValue(
  input,
  insertedText
) {

  const selectionStart =

    input.selectionStart

    ?? input.value.length


  const selectionEnd =

    input.selectionEnd

    ?? selectionStart


  return (

    input.value.slice(
      0,
      selectionStart
    )

    + insertedText

    + input.value.slice(
      selectionEnd
    )
  )
}



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


    if (
      !/^[0-9]$/.test(
        event.key
      )
    ) {

      event.preventDefault()

      return
    }


    const projected =
      projectedValue(

        input,

        event.key
      )


    if (
      projected.length
      > MAX_LENGTH
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


    const inputType =
      String(
        event.inputType || ""
      )


    if (
      inputType.startsWith(
        "delete"
      )
    ) {

      return
    }


    if (
      !inputType.startsWith(
        "insert"
      )
    ) {

      return
    }


    const inserted =
      String(
        event.data || ""
      )


    if (
      inserted

      && !/^[0-9]+$/.test(
        inserted
      )
    ) {

      event.preventDefault()

      return
    }


    if (
      inserted

      && projectedValue(
        input,
        inserted
      ).length > MAX_LENGTH
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


    const pastedText =

      event.clipboardData

      ?.getData(
        "text"
      )

      ?? ""


    if (
      !/^[0-9]+$/.test(
        pastedText
      )

      || projectedValue(

        input,

        pastedText
      ).length > MAX_LENGTH
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


    const droppedText =

      event.dataTransfer

      ?.getData(
        "text"
      )

      ?? ""


    if (
      !/^[0-9]+$/.test(
        droppedText
      )

      || projectedValue(

        input,

        droppedText
      ).length > MAX_LENGTH
    ) {

      event.preventDefault()
    }
  },

  true
)



document.addEventListener(

  "input",

  event => {

    const input =
      event.target


    if (
      isBridgeIdInput(
        input
      )
    ) {

      sanitizeValue(
        input,
        true
      )
    }
  },

  true
)



document.addEventListener(

  "focusin",

  event => {

    if (
      normalizeText(
        event.target
        ?.getAttribute?.(
          "aria-label"
        )
      )
      .includes(
        "id puente"
      )
    ) {

      configureBridgeId()
    }
  },

  true
)



function scheduleConfigure() {

  if (
    updateScheduled
  ) {

    return
  }


  updateScheduled =
    true


  requestAnimationFrame(

    () => {

      updateScheduled =
        false


      configureBridgeId()
    }
  )
}



function start() {

  configureBridgeId()


  const observer =
    new MutationObserver(
      scheduleConfigure
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

        "maxlength",

        "pattern",

        "inputmode",

        "hidden",

        "class",

        "style"
      ]
    }
  )


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
      scheduleConfigure,
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
