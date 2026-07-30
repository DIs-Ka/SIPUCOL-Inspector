
/*
SIPUCOL — Pulido visual de controles

No reemplaza funciones.
No cambia eventos.
Solo añade clases y estilos.
*/

const style = document.createElement("style")

style.textContent = `
  .sipucol-project-action {
    position: relative !important;
    min-height: 42px !important;
    padding: 0 17px !important;
    border-radius: 11px !important;
    font-size: 13px !important;
    font-weight: 750 !important;
    letter-spacing: 0.01em !important;
    transition:
      transform 150ms ease,
      box-shadow 150ms ease,
      border-color 150ms ease,
      background 150ms ease !important;
    cursor: pointer !important;
    white-space: nowrap !important;
  }

  .sipucol-project-action:hover {
    transform: translateY(-1px) !important;
  }

  .sipucol-project-action:active {
    transform: translateY(0) scale(0.985) !important;
  }

  .sipucol-action-save {
    border:
      1px solid rgba(105, 158, 255, 0.65) !important;
    background:
      linear-gradient(
        180deg,
        rgba(54, 112, 230, 0.98),
        rgba(35, 78, 177, 0.98)
      ) !important;
    color: white !important;
    box-shadow:
      0 7px 22px
      rgba(40, 91, 205, 0.27) !important;
  }

  .sipucol-action-save:hover {
    border-color:
      rgba(150, 190, 255, 0.95) !important;
    box-shadow:
      0 10px 27px
      rgba(46, 100, 225, 0.37) !important;
  }

  .sipucol-action-load {
    border:
      1px solid rgba(108, 141, 202, 0.38) !important;
    background:
      linear-gradient(
        180deg,
        rgba(29, 45, 76, 0.98),
        rgba(21, 34, 59, 0.98)
      ) !important;
    color: #dbe7ff !important;
    box-shadow:
      0 6px 18px
      rgba(0, 0, 0, 0.2) !important;
  }

  .sipucol-action-load:hover {
    border-color:
      rgba(112, 161, 255, 0.68) !important;
    background:
      linear-gradient(
        180deg,
        rgba(37, 57, 94, 0.98),
        rgba(27, 42, 72, 0.98)
      ) !important;
  }

  .sipucol-action-excel {
    border:
      1px solid rgba(81, 180, 145, 0.44) !important;
    background:
      linear-gradient(
        180deg,
        rgba(25, 107, 82, 0.97),
        rgba(18, 77, 61, 0.97)
      ) !important;
    color: #effff9 !important;
    box-shadow:
      0 7px 20px
      rgba(22, 111, 82, 0.22) !important;
  }

  .sipucol-action-excel:hover {
    border-color:
      rgba(126, 223, 187, 0.7) !important;
    box-shadow:
      0 9px 25px
      rgba(22, 122, 89, 0.31) !important;
  }

  .sipucol-action-new {
    border:
      1px solid rgba(126, 145, 181, 0.3) !important;
    background:
      rgba(33, 44, 66, 0.82) !important;
    color: #cfd9ed !important;
  }

  .sipucol-action-new:hover {
    border-color:
      rgba(126, 164, 235, 0.52) !important;
    color: white !important;
  }

  .sipucol-project-action:disabled {
    opacity: 0.55 !important;
    cursor: not-allowed !important;
    transform: none !important;
    box-shadow: none !important;
  }
`

document.head.appendChild(style)


function normalizarTexto(texto) {
  return String(texto || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(
      /[\u0300-\u036f]/g,
      ""
    )
}


function aplicarClase(elemento) {
  if (
    !(elemento instanceof HTMLElement)
  ) {
    return
  }

  const texto = normalizarTexto(
    elemento.textContent
  )

  let clase = null

  if (
    texto.includes("guardar proyecto")
    || texto === "guardar"
  ) {
    clase = "sipucol-action-save"
  } else if (
    texto.includes("cargar proyecto")
    || texto.includes("abrir proyecto")
    || texto === "cargar"
  ) {
    clase = "sipucol-action-load"
  } else if (
    texto.includes("guardar excel")
    || texto.includes("exportar excel")
    || texto.includes("generar excel")
  ) {
    clase = "sipucol-action-excel"
  } else if (
    texto.includes("nuevo proyecto")
    || texto.includes("proyecto nuevo")
  ) {
    clase = "sipucol-action-new"
  }

  if (!clase) {
    return
  }

  elemento.classList.add(
    "sipucol-project-action",
    clase
  )
}


function revisarControles() {
  const elementos = document.querySelectorAll(
    "button, [role='button'], label"
  )

  for (const elemento of elementos) {
    aplicarClase(elemento)
  }
}


const observer = new MutationObserver(
  revisarControles
)

observer.observe(
  document.documentElement,
  {
    childList: true,
    subtree: true
  }
)

if (
  document.readyState === "loading"
) {
  document.addEventListener(
    "DOMContentLoaded",
    revisarControles,
    {
      once: true
    }
  )
} else {
  revisarControles()
}
