
/*
SIPUCOL — Inicio siempre limpio

Solo elimina datos persistidos de esta aplicación.
No toca archivos Excel ni proyectos JSON guardados
en el computador.
*/

const clavesExactas = [
  "sipucol-data",
  "sipucol-project",
  "sipucol-inspector",
  "sipucol-evaluacion",
  "sipucol-identificacion",
  "sipucol-componentes",
  "sipucol-fotos",
  "sipucol-start-mode",
  "sipucol-clean-start-applied"
]

const patronesSIPUCOL = [
  "sipucol",
  "inspector",
  "componentesestado",
  "bloquesevaluacion",
  "identificacion",
  "evaluacion"
]

function esClaveDeDatosSIPUCOL(clave) {
  const normalizada = String(clave || "").toLowerCase()

  return (
    clavesExactas.includes(normalizada)
    || patronesSIPUCOL.some(
      patron => normalizada.includes(patron)
    )
  )
}

try {
  const claves = []

  for (
    let indice = 0;
    indice < localStorage.length;
    indice += 1
  ) {
    const clave = localStorage.key(indice)

    if (
      clave
      && esClaveDeDatosSIPUCOL(clave)
    ) {
      claves.push(clave)
    }
  }

  for (const clave of claves) {
    localStorage.removeItem(clave)
  }

  /*
  También limpiamos estados temporales antiguos.
  Esto no afecta archivos guardados.
  */
  sessionStorage.removeItem(
    "sipucol-clean-start-applied"
  )
} catch (error) {
  console.warn(
    "[SIPUCOL] No se pudieron limpiar datos iniciales:",
    error
  )
}
