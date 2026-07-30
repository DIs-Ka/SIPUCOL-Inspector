
/*
============================================================
SIPUCOL — BOTÓN LIMPIAR TODO
============================================================

Módulo nuevo e independiente.

No modifica código antiguo.
No modifica PDF, Excel, Fotos, Evaluación ni Códigos.

Su única responsabilidad es:

- mostrar el botón Limpiar todo;
- borrar el proyecto autoguardado;
- conservar preferencias visuales;
- recargar la aplicación vacía.
*/


const DETECTED_STORAGE_KEYS =
  new Set(
    ["sipucol-autosave-v3", "sipucol-clean-start-applied"]
  )


const BUTTON_ID =
  "sipucol-clear-project-button"


const STYLE_ID =
  "sipucol-clear-project-style"


const LAST_CLEAR_BACKUP_KEY =
  "sipucol-last-clear-snapshot"


let scheduled =
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



function isVisualPreferenceKey(
  key
) {

  const normalized =
    normalizeText(
      key
    )


  return [

    "theme",

    "tema",

    "appearance",

    "apariencia",

    "accent",

    "color",

    "zoom",

    "thumbnail",

    "thumb",

    "miniatura",

    "size",

    "tamano",

    "layout",

    "panel-size",

    "slider",

    "viewer",

    "ui-setting",

    "start-mode",

    "session-mode"

  ].some(

    marker =>

      normalized.includes(
        marker
      )
  )
}



function hasStrongProjectKeyMarker(
  key
) {

  const normalized =
    normalizeText(
      key
    )


  return [

    "project",

    "proyecto",

    "autosave",

    "auto-save",

    "borrador",

    "draft",

    "inspection",

    "inspeccion",

    "evaluation",

    "evaluacion",

    "identification",

    "identificacion",

    "component",

    "componente",

    "damage",

    "dano",

    "observacion",

    "form-data",

    "formdata",

    "app-data",

    "appdata",

    "sipucol-data",

    "sipucol-state",

    "sipucol_state"

  ].some(

    marker =>

      normalized.includes(
        marker
      )
  )
}



function objectLooksLikeProject(
  value
) {

  if (
    value === null
    || typeof value !== "object"
  ) {

    return false
  }


  const markers = new Set([

    "identificacion",

    "identification",

    "componentesestado",

    "componentes",

    "components",

    "tablas",

    "evaluacion",

    "evaluation",

    "observaciones",

    "observations",

    "idpuente",

    "nombrepuente",

    "fechalevantamiento",

    "responsable",

    "administrador",

    "entidad",

    "danos",

    "damages"
  ])


  const keys =
    Object.keys(
      value
    )
    .map(
      normalizeText
    )
    .map(

      key =>

        key.replace(
          /\s+/g,
          ""
        )
    )


  const matches =
    keys.filter(

      key =>

        markers.has(
          key
        )
    ).length


  if (
    matches >= 1
  ) {

    return true
  }


  if (
    Array.isArray(
      value
    )
  ) {

    return value.some(

      item => {

        if (
          !item
          || typeof item !== "object"
        ) {

          return false
        }


        const itemKeys =
          Object.keys(
            item
          )
          .map(
            normalizeText
          )


        return (

          itemKeys.includes(
            "codigo"
          )

          && (
            itemKeys.includes(
              "severidad"
            )

            || itemKeys.includes(
              "fotos"
            )
          )
        )
      }
    )
  }


  return false
}



function valueLooksLikeProject(
  rawValue
) {

  if (
    typeof rawValue !== "string"
    || rawValue.trim() === ""
  ) {

    return false
  }


  try {

    const parsed =
      JSON.parse(
        rawValue
      )


    return objectLooksLikeProject(
      parsed
    )

  } catch {

    return false
  }
}



function shouldDeleteStorageKey(
  key,
  value
) {

  if (
    key === LAST_CLEAR_BACKUP_KEY
  ) {

    return false
  }


  const strongProjectKey =
    hasStrongProjectKeyMarker(
      key
    )


  if (
    isVisualPreferenceKey(
      key
    )

    && !strongProjectKey
  ) {

    return false
  }


  if (
    strongProjectKey
  ) {

    return true
  }


  if (
    DETECTED_STORAGE_KEYS.has(
      key
    )

    && !isVisualPreferenceKey(
      key
    )
  ) {

    return true
  }


  return valueLooksLikeProject(
    value
  )
}



function collectAndDelete(
  storage
) {

  const deleted = {}


  const keys = []


  for (
    let index = 0;
    index < storage.length;
    index += 1
  ) {

    const key =
      storage.key(
        index
      )


    if (key !== null) {

      keys.push(
        key
      )
    }
  }


  for (
    const key
    of keys
  ) {

    const value =
      storage.getItem(
        key
      )


    if (
      !shouldDeleteStorageKey(
        key,
        value
      )
    ) {

      continue
    }


    deleted[key] =
      value


    storage.removeItem(
      key
    )
  }


  return deleted
}



async function deleteSipucolDatabases() {

  if (
    !window.indexedDB

    || typeof indexedDB.databases
       !== "function"
  ) {

    return
  }


  try {

    const databases =
      await indexedDB.databases()


    for (
      const database
      of databases
    ) {

      const name =
        database.name || ""


      const normalized =
        normalizeText(
          name
        )


      if (
        normalized.includes(
          "sipucol"
        )

        || normalized.includes(
          "inspector"
        )

        || normalized.includes(
          "inspeccion"
        )
      ) {

        indexedDB.deleteDatabase(
          name
        )
      }
    }

  } catch {

    /*
    IndexedDB no es necesario para la versión
    actual; este bloque solo es preventivo.
    */
  }
}



async function clearCurrentProject() {

  const confirmed =
    window.confirm(

      "¿Limpiar todo el proyecto?\n\n"

      + "Se borrarán los datos autoguardados: "

      + "identificación, evaluación, daños, "

      + "observaciones y estado de trabajo.\n\n"

      + "No se borrarán archivos Excel, PDF, "

      + "imágenes ni carpetas del computador."
    )


  if (!confirmed) {

    return
  }


  const snapshot = {

    date:
      new Date()
      .toISOString(),

    localStorage:
      collectAndDelete(
        window.localStorage
      ),

    sessionStorage:
      collectAndDelete(
        window.sessionStorage
      )
  }


  try {

    window.sessionStorage.setItem(

      LAST_CLEAR_BACKUP_KEY,

      JSON.stringify(
        snapshot
      )
    )

  } catch {

  }


  await deleteSipucolDatabases()


  window.location.reload()
}



function findControlToolbar() {

  const wantedTexts = new Set([

    "guardar proyecto",

    "cargar proyecto",

    "guardar excel",

    "guardar pdf",

    "generar pdf"
  ])


  const matchingButtons = [

    ...document.querySelectorAll(
      "button"
    )

  ].filter(

    button =>

      wantedTexts.has(

        normalizeText(
          button.textContent
        )
      )
  )


  if (
    matchingButtons.length === 0
  ) {

    return null
  }


  const candidates = []


  for (
    const button
    of matchingButtons
  ) {

    let current =
      button.parentElement


    for (
      let level = 0;
      level < 6;
      level += 1
    ) {

      if (!current) {

        break
      }


      const count = [

        ...current.querySelectorAll(
          "button"
        )

      ].filter(

        candidate =>

          wantedTexts.has(

            normalizeText(
              candidate.textContent
            )
          )
      ).length


      if (
        count >= 2
      ) {

        candidates.push({

          element:
            current,

          count,

          size:
            current.outerHTML.length
        })
      }


      current =
        current.parentElement
    }
  }


  candidates.sort(

    (
      first,
      second
    ) =>

      second.count
      - first.count

      || first.size
      - second.size
  )


  return (

    candidates[0]
      ?.element

    || matchingButtons[0]
       .parentElement
  )
}



function findReferenceButton(
  toolbar
) {

  const priorities = [

    "cargar proyecto",

    "guardar proyecto",

    "guardar excel",

    "guardar pdf"
  ]


  for (
    const priority
    of priorities
  ) {

    const button = [

      ...toolbar.querySelectorAll(
        "button"
      )

    ].find(

      candidate =>

        normalizeText(
          candidate.textContent
        )
        === priority
    )


    if (button) {

      return button
    }
  }


  return null
}



function installButton() {

  if (
    document.getElementById(
      BUTTON_ID
    )
  ) {

    return true
  }


  const toolbar =
    findControlToolbar()


  if (!toolbar) {

    return false
  }


  const reference =
    findReferenceButton(
      toolbar
    )


  const button =
    document.createElement(
      "button"
    )


  button.id =
    BUTTON_ID


  button.type =
    "button"


  button.textContent =
    "Limpiar todo"


  button.title =
    "Borrar los datos del proyecto actual"


  if (
    reference
    && typeof reference.className
       === "string"
  ) {

    button.className =
      reference.className
  }


  button.addEventListener(

    "click",

    clearCurrentProject
  )


  toolbar.appendChild(
    button
  )


  return true
}



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

    #${BUTTON_ID} {

      border:
        1px solid
        rgba(
          255,
          111,
          104,
          0.72
        )
        !important;

      background:
        rgba(
          102,
          28,
          35,
          0.78
        )
        !important;

      background-image:
        none !important;

      color:
        #fff2f2
        !important;

      box-shadow:
        0 0 12px
        rgba(
          255,
          79,
          87,
          0.12
        )
        !important;

      text-shadow:
        none !important;

      transition:
        transform 140ms ease,
        background 140ms ease,
        box-shadow 140ms ease
        !important;
    }


    #${BUTTON_ID}:hover {

      transform:
        translateY(
          -1px
        )
        !important;

      background:
        rgba(
          132,
          34,
          43,
          0.9
        )
        !important;

      box-shadow:
        0 0 18px
        rgba(
          255,
          83,
          90,
          0.22
        )
        !important;
    }


    #${BUTTON_ID}:active {

      transform:
        scale(
          0.985
        )
        !important;
    }
  `


  document.head.appendChild(
    style
  )
}



function scheduleInstall() {

  if (scheduled) {

    return
  }


  scheduled =
    true


  requestAnimationFrame(

    () => {

      scheduled =
        false


      installButton()
    }
  )
}



function start() {

  installStyles()

  installButton()


  const observer =
    new MutationObserver(
      scheduleInstall
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

    start,

    {
      once:
        true
    }
  )

} else {

  start()
}
