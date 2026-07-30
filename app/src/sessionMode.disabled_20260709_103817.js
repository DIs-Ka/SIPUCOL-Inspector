
const MODE_KEY = "sipucol-start-mode"
const SESSION_CLEAN_KEY = "sipucol-clean-start-applied"

const VALID_MODES = new Set([
  "remember",
  "clean"
])

function getMode() {
  const mode = localStorage.getItem(MODE_KEY)

  if (VALID_MODES.has(mode)) {
    return mode
  }

  localStorage.setItem(
    MODE_KEY,
    "remember"
  )

  return "remember"
}


function getThemeEntries() {
  const entries = []

  for (
    let index = 0;
    index < localStorage.length;
    index += 1
  ) {
    const key = localStorage.key(index)

    if (!key) {
      continue
    }

    const normalized = key.toLowerCase()

    if (
      normalized.includes("theme")
      || normalized.includes("appearance")
      || normalized.includes("color-mode")
    ) {
      entries.push([
        key,
        localStorage.getItem(key)
      ])
    }
  }

  return entries
}


function restoreThemeEntries(entries) {
  for (
    const [key, value]
    of entries
  ) {
    if (value !== null) {
      localStorage.setItem(
        key,
        value
      )
    }
  }
}


function clearPersistentAppData({
  keepMode = true,
  keepTheme = true
} = {}) {
  const currentMode = getMode()

  const themeEntries = (
    keepTheme
      ? getThemeEntries()
      : []
  )

  localStorage.clear()
  sessionStorage.clear()

  if (keepMode) {
    localStorage.setItem(
      MODE_KEY,
      currentMode
    )
  }

  if (keepTheme) {
    restoreThemeEntries(
      themeEntries
    )
  }

  return currentMode
}


/*
Siempre iniciar limpio:
- Limpia al abrir una NUEVA sesión de pestaña.
- sessionStorage evita que F5 o Vite borren el trabajo
  repetidamente dentro de la misma sesión.
*/
function applyStartupMode() {
  const mode = getMode()

  if (
    mode !== "clean"
    || sessionStorage.getItem(
      SESSION_CLEAN_KEY
    ) === "1"
  ) {
    return
  }

  const themeEntries = getThemeEntries()

  localStorage.clear()
  sessionStorage.clear()

  localStorage.setItem(
    MODE_KEY,
    "clean"
  )

  restoreThemeEntries(
    themeEntries
  )

  sessionStorage.setItem(
    SESSION_CLEAN_KEY,
    "1"
  )
}


applyStartupMode()


function createSessionControl() {
  if (
    document.getElementById(
      "sipucol-session-control"
    )
  ) {
    return
  }

  const style = document.createElement(
    "style"
  )

  style.textContent = `
    #sipucol-session-control {
      position: fixed;
      right: 18px;
      bottom: 18px;
      z-index: 999999;
      font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
    }

    #sipucol-session-control * {
      box-sizing: border-box;
    }

    .sipucol-session-pill {
      min-height: 42px;
      padding: 0 15px;
      border: 1px solid
        rgba(106, 154, 255, 0.36);
      border-radius: 13px;
      background:
        rgba(14, 25, 48, 0.96);
      color: #dce8ff;
      box-shadow:
        0 12px 34px
        rgba(0, 0, 0, 0.34);
      cursor: pointer;
      font-size: 13px;
      font-weight: 700;
      backdrop-filter: blur(16px);
    }

    .sipucol-session-pill:hover {
      border-color:
        rgba(115, 168, 255, 0.72);
      transform:
        translateY(-1px);
    }

    .sipucol-session-panel {
      width: min(
        370px,
        calc(100vw - 32px)
      );
      padding: 17px;
      border: 1px solid
        rgba(111, 157, 255, 0.34);
      border-radius: 17px;
      background:
        rgba(12, 22, 42, 0.985);
      color: #e8efff;
      box-shadow:
        0 22px 60px
        rgba(0, 0, 0, 0.48);
      backdrop-filter: blur(20px);
    }

    .sipucol-session-hidden {
      display: none;
    }

    .sipucol-session-head {
      display: flex;
      align-items: flex-start;
      justify-content:
        space-between;
      gap: 14px;
      margin-bottom: 14px;
    }

    .sipucol-session-title {
      margin: 0;
      color: #f6f9ff;
      font-size: 15px;
      font-weight: 800;
    }

    .sipucol-session-subtitle {
      margin: 5px 0 0;
      color: #91a4c9;
      font-size: 12px;
      line-height: 1.45;
    }

    .sipucol-session-close {
      width: 31px;
      height: 31px;
      border: 1px solid
        rgba(255, 255, 255, 0.1);
      border-radius: 9px;
      background:
        rgba(255, 255, 255, 0.04);
      color: #b9c7e4;
      cursor: pointer;
      font-size: 18px;
      line-height: 1;
    }

    .sipucol-session-close:hover {
      color: white;
      background:
        rgba(255, 255, 255, 0.09);
    }

    .sipucol-session-options {
      display: grid;
      grid-template-columns:
        repeat(2, minmax(0, 1fr));
      gap: 8px;
      padding: 5px;
      border-radius: 13px;
      background:
        rgba(255, 255, 255, 0.045);
    }

    .sipucol-session-mode {
      min-height: 44px;
      padding: 8px 10px;
      border: 1px solid transparent;
      border-radius: 10px;
      background: transparent;
      color: #91a4c9;
      cursor: pointer;
      font-size: 12px;
      font-weight: 750;
    }

    .sipucol-session-mode:hover {
      color: #dbe7ff;
      background:
        rgba(89, 132, 221, 0.12);
    }

    .sipucol-session-mode.active {
      border-color:
        rgba(89, 143, 255, 0.56);
      background:
        linear-gradient(
          180deg,
          rgba(62, 121, 243, 0.34),
          rgba(45, 91, 190, 0.25)
        );
      color: #eef4ff;
      box-shadow:
        inset 0 0 0 1px
        rgba(255, 255, 255, 0.035);
    }

    .sipucol-session-description {
      min-height: 57px;
      margin: 11px 2px 13px;
      padding: 11px 12px;
      border: 1px solid
        rgba(126, 158, 217, 0.14);
      border-radius: 11px;
      background:
        rgba(74, 106, 167, 0.08);
      color: #aebddd;
      font-size: 12px;
      line-height: 1.5;
    }

    .sipucol-session-clear {
      width: 100%;
      min-height: 43px;
      border: 1px solid
        rgba(255, 111, 132, 0.42);
      border-radius: 11px;
      background:
        rgba(153, 40, 61, 0.16);
      color: #ffbac5;
      cursor: pointer;
      font-size: 12px;
      font-weight: 800;
    }

    .sipucol-session-clear:hover {
      border-color:
        rgba(255, 119, 139, 0.74);
      background:
        rgba(177, 48, 72, 0.25);
      color: #ffe4e8;
    }

    .sipucol-session-note {
      margin: 10px 2px 0;
      color: #7185aa;
      font-size: 10.5px;
      line-height: 1.45;
    }

    @media (
      max-width: 650px
    ) {
      #sipucol-session-control {
        right: 10px;
        bottom: 10px;
      }

      .sipucol-session-panel {
        width:
          calc(100vw - 20px);
      }
    }
  `

  document.head.appendChild(
    style
  )

  const root = document.createElement(
    "div"
  )

  root.id =
    "sipucol-session-control"

  root.innerHTML = `
    <button
      type="button"
      class="sipucol-session-pill"
      id="sipucol-session-pill"
    >
      Inicio: recordar datos
    </button>

    <section
      class="
        sipucol-session-panel
        sipucol-session-hidden
      "
      id="sipucol-session-panel"
      aria-label="
        Preferencias de inicio
      "
    >
      <header
        class="sipucol-session-head"
      >
        <div>
          <h3
            class="
              sipucol-session-title
            "
          >
            Datos al iniciar
          </h3>

          <p
            class="
              sipucol-session-subtitle
            "
          >
            Decide si SIPUCOL conserva
            el trabajo anterior o abre
            vacío.
          </p>
        </div>

        <button
          type="button"
          class="
            sipucol-session-close
          "
          id="sipucol-session-close"
          aria-label="Cerrar"
        >
          ×
        </button>
      </header>

      <div
        class="
          sipucol-session-options
        "
      >
        <button
          type="button"
          class="
            sipucol-session-mode
          "
          data-mode="remember"
        >
          Recordar datos
        </button>

        <button
          type="button"
          class="
            sipucol-session-mode
          "
          data-mode="clean"
        >
          Iniciar limpio
        </button>
      </div>

      <div
        class="
          sipucol-session-description
        "
        id="
          sipucol-session-description
        "
      ></div>

      <button
        type="button"
        class="
          sipucol-session-clear
        "
        id="sipucol-clear-all"
      >
        Borrar todo y empezar vacío
      </button>

      <p
        class="
          sipucol-session-note
        "
      >
        Esta acción limpia los datos
        guardados de la app. No modifica
        archivos Excel ni proyectos JSON
        ya guardados en el computador.
      </p>
    </section>
  `

  document.body.appendChild(
    root
  )

  const pill =
    root.querySelector(
      "#sipucol-session-pill"
    )

  const panel =
    root.querySelector(
      "#sipucol-session-panel"
    )

  const closeButton =
    root.querySelector(
      "#sipucol-session-close"
    )

  const clearButton =
    root.querySelector(
      "#sipucol-clear-all"
    )

  const description =
    root.querySelector(
      "#sipucol-session-description"
    )

  const modeButtons = [
    ...root.querySelectorAll(
      "[data-mode]"
    )
  ]

  function updateUi() {
    const mode = getMode()

    for (
      const button
      of modeButtons
    ) {
      button.classList.toggle(
        "active",
        button.dataset.mode === mode
      )
    }

    if (
      mode === "clean"
    ) {
      pill.textContent =
        "Inicio: siempre limpio"

      description.textContent =
        "La próxima vez que abras "
        + "SIPUCOL en una sesión nueva, "
        + "la interfaz comenzará vacía. "
        + "El trabajo actual no se borra "
        + "al cambiar esta opción."
    } else {
      pill.textContent =
        "Inicio: recordar datos"

      description.textContent =
        "SIPUCOL conserva automáticamente "
        + "lo escrito y lo recupera cuando "
        + "vuelves a abrir la app."
    }
  }

  pill.addEventListener(
    "click",
    () => {
      panel.classList.toggle(
        "sipucol-session-hidden"
      )
    }
  )

  closeButton.addEventListener(
    "click",
    () => {
      panel.classList.add(
        "sipucol-session-hidden"
      )
    }
  )

  for (
    const button
    of modeButtons
  ) {
    button.addEventListener(
      "click",
      () => {
        const newMode =
          button.dataset.mode

        localStorage.setItem(
          MODE_KEY,
          newMode
        )

        /*
        Al activar clean no borramos
        lo actual. Se aplicará al
        próximo inicio real.
        */
        sessionStorage.setItem(
          SESSION_CLEAN_KEY,
          "1"
        )

        updateUi()
      }
    )
  }

  clearButton.addEventListener(
    "click",
    () => {
      const accepted = window.confirm(
        "Se borrará todo lo escrito "
        + "y la app volverá a iniciar "
        + "vacía.\n\n"
        + "Los Excel y proyectos JSON "
        + "guardados en el computador "
        + "no se eliminarán."
      )

      if (!accepted) {
        return
      }

      const mode =
        clearPersistentAppData({
          keepMode: true,
          keepTheme: true
        })

      if (
        mode === "clean"
      ) {
        sessionStorage.setItem(
          SESSION_CLEAN_KEY,
          "1"
        )
      }

      window.location.reload()
    }
  )

  updateUi()
}


if (
  document.readyState
  === "loading"
) {
  document.addEventListener(
    "DOMContentLoaded",
    createSessionControl,
    {
      once: true
    }
  )
} else {
  createSessionControl()
}
