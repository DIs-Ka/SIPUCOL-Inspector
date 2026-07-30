/*
SIPUCOL — Control estricto de ID Puente

Reglas:
- Únicamente dígitos del 0 al 9.
- Máximo 12 dígitos.
- No convierte letras.
- No elimina caracteres después de escribirlos.
- Bloquea el carácter inválido antes de que entre.
*/

const MAX_ID_LENGTH = 12


function normalizarTexto(valor) {
  return String(valor || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(
      /[\u0300-\u036f]/g,
      ""
    )
}


function buscarInputIdPuente() {

  const labels =
    document.querySelectorAll(
      "label"
    )


  for (
    const label
    of labels
  ) {

    const texto =
      normalizarTexto(
        label.textContent
      )


    if (
      texto !== "id puente"
      && !texto.startsWith(
        "id puente"
      )
    ) {

      continue
    }


    if (
      label.htmlFor
    ) {

      const input =
        document.getElementById(
          label.htmlFor
        )


      if (
        input
        instanceof HTMLInputElement
      ) {

        return input
      }
    }


    const dentro =
      label.querySelector(
        "input"
      )


    if (
      dentro
      instanceof HTMLInputElement
    ) {

      return dentro
    }


    const contenedor =
      label.parentElement


    if (
      contenedor
    ) {

      const input =
        contenedor.querySelector(
          "input"
        )


      if (
        input
        instanceof HTMLInputElement
      ) {

        return input
      }
    }
  }


  const inputs =
    document.querySelectorAll(
      "input"
    )


  for (
    const input
    of inputs
  ) {

    const identidad =
      normalizarTexto(
        [
          input.id,
          input.name,
          input.placeholder,
          input.getAttribute(
            "aria-label"
          ),
          input.getAttribute(
            "data-field"
          )
        ].join(
          " "
        )
      )


    if (
      identidad.includes(
        "idpuente"
      )
      || identidad.includes(
        "id puente"
      )
    ) {

      return input
    }
  }


  return null
}


function cantidadDespuesDeInsertar(
  input,
  texto
) {

  const inicio =
    input.selectionStart
    ?? input.value.length


  const final =
    input.selectionEnd
    ?? inicio


  return (
    input.value.length
    - (
      final
      - inicio
    )
    + texto.length
  )
}


function protegerIdPuente(
  input
) {

  if (
    !input
    || input.dataset
      .sipucolIdGuard
      === "true"
  ) {

    return
  }


  /*
  Se mantiene como texto para
  conservar ceros iniciales.
  */

  input.type =
    "text"


  input.inputMode =
    "numeric"


  input.maxLength =
    MAX_ID_LENGTH


  input.setAttribute(
    "pattern",
    "[0-9]{0,12}"
  )


  input.setAttribute(
    "autocomplete",
    "off"
  )


  input.setAttribute(
    "placeholder",
    "Máximo 12 dígitos"
  )


  input.dataset
    .sipucolIdGuard =
      "true"


  /*
  Bloqueo antes de insertar.
  No hace limpieza posterior.
  */

  input.addEventListener(
    "beforeinput",
    evento => {

      if (
        !evento.inputType
          .startsWith(
            "insert"
          )
      ) {

        return
      }


      const texto =
        evento.data


      if (
        texto === null
      ) {

        return
      }


      if (
        !/^\d+$/.test(
          texto
        )
      ) {

        evento.preventDefault()

        return
      }


      if (
        cantidadDespuesDeInsertar(
          input,
          texto
        )
        > MAX_ID_LENGTH
      ) {

        evento.preventDefault()
      }
    }
  )


  /*
  Bloqueo de teclado.
  Navegación, borrar y atajos
  siguen funcionando.
  */

  input.addEventListener(
    "keydown",
    evento => {

      if (
        evento.ctrlKey
        || evento.metaKey
        || evento.altKey
      ) {

        return
      }


      const permitidas =
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
        permitidas.has(
          evento.key
        )
      ) {

        return
      }


      if (
        /^\d$/.test(
          evento.key
        )
      ) {

        if (
          cantidadDespuesDeInsertar(
            input,
            evento.key
          )
          <= MAX_ID_LENGTH
        ) {

          return
        }
      }


      evento.preventDefault()
    }
  )


  /*
  Pegar:
  solo se permite cuando TODO
  el contenido son dígitos y
  el resultado no supera 12.
  No transforma el texto.
  */

  input.addEventListener(
    "paste",
    evento => {

      const texto =
        evento.clipboardData
          ?.getData(
            "text"
          )
        ?? ""


      if (
        !/^\d+$/.test(
          texto
        )
      ) {

        evento.preventDefault()

        return
      }


      if (
        cantidadDespuesDeInsertar(
          input,
          texto
        )
        > MAX_ID_LENGTH
      ) {

        evento.preventDefault()
      }
    }
  )


  /*
  Arrastrar texto:
  se bloquea para impedir
  caracteres no controlados.
  */

  input.addEventListener(
    "drop",
    evento => {

      const texto =
        evento.dataTransfer
          ?.getData(
            "text"
          )
        ?? ""


      if (
        !/^\d+$/.test(
          texto
        )
        || cantidadDespuesDeInsertar(
          input,
          texto
        )
        > MAX_ID_LENGTH
      ) {

        evento.preventDefault()
      }
    }
  )
}


function aplicarProteccion() {

  protegerIdPuente(
    buscarInputIdPuente()
  )
}


function iniciar() {

  aplicarProteccion()


  const observer =
    new MutationObserver(
      aplicarProteccion
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
}


if (
  document.readyState
  === "loading"
) {

  document.addEventListener(
    "DOMContentLoaded",
    iniciar,
    {
      once:
        true
    }
  )

} else {

  iniciar()
}
