const fs = require('fs')
const path = require('path')
const XLSX = require('xlsx')

const archivoExcel = path.join(
  process.cwd(),
  'manuals',
  '04. FORMATO INSPECCION NIVEL 2 CON CALCULO DE IC SIN BLOQUEO (1).xlsm'
)

const salida = path.join(process.cwd(), 'src', 'data', 'formatoSIPUCOL.js')

const codigoRegex = /^(D\d|E\d|S\d|DR\d|D23-8)/i

function limpiar(valor) {
  return String(valor ?? '')
    .replace(/\s+/g, ' ')
    .trim()
}

function areaPorCodigo(codigo) {
  const c = codigo.toUpperCase()

  if (c.startsWith('DR')) return 'Daños relevantes'
  if (c.startsWith('D')) return 'Durabilidad'
  if (c.startsWith('E')) return 'Estabilidad'
  if (c.startsWith('S')) return 'Seguridad vial'

  return 'Sin área'
}

function idSeguro(texto) {
  return texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^A-Za-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

const workbook = XLSX.readFile(archivoExcel, {
  cellDates: false,
  cellFormula: false,
  cellStyles: false
})

const hojasIgnoradas = new Set([
  'ÍNDICE',
  'INDICE',
  'CALCULO IC',
  'CÁLCULO IC',
  'CALCULO DE IC',
  'CÁLCULO DE IC'
])

const componentes = []

for (const nombreHoja of workbook.SheetNames) {
  const nombre = limpiar(nombreHoja)
  const nombreMayus = nombre.toUpperCase()

  if (!nombre) continue
  if (hojasIgnoradas.has(nombreMayus)) continue
  if (nombreMayus.startsWith('ANX')) continue

  const hoja = workbook.Sheets[nombreHoja]

  const filas = XLSX.utils.sheet_to_json(hoja, {
    header: 1,
    defval: ''
  })

  const items = []
  const vistos = new Set()

  filas.forEach((fila, index) => {
    const filaExcel = index + 1
    const celdas = fila.map(limpiar)

    const indiceCodigo = celdas.findIndex((celda) => codigoRegex.test(celda))
    if (indiceCodigo === -1) return

    const codigo = celdas[indiceCodigo]

    const textosDerecha = celdas
      .slice(indiceCodigo + 1)
      .filter(Boolean)

    const dano = textosDerecha[0] || ''
    const detalle = textosDerecha.slice(1, 4).join(' / ')

    const clave = [
      nombre,
      codigo,
      dano,
      detalle
    ].join('|').toLowerCase()

    if (vistos.has(clave)) return
    vistos.add(clave)

    items.push({
      id: `${idSeguro(nombre)}-${items.length + 1}-${idSeguro(codigo)}`,
      hoja: nombre,
      filaExcel,
      codigo,
      dano,
      detalle,
      area: areaPorCodigo(codigo)
    })
  })

  if (items.length > 0) {
    componentes.push({
      id: idSeguro(nombre),
      nombre,
      items
    })
  }
}

const totalItems = componentes.reduce((acc, comp) => acc + comp.items.length, 0)

const contenido =
  `export const plantillaEvaluacion = ${JSON.stringify(componentes, null, 2)}\n\n` +
  `export const resumenFormato = ${JSON.stringify({
    componentes: componentes.length,
    items: totalItems
  }, null, 2)}\n`

fs.writeFileSync(salida, contenido, 'utf8')

console.log('Listo.')
console.log(`Componentes encontrados: ${componentes.length}`)
console.log(`Filas únicas de evaluación: ${totalItems}`)
console.log(`Archivo generado: ${salida}`)

for (const comp of componentes) {
  console.log(`- ${comp.nombre}: ${comp.items.length} filas únicas`)
}
