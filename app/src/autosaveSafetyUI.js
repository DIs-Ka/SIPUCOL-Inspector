
/*
==========================================================
SIPUCOL — AUTOGUARDADO + LIMPIAR TODO
==========================================================

Este módulo NO cambia los estados de React.

La aplicación conserva su guardado automático original.
Este módulo únicamente:

1. Muestra que el autoguardado está activo.
2. Añade "Limpiar todo".
3. Mejora visualmente Guardar, Cargar y Excel.
4. Nunca limpia datos automáticamente al iniciar.
*/

const detectedPersistenceKeys =
[
  "sipucol-autosave-v3"
]


function normalizeText(value) {

  return String(
    value || ""
  )
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(
      /[\u0300-\u036f]/g,
      ""
    )
}


function installStyles() {

  if (
    document.getElementById(
      "sipucol-autosave-styles"
    )
  ) {
    return
  }

  const style =
    document.createElement(
      "style"
    )

  style.id =
    "sipucol-autosave-styles"

  style.textContent = `

    /*
    ==============================================
    BOTONES PRINCIPALES
    ==============================================
    */

    .sipucol-action-button {

      min-height: 42px !important;

      padding:
        0 16px !important;

      border-radius:
        11px !important;

      font-size:
        12.5px !important;

      font-weight:
        760 !important;

      letter-spacing:
        0.01em !important;

      transition:
        transform 150ms ease,
        border-color 150ms ease,
        background 150ms ease,
        box-shadow 150ms ease
        !important;

      cursor:
        pointer !important;

      white-space:
        nowrap !important;
    }


    .sipucol-action-button:hover {

      transform:
        translateY(-1px) !important;
    }


    .sipucol-action-button:active {

      transform:
        translateY(0)
        scale(0.985)
        !important;
    }


    /*
    GUARDAR PROYECTO
    */

    .sipucol-save-project {

      border:
        1px solid
        rgba(
          105,
          160,
          255,
          0.68
        )
        !important;

      background:
        linear-gradient(
          180deg,
          #3678e8,
          #2455b9
        )
        !important;

      color:
        #ffffff
        !important;

      box-shadow:
        0 8px 22px
        rgba(
          35,
          91,
          210,
          0.28
        )
        !important;
    }


    .sipucol-save-project:hover {

      border-color:
        rgba(
          160,
          198,
          255,
          0.95
        )
        !important;

      box-shadow:
        0 11px 28px
        rgba(
          45,
          105,
          235,
          0.38
        )
        !important;
    }


    /*
    CARGAR PROYECTO
    */

    .sipucol-load-project {

      border:
        1px solid
        rgba(
          113,
          154,
          236,
          0.46
        )
        !important;

      background:
        linear-gradient(
          180deg,
          #263b66,
          #1b2a49
        )
        !important;

      color:
        #e2ebff
        !important;

      box-shadow:
        0 7px 18px
        rgba(
          0,
          0,
          0,
          0.22
        )
        !important;
    }


    .sipucol-load-project:hover {

      border-color:
        rgba(
          126,
          174,
          255,
          0.76
        )
        !important;

      background:
        linear-gradient(
          180deg,
          #304a7d,
          #21365d
        )
        !important;
    }


    /*
    EXCEL
    */

    .sipucol-excel-action {

      border:
        1px solid
        rgba(
          82,
          205,
          164,
          0.54
        )
        !important;

      background:
        linear-gradient(
          180deg,
          #198661,
          #116044
        )
        !important;

      color:
        #effff9
        !important;

      box-shadow:
        0 8px 22px
        rgba(
          24,
          131,
          91,
          0.25
        )
        !important;
    }


    .sipucol-excel-action:hover {

      border-color:
        rgba(
          125,
          237,
          196,
          0.88
        )
        !important;

      box-shadow:
        0 11px 27px
        rgba(
          30,
          151,
          105,
          0.34
        )
        !important;
    }


    /*
    NUEVO
    */

    .sipucol-new-project {

      border:
        1px solid
        rgba(
          136,
          157,
          197,
          0.34
        )
        !important;

      background:
        rgba(
          34,
          48,
          74,
          0.9
        )
        !important;

      color:
        #d0dcf3
        !important;
    }


    .sipucol-new-project:hover {

      border-color:
        rgba(
          130,
          170,
          245,
          0.62
        )
        !important;

      color:
        white
        !important;
    }


    /*
    DESACTIVADO
    */

    .sipucol-action-button:disabled {

      opacity:
        0.5 !important;

      cursor:
        not-allowed !important;

      transform:
        none !important;

      box-shadow:
        none !important;
    }


    /*
    ==============================================
    ESTADO DE AUTOGUARDADO
    ==============================================
    */

    #sipucol-autosave-tools {

      position:
        fixed;

      right:
        17px;

      bottom:
        17px;

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
          102,
          145,
          225,
          0.3
        );

      border-radius:
        14px;

      background:
        rgba(
          12,
          23,
          44,
          0.97
        );

      box-shadow:
        0 16px 40px
        rgba(
          0,
          0,
          0,
          0.42
        );

      backdrop-filter:
        blur(17px);

      font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        sans-serif;
    }


    .sipucol-autosave-status {

      display:
        flex;

      align-items:
        center;

      gap:
        8px;

      padding:
        0 10px;

      color:
        #c8d7f4;

      font-size:
        11px;

      font-weight:
        700;

      white-space:
        nowrap;
    }


    .sipucol-autosave-dot {

      width:
        8px;

      height:
        8px;

      border-radius:
        999px;

      background:
        #55d59b;

      box-shadow:
        0 0 0 4px
        rgba(
          85,
          213,
          155,
          0.1
        );
    }


    .sipucol-clear-button {

      min-height:
        34px;

      padding:
        0 12px;

      border:
        1px solid
        rgba(
          255,
          113,
          134,
          0.38
        );

      border-radius:
        9px;

      background:
        rgba(
          145,
          43,
          61,
          0.16
        );

      color:
        #ffb8c4;

      cursor:
        pointer;

      font-size:
        11px;

      font-weight:
        780;

      transition:
        150ms ease;
    }


    .sipucol-clear-button:hover {

      border-color:
        rgba(
          255,
          128,
          147,
          0.78
        );

      background:
        rgba(
          173,
          47,
          70,
          0.3
        );

      color:
        #ffe3e8;
    }


    /*
    ==============================================
    MODAL
    ==============================================
    */

    .sipucol-clear-overlay {

      position:
        fixed;

      inset:
        0;

      z-index:
        1000000;

      display:
        grid;

      place-items:
        center;

      padding:
        22px;

      background:
        rgba(
          4,
          9,
          19,
          0.7
        );

      backdrop-filter:
        blur(8px);
    }


    .sipucol-clear-modal {

      width:
        min(
          440px,
          calc(
            100vw
            - 34px
          )
        );

      padding:
        22px;

      border:
        1px solid
        rgba(
          111,
          153,
          234,
          0.3
        );

      border-radius:
        18px;

      background:
        linear-gradient(
          180deg,
          #111f3a,
          #0c172c
        );

      box-shadow:
        0 28px 80px
        rgba(
          0,
          0,
          0,
          0.58
        );

      color:
        #e8efff;
    }


    .sipucol-clear-modal h3 {

      margin:
        0 0 8px;

      font-size:
        18px;

      font-weight:
        820;
    }


    .sipucol-clear-modal p {

      margin:
        0;

      color:
        #9fb0d2;

      font-size:
        13px;

      line-height:
        1.55;
    }


    .sipucol-clear-warning {

      margin-top:
        15px;

      padding:
        12px;

      border:
        1px solid
        rgba(
          255,
          121,
          142,
          0.22
        );

      border-radius:
        11px;

      background:
        rgba(
          150,
          43,
          62,
          0.11
        );

      color:
        #d9b5bd;

      font-size:
        12px;

      line-height:
        1.5;
    }


    .sipucol-clear-actions {

      display:
        flex;

      justify-content:
        flex-end;

      gap:
        9px;

      margin-top:
        20px;
    }


    .sipucol-modal-cancel,
    .sipucol-modal-confirm {

      min-height:
        39px;

      padding:
        0 15px;

      border-radius:
        10px;

      cursor:
        pointer;

      font-size:
        12px;

      font-weight:
        780;
    }


    .sipucol-modal-cancel {

      border:
        1px solid
        rgba(
          133,
          158,
          205,
          0.28
        );

      background:
        rgba(
          54,
          72,
          105,
          0.38
        );

      color:
        #d5e0f5;
    }


    .sipucol-modal-confirm {

      border:
        1px solid
        rgba(
          255,
          123,
          143,
          0.58
        );

      background:
        linear-gradient(
          180deg,
          #ae3850,
          #7d273a
        );

      color:
        white;
    }


    @media (
      max-width:
      620px
    ) {

      #sipucol-autosave-tools {

        right:
          9px;

        bottom:
          9px;
      }


      .sipucol-autosave-status {

        display:
          none;
      }
    }
  `

  document.head.appendChild(
    style
  )
}


function classifyActionButton(
  element
) {

  if (
    !(
      element
      instanceof HTMLElement
    )
  ) {
    return
  }

  const text =
    normalizeText(
      element.textContent
    )

  let className =
    null

  if (
    text.includes(
      "guardar proyecto"
    )
  ) {

    className =
      "sipucol-save-project"

  } else if (

    text.includes(
      "cargar proyecto"
    )

    || text.includes(
      "abrir proyecto"
    )

  ) {

    className =
      "sipucol-load-project"

  } else if (

    text.includes(
      "guardar excel"
    )

    || text.includes(
      "exportar excel"
    )

    || text.includes(
      "generar excel"
    )

  ) {

    className =
      "sipucol-excel-action"

  } else if (

    text.includes(
      "nuevo proyecto"
    )

  ) {

    className =
      "sipucol-new-project"
  }

  if (!className) {
    return
  }

  element.classList.add(
    "sipucol-action-button",
    className
  )
}


function polishExistingButtons() {

  const elements =
    document.querySelectorAll(
      `
      button,
      [role="button"]
      `
    )

  for (
    const element
    of elements
  ) {

    classifyActionButton(
      element
    )
  }
}


function preserveThemeValues() {

  const preserved = []

  for (
    let index = 0;
    index < localStorage.length;
    index += 1
  ) {

    const key =
      localStorage.key(
        index
      )

    if (!key) {
      continue
    }

    const normalized =
      normalizeText(
        key
      )

    if (

      normalized.includes(
        "theme"
      )

      || normalized.includes(
        "appearance"
      )

      || normalized.includes(
        "color-mode"
      )

    ) {

      preserved.push([
        key,
        localStorage.getItem(
          key
        )
      ])
    }
  }

  return preserved
}


function clearApplicationData() {

  const themeValues =
    preserveThemeValues()

  /*
  El origen localhost pertenece a
  SIPUCOL, por lo que se limpian
  todos los datos persistidos de
  la aplicación.

  Los Excel y JSON guardados en
  Windows NO se tocan.
  */

  localStorage.clear()

  sessionStorage.clear()

  for (
    const [
      key,
      value
    ]
    of themeValues
  ) {

    if (
      value
      !== null
    ) {

      localStorage.setItem(
        key,
        value
      )
    }
  }

  location.reload()
}


function openClearModal() {

  if (
    document.getElementById(
      "sipucol-clear-overlay"
    )
  ) {
    return
  }

  const overlay =
    document.createElement(
      "div"
    )

  overlay.id =
    "sipucol-clear-overlay"

  overlay.className =
    "sipucol-clear-overlay"

  overlay.innerHTML = `

    <section
      class="
        sipucol-clear-modal
      "
    >

      <h3>
        Limpiar todos los datos
      </h3>

      <p>
        La interfaz volverá al estado
        inicial vacío. Se eliminará
        únicamente el autoguardado
        local de esta aplicación.
      </p>

      <div
        class="
          sipucol-clear-warning
        "
      >
        Los archivos Excel y los
        proyectos .sipucol.json que
        ya guardaste en Windows no
        serán eliminados.
      </div>

      <div
        class="
          sipucol-clear-actions
        "
      >

        <button
          type="button"
          class="
            sipucol-modal-cancel
          "
        >
          Cancelar
        </button>

        <button
          type="button"
          class="
            sipucol-modal-confirm
          "
        >
          Limpiar y empezar vacío
        </button>

      </div>

    </section>
  `

  document.body.appendChild(
    overlay
  )

  overlay
    .querySelector(
      ".sipucol-modal-cancel"
    )
    .addEventListener(
      "click",
      () => {
        overlay.remove()
      }
    )

  overlay
    .querySelector(
      ".sipucol-modal-confirm"
    )
    .addEventListener(
      "click",
      clearApplicationData
    )

  overlay.addEventListener(
    "click",
    event => {

      if (
        event.target
        === overlay
      ) {

        overlay.remove()
      }
    }
  )
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
        sipucol-autosave-status
      "
      title="
        La información escrita se
        conserva localmente en este
        navegador.
      "
    >

      <span
        class="
          sipucol-autosave-dot
        "
      ></span>

      <span>
        Guardado automático activo
      </span>

    </div>

    <button
      type="button"
      class="
        sipucol-clear-button
      "
    >
      Limpiar todo
    </button>
  `

  root
    .querySelector(
      ".sipucol-clear-button"
    )
    .addEventListener(
      "click",
      openClearModal
    )

  document.body.appendChild(
    root
  )
}


function startUi() {

  installStyles()

  polishExistingButtons()

  installAutosaveTools()

  const observer =
    new MutationObserver(
      polishExistingButtons
    )

  observer.observe(
    document.body,
    {
      childList: true,
      subtree: true
    }
  )

  console.info(
    "[SIPUCOL] Guardado automático conservado."
  )

  console.info(
    "[SIPUCOL] Claves detectadas:",
    detectedPersistenceKeys
  )
}


if (
  document.readyState
  === "loading"
) {

  document.addEventListener(
    "DOMContentLoaded",
    startUi,
    {
      once: true
    }
  )

} else {

  startUi()
}

/* === SIPUCOL_FINAL_GREEN_UI_START === */

;(() => {

  const STYLE_ID =
    "sipucol-final-green-ui-style"


  function normalizeText(
    value
  ) {

    return String(
      value || ""
    )
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(
        /[\u0300-\u036f]/g,
        ""
      )
  }


  /*
  ========================================================
  ESTILOS
  ========================================================
  */

  function installFinalStyles() {

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

      /*
      BOTONES PRINCIPALES
      */

      .sipucol-final-action {

        min-height:
          42px !important;

        padding:
          0 17px !important;

        border-radius:
          11px !important;

        color:
          #f3fff9 !important;

        font-size:
          12.5px !important;

        font-weight:
          760 !important;

        letter-spacing:
          0.01em !important;

        transition:
          transform 150ms ease,
          border-color 150ms ease,
          background 150ms ease,
          box-shadow 150ms ease
          !important;

        cursor:
          pointer !important;

        white-space:
          nowrap !important;
      }


      .sipucol-final-action:hover {

        transform:
          translateY(-1px)
          !important;
      }


      .sipucol-final-action:active {

        transform:
          translateY(0)
          scale(0.985)
          !important;
      }


      /*
      GUARDAR PROYECTO
      Verde más luminoso
      */

      .sipucol-final-save {

        border:
          1px solid
          rgba(
            93,
            232,
            178,
            0.64
          )
          !important;

        background:
          linear-gradient(
            180deg,
            #1fa879,
            #137556
          )
          !important;

        box-shadow:
          0 8px 22px
          rgba(
            23,
            145,
            100,
            0.25
          )
          !important;
      }


      .sipucol-final-save:hover {

        border-color:
          rgba(
            128,
            255,
            204,
            0.88
          )
          !important;

        background:
          linear-gradient(
            180deg,
            #28bb89,
            #17805e
          )
          !important;

        box-shadow:
          0 11px 27px
          rgba(
            23,
            160,
            111,
            0.34
          )
          !important;
      }


      /*
      CARGAR PROYECTO
      Verde azulado oscuro
      */

      .sipucol-final-load {

        border:
          1px solid
          rgba(
            77,
            204,
            166,
            0.5
          )
          !important;

        background:
          linear-gradient(
            180deg,
            #19765d,
            #10503f
          )
          !important;

        box-shadow:
          0 8px 20px
          rgba(
            12,
            102,
            76,
            0.23
          )
          !important;
      }


      .sipucol-final-load:hover {

        border-color:
          rgba(
            107,
            235,
            194,
            0.78
          )
          !important;

        background:
          linear-gradient(
            180deg,
            #20886b,
            #145c49
          )
          !important;
      }


      /*
      GUARDAR EXCEL
      Verde medio
      */

      .sipucol-final-excel {

        border:
          1px solid
          rgba(
            78,
            214,
            161,
            0.55
          )
          !important;

        background:
          linear-gradient(
            180deg,
            #188a61,
            #105f44
          )
          !important;

        box-shadow:
          0 8px 21px
          rgba(
            19,
            125,
            85,
            0.24
          )
          !important;
      }


      .sipucol-final-excel:hover {

        border-color:
          rgba(
            118,
            241,
            190,
            0.85
          )
          !important;

        background:
          linear-gradient(
            180deg,
            #1e9b6d,
            #126b4b
          )
          !important;
      }


      /*
      GUARDAR PDF
      Mantiene el concepto original,
      apenas diferente al Excel
      */

      .sipucol-final-pdf {

        border:
          1px solid
          rgba(
            55,
            225,
            171,
            0.62
          )
          !important;

        background:
          linear-gradient(
            180deg,
            #119d70,
            #08724f
          )
          !important;

        box-shadow:
          0 8px 22px
          rgba(
            10,
            137,
            93,
            0.25
          )
          !important;
      }


      .sipucol-final-pdf:hover {

        border-color:
          rgba(
            116,
            255,
            209,
            0.9
          )
          !important;

        background:
          linear-gradient(
            180deg,
            #17ae7d,
            #0b8059
          )
          !important;
      }


      /*
      INPUTS NATIVOS
      */

      .sipucol-native-control {

        color-scheme:
          dark !important;

        border:
          1px solid
          rgba(
            20,
            210,
            145,
            0.46
          )
          !important;

        background:
          linear-gradient(
            180deg,
            rgba(
              5,
              18,
              35,
              0.98
            ),
            rgba(
              4,
              13,
              28,
              0.98
            )
          )
          !important;

        color:
          #e9fff6
          !important;

        transition:
          border-color 140ms ease,
          box-shadow 140ms ease,
          background 140ms ease
          !important;
      }


      .sipucol-native-control:hover {

        border-color:
          rgba(
            34,
            230,
            162,
            0.72
          )
          !important;
      }


      .sipucol-native-control:focus {

        outline:
          none !important;

        border-color:
          rgba(
            70,
            247,
            180,
            0.94
          )
          !important;

        box-shadow:
          0 0 0 3px
          rgba(
            27,
            210,
            143,
            0.13
          )
          !important;
      }


      /*
      ICONOS NATIVOS FECHA/HORA
      */

      .sipucol-native-control
      ::-webkit-calendar-picker-indicator {

        cursor:
          pointer;

        opacity:
          0.88;

        filter:
          invert(88%)
          sepia(24%)
          saturate(653%)
          hue-rotate(93deg)
          brightness(104%);
      }


      input.sipucol-native-control
      [type="date"],

      input.sipucol-native-control
      [type="time"] {

        cursor:
          pointer !important;
      }


      /*
      SPINNER NUMÉRICO
      */

      input[type="number"]
      .sipucol-native-control {

        font-variant-numeric:
          tabular-nums;
      }


      /*
      NO CAMBIAR BOTONES DESACTIVADOS
      */

      .sipucol-final-action:disabled {

        opacity:
          0.5 !important;

        cursor:
          not-allowed !important;

        transform:
          none !important;

        box-shadow:
          none !important;
      }
    `

    document.head.appendChild(
      style
    )
  }


  /*
  ========================================================
  BOTONES
  ========================================================
  */

  function styleMainButtons() {

    const buttons =
      document.querySelectorAll(
        `
        button,
        [role="button"]
        `
      )

    for (
      const button
      of buttons
    ) {

      const text =
        normalizeText(
          button.textContent
        )


      let finalClass =
        null


      if (
        text.includes(
          "guardar proyecto"
        )
      ) {

        finalClass =
          "sipucol-final-save"

      } else if (

        text.includes(
          "cargar proyecto"
        )

        || text.includes(
          "abrir proyecto"
        )

      ) {

        finalClass =
          "sipucol-final-load"

      } else if (

        text.includes(
          "guardar excel"
        )

        || text.includes(
          "exportar excel"
        )

      ) {

        finalClass =
          "sipucol-final-excel"

      } else if (

        text.includes(
          "guardar pdf"
        )

        || text.includes(
          "exportar pdf"
        )

      ) {

        finalClass =
          "sipucol-final-pdf"
      }


      if (!finalClass) {
        continue
      }


      button.classList.add(
        "sipucol-final-action",
        finalClass
      )
    }
  }


  /*
  ========================================================
  SELECTORES ID / FECHA / HORA
  ========================================================
  */

  function getInputFromLabel(
    label
  ) {

    if (
      label.htmlFor
    ) {

      const target =
        document.getElementById(
          label.htmlFor
        )

      if (
        target
        instanceof HTMLInputElement
      ) {

        return target
      }
    }


    const inside =
      label.querySelector(
        "input"
      )

    if (
      inside
      instanceof HTMLInputElement
    ) {

      return inside
    }


    const parent =
      label.parentElement


    if (parent) {

      const input =
        parent.querySelector(
          "input"
        )

      if (
        input
        instanceof HTMLInputElement
      ) {

        return input
      }
    }


    return null
  }


  
function configureNumberInput(input) {
  // Neutralizado: el control final del ID se aplica
  // únicamente al campo real ID Puente.
  return
}



  function configureDateInput(
    input
  ) {

    if (
      !input
    ) {
      return
    }


    if (
      input.type
      !== "date"
    ) {

      input.type =
        "date"
    }


    input.classList.add(
      "sipucol-native-control"
    )
  }


  function configureTimeInput(
    input
  ) {

    if (
      !input
    ) {
      return
    }


    if (
      input.type
      !== "time"
    ) {

      input.type =
        "time"
    }


    input.setAttribute(
      "step",
      "60"
    )

    input.classList.add(
      "sipucol-native-control"
    )
  }


  function configureByLabels() {

    const labels =
      document.querySelectorAll(
        "label"
      )


    for (
      const label
      of labels
    ) {

      const text =
        normalizeText(
          label.textContent
        )


      const input =
        getInputFromLabel(
          label
        )


      if (!input) {
        continue
      }


      if (
        text === "id puente"
        || text.includes(
          "id puente"
        )
      ) {

        configureNumberInput(
          input
        )

      } else if (

        text.includes(
          "fecha de levantamiento"
        )

      ) {

        configureDateInput(
          input
        )

      } else if (

        text === "hora"

      ) {

        configureTimeInput(
          input
        )
      }
    }
  }


  /*
  Fallback por atributos,
  por si cambia la estructura.
  */

  function configureByAttributes() {

    const inputs =
      document.querySelectorAll(
        "input"
      )


    for (
      const input
      of inputs
    ) {

      const attributes =
        normalizeText(
          [
            input.name,
            input.id,
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
        attributes.includes(
          "idpuente"
        )

        || attributes.includes(
          "id puente"
        )
      ) {

        configureNumberInput(
          input
        )

      } else if (

        attributes.includes(
          "fecha"
        )

        && attributes.includes(
          "levantamiento"
        )

      ) {

        configureDateInput(
          input
        )

      } else if (

        attributes === "hora"

        || attributes.includes(
          " hora "
        )

      ) {

        configureTimeInput(
          input
        )
      }
    }
  }


  function applyEnhancements() {

    installFinalStyles()

    styleMainButtons()

    configureByLabels()

    configureByAttributes()
  }


  /*
  React puede volver a renderizar.
  El observer mantiene los estilos
  y los tipos correctos.
  */

  function start() {

    applyEnhancements()


    const observer =
      new MutationObserver(
        () => {

          applyEnhancements()
        }
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
          "type"
        ]
      }
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

})()

/* === SIPUCOL_FINAL_GREEN_UI_END === */

/* === SIPUCOL_FLAT_NEON_FINAL_START === */

;(() => {

  const STYLE_ID =
    "sipucol-flat-neon-final"


  function norm(
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


  function installFlatStyles() {

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

      /*
      ==========================================
      BOTONES PRINCIPALES:
      PLANOS + BORDE NEÓN
      ==========================================
      */

      .sipucol-final-action,
      .sipucol-action-button {

        background-image:
          none !important;

        border-radius:
          10px !important;

        min-height:
          42px !important;

        color:
          #edfff8 !important;

        text-shadow:
          none !important;

        transition:
          transform 150ms ease,
          border-color 150ms ease,
          background-color 150ms ease,
          box-shadow 150ms ease,
          filter 150ms ease
          !important;
      }


      /*
      GUARDAR PROYECTO
      */

      .sipucol-final-save,
      .sipucol-save-project {

        background:
          rgba(
            17,
            112,
            78,
            0.78
          )
          !important;

        border:
          1px solid
          rgba(
            55,
            238,
            171,
            0.82
          )
          !important;

        box-shadow:
          inset 0 0 0 1px
          rgba(
            105,
            255,
            202,
            0.035
          ),
          0 0 11px
          rgba(
            35,
            220,
            155,
            0.12
          )
          !important;
      }


      /*
      CARGAR PROYECTO
      */

      .sipucol-final-load,
      .sipucol-load-project {

        background:
          rgba(
            14,
            85,
            67,
            0.82
          )
          !important;

        border:
          1px solid
          rgba(
            43,
            205,
            157,
            0.72
          )
          !important;

        box-shadow:
          inset 0 0 0 1px
          rgba(
            104,
            241,
            197,
            0.025
          ),
          0 0 10px
          rgba(
            30,
            190,
            141,
            0.1
          )
          !important;
      }


      /*
      GUARDAR EXCEL
      */

      .sipucol-final-excel,
      .sipucol-excel-action {

        background:
          rgba(
            18,
            123,
            82,
            0.78
          )
          !important;

        border:
          1px solid
          rgba(
            65,
            232,
            164,
            0.78
          )
          !important;

        box-shadow:
          inset 0 0 0 1px
          rgba(
            118,
            255,
            205,
            0.03
          ),
          0 0 11px
          rgba(
            42,
            205,
            142,
            0.12
          )
          !important;
      }


      /*
      GUARDAR PDF
      */

      .sipucol-final-pdf {

        background:
          rgba(
            10,
            101,
            79,
            0.83
          )
          !important;

        border:
          1px solid
          rgba(
            42,
            223,
            170,
            0.8
          )
          !important;

        box-shadow:
          inset 0 0 0 1px
          rgba(
            108,
            255,
            211,
            0.03
          ),
          0 0 11px
          rgba(
            29,
            205,
            153,
            0.12
          )
          !important;
      }


      /*
      HOVER:
      mantiene la animación
      */

      .sipucol-final-action:hover,
      .sipucol-action-button:hover {

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
          0 0 0 1px
          rgba(
            94,
            255,
            205,
            0.16
          ),
          0 0 19px
          rgba(
            43,
            224,
            164,
            0.22
          )
          !important;
      }


      .sipucol-final-action:active,
      .sipucol-action-button:active {

        transform:
          translateY(
            0
          )
          scale(
            0.985
          )
          !important;
      }


      /*
      ==========================================
      ID PUENTE
      ==========================================
      */

      input[
        data-sipucol-bridge-id="true"
      ] {

        appearance:
          none !important;

        -webkit-appearance:
          none !important;

        font-variant-numeric:
          tabular-nums;

        letter-spacing:
          0.025em;
      }


      input[
        data-sipucol-bridge-id="true"
      ]::placeholder {

        color:
          rgba(
            122,
            164,
            151,
            0.58
          );

        font-size:
          12px;
      }


      /*
      ==========================================
      ENVÍO FOTO -> EVALUACIÓN
      ==========================================
      */

      [
        data-sipucol-hidden-photo-evaluation
      ] {

        display:
          none !important;
      }

    `


    document.head.appendChild(
      style
    )
  }


  function hidePhotoEvaluationSection() {

    const elements = [
      ...document.querySelectorAll(
        `
        div,
        section,
        header,
        span,
        p,
        strong
        `
      )
    ]


    for (
      const element
      of elements
    ) {

      const ownText =
        norm(
          element.textContent
        )


      if (
        ownText
        !== "enviar foto a evaluacion"
      ) {

        continue
      }


      let current =
        element.parentElement


      let candidate =
        null


      for (
        let level = 0;
        level < 5;
        level += 1
      ) {

        if (!current) {
          break
        }


        const text =
          norm(
            current.textContent
          )


        const buttons =
          current.querySelectorAll(
            "button"
          )


        const isCompact =
          text.length
          < 320


        const hasDestination =
          text.includes(
            "destino:"
          )


        const doesNotContainGallery =
          !text.includes(
            "no hay foto seleccionada"
          )


        if (
          hasDestination
          && buttons.length >= 1
          && isCompact
          && doesNotContainGallery
        ) {

          candidate =
            current

          break
        }


        current =
          current.parentElement
      }


      if (
        candidate
      ) {

        candidate.setAttribute(
          "data-sipucol-hidden-photo-evaluation",
          "true"
        )

        continue
      }


      /*
      Fallback:
      ocultar encabezado y fila
      inmediatamente relacionada.
      */

      const row =
        element.parentElement


      if (
        row
      ) {

        row.setAttribute(
          "data-sipucol-hidden-photo-evaluation",
          "true"
        )


        const next =
          row.nextElementSibling


        if (
          next
          && next.querySelectorAll(
            "button"
          ).length
          > 0
        ) {

          next.setAttribute(
            "data-sipucol-hidden-photo-evaluation",
            "true"
          )
        }
      }
    }
  }


  function applyFinalUi() {

    installFlatStyles()

    hidePhotoEvaluationSection()
  }


  function startFinalUi() {

    applyFinalUi()


    const observer =
      new MutationObserver(
        applyFinalUi
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
      startFinalUi,
      {
        once:
          true
      }
    )

  } else {

    startFinalUi()
  }

})()

/* === SIPUCOL_FLAT_NEON_FINAL_END === */
