import { useEffect, useMemo, useRef, useState } from 'react'
import { plantillaEvaluacion } from '../data/formatoSIPUCOL'
import { areasCodigos, codigosSIPUCOL } from '../data/codigosSIPUCOL'

const API_BASE = 'http://127.0.0.1:8000'
const severidades = [0, 1, 2, 3, 4, 5]

const camposIdentificacion = [
  ['nombrePuente', 'Nombre del puente'],
  ['idPuente', 'ID Puente'],
  ['administradorVial', 'Administrador vial'],
  ['entidadAdministradora', 'Entidad administradora'],
  ['responsableDiligenciamiento', 'Responsable del diligenciamiento'],
  ['cargoDiligenciamiento', 'Cargo'],
  ['tarjetaDiligenciamiento', 'Tarjeta profesional'],
  ['responsableRevision', 'Responsable de la revisión'],
  ['cargoRevision', 'Cargo revisión'],
  ['tarjetaRevision', 'Tarjeta profesional revisión'],
  ['fecha', 'Fecha de levantamiento'],
  ['hora', 'Hora']
]

const bloquesEvaluacionIniciales = [
  'Superficie del Puente',
  'Juntas de dilatación',
  'Bordillo',
  'Barandas',
  'Aletas',
  'Estribos',
  'Apoyos',
  'Losa',
  'Vigas',
  'Señalización',
  'Puente en General'
]

function crearIdentificacionInicial() {
  return camposIdentificacion.reduce((acc, [key]) => {
    acc[key] = ''
    return acc
  }, {})
}

function limpiarTexto(valor) {
  return String(valor || '').replace(/\s+/g, ' ').trim()
} 

function escaparRegex(texto) {
  return String(texto || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function valorMalo(valor) {
  const v = limpiarTexto(valor).toLowerCase()

  if (!v) return true
  if (v === '0') return true
  if (v === '-') return true
  if (v === 'null') return true
  if (v === 'undefined') return true
  if (v === 'nan') return true
  if (/^0(\s*\/\s*0)+$/.test(v)) return true
  if (/^\d+([.,]\d+)?$/.test(v)) return true

  return false
}

function crearIndiceCatalogoSIPUCOL() {
  const lista = Array.isArray(areasCodigos) ? areasCodigos : []
  const mapa = new Map()

  for (const item of lista) {
    const codigo = limpiarTexto(item.codigo || item.code || item.id).toUpperCase()

    if (!codigo) continue

    mapa.set(codigo, item)
  }

  return mapa
}

const INDICE_CATALOGO_SIPUCOL = crearIndiceCatalogoSIPUCOL()

function buscarCatalogoSIPUCOL(codigo) {
  return INDICE_CATALOGO_SIPUCOL.get(limpiarTexto(codigo).toUpperCase())
}

function limpiarTituloCatalogo(codigo, texto) {
  let t = limpiarTexto(texto)

  if (!t) return ''

  t = t.replace(new RegExp('^' + escaparRegex(codigo) + '\\s*[-–:.]?\\s*', 'i'), '')
  t = t.replace(/^\d+(\.\d+)*\s+/, '')

  const cortes = [
    ' Tipo de ',
    ' Condiciones ',
    ' Condiciones patológicas',
    ' Calificación ',
    ' Insignificante',
    ' Ligero',
    ' Leve',
    ' Fuerte',
    ' Severo',
    ' Extremo',
    ' No presenta',
    ' Fuente:',
    ' Fuente :'
  ]

  let limite = -1

  for (const corte of cortes) {
    const pos = t.toLowerCase().indexOf(corte.toLowerCase())

    if (pos > 4 && (limite === -1 || pos < limite)) {
      limite = pos
    }
  }

  if (limite > 0) {
    t = t.slice(0, limite)
  }

  return limpiarTexto(t)
}

function primerCampoValido(obj, campos) {
  for (const campo of campos) {
    const valor = limpiarTexto(obj?.[campo])

    if (!valorMalo(valor)) return valor
  }

  return ''
}

function tituloDesdeCatalogo(codigo) {
  const catalogo = buscarCatalogoSIPUCOL(codigo)

  if (!catalogo) return ''

  const directo = primerCampoValido(catalogo, [
    'nombre',
    'titulo',
    'title',
    'name',
    'dano',
    'daño',
    'descripcionCorta',
    'descripcion_corta'
  ])

  if (directo) {
    return limpiarTituloCatalogo(codigo, directo)
  }

  const desdeExtracto = primerCampoValido(catalogo, [
    'extracto',
    'texto',
    'descripcion',
    'description'
  ])

  return limpiarTituloCatalogo(codigo, desdeExtracto)
}

function danoEvaluacionSeguro(codigo, item) {
  const original = primerCampoValido(item, [
    'dano',
    'daño',
    'deterioro',
    'nombre',
    'titulo'
  ])

  if (original) {
    return limpiarTituloCatalogo(codigo, original)
  }

  const catalogo = tituloDesdeCatalogo(codigo)

  if (catalogo) return catalogo

  return codigo || 'Daño sin nombre'
}

function materialDesdeCodigo(codigo, catalogo) {
  const desdeCatalogo = primerCampoValido(catalogo, [
    'material',
    'materiales',
    'tipoMaterial',
    'tipo_material',
    'elemento',
    'componente'
  ])

  if (desdeCatalogo) return desdeCatalogo

  const area = primerCampoValido(catalogo, [
    'area',
    'categoría',
    'categoria',
    'grupo'
  ])

  if (area) return area

  const c = limpiarTexto(codigo).toUpperCase()

  if (c.startsWith('D1') || c.startsWith('E1') || c.startsWith('S1')) return 'Superficie / accesos'
  if (c.startsWith('D2') || c.startsWith('E2')) return 'Subestructura'
  if (c.startsWith('D3') || c.startsWith('E3')) return 'Superestructura'
  if (c.startsWith('D4') || c.startsWith('E4')) return 'Hidráulico / cauce'
  if (c.startsWith('D6') || c.startsWith('E6')) return 'Concreto / acero'
  if (c.startsWith('S')) return 'Seguridad vial'
  if (c.startsWith('DR')) return 'Daño relevante'

  return 'No especificado'
}

function materialDetalleSeguro(codigo, item) {
  const catalogo = buscarCatalogoSIPUCOL(codigo)

  const materialDirecto = primerCampoValido(item, [
    'material',
    'materiales',
    'tipoMaterial',
    'tipo_material',
    'elemento',
    'componente'
  ])

  const detalleOriginal = limpiarTexto(
    item?.detalle ||
    item?.materialDetalle ||
    item?.material_detalle ||
    item?.descripcionMaterial ||
    ''
  )

  const partesValidas = detalleOriginal
    .split('/')
    .map((p) => limpiarTexto(p))
    .filter((p) => !valorMalo(p))
    .filter((p) => p.toUpperCase() !== limpiarTexto(codigo).toUpperCase())

  let material = ''

  if (materialDirecto) {
    material = materialDirecto
  } else if (partesValidas.length) {
    material = partesValidas[0]
  } else {
    material = materialDesdeCodigo(codigo, catalogo)
  }

  const extras = partesValidas
    .slice(material === partesValidas[0] ? 1 : 0)
    .filter((p) => p.toUpperCase() !== limpiarTexto(codigo).toUpperCase())

  const salida = [material, codigo, ...extras]
    .map((p) => limpiarTexto(p))
    .filter((p) => !valorMalo(p))

  return salida.join(' / ') || `${materialDesdeCodigo(codigo, catalogo)} / ${codigo}`
}

function normalizarItemEvaluacion(item) {
  const codigo = limpiarTexto(item.codigo)

  return {
    ...item,
    codigo,
    dano: danoEvaluacionSeguro(codigo, item),
    detalle: materialDetalleSeguro(codigo, item)
  }
}

function normalizarComponentesGuardados(lista) {
  return ordenarComponentesComoExcel(
    (lista || [])
      .map((componente) => ({
        ...componente,
        items: (componente.items || [])
          .map(normalizarItemEvaluacion)
          .filter((item) => item.codigo && item.dano)
      }))
      .filter((componente) => componente.items.length > 0)
  )
}



function numeroFilaExcel(item, fallback = 999999) {
  const posibles = [
    item?.filaExcel,
    item?.fila,
    item?.row,
    item?.rowExcel,
    item?.excelRow,
    item?.numeroFila
  ]

  for (const valor of posibles) {
    const n = Number(String(valor || '').replace(/[^0-9]/g, ''))

    if (Number.isFinite(n) && n > 0) return n
  }

  return fallback
}

function ordenarItemsComoExcel(items) {
  return [...(items || [])].sort((a, b) => {
    const filaA = numeroFilaExcel(a)
    const filaB = numeroFilaExcel(b)

    if (filaA !== filaB) return filaA - filaB

    const ordenA = Number(a?.ordenOriginal ?? a?.orden ?? 999999)
    const ordenB = Number(b?.ordenOriginal ?? b?.orden ?? 999999)

    if (ordenA !== ordenB) return ordenA - ordenB

    return String(a?.codigo || '').localeCompare(String(b?.codigo || ''))
  })
}

function ordenarComponentesComoExcel(componentes) {
  return (componentes || []).map((componente) => ({
    ...componente,
    items: ordenarItemsComoExcel(componente.items)
  }))
}

function crearPlantillaInicial() {
  return plantillaEvaluacion
    .map((componente) => {
      const vistos = new Set()

      const items = componente.items
        .map((item, index) => {
          const codigo = limpiarTexto(item.codigo)
          const itemNormalizado = normalizarItemEvaluacion(item)
          const dano = itemNormalizado.dano
          const detalle = itemNormalizado.detalle

          return {
            ...item,
            id: `${componente.id}-${index}-${codigo}`,
            ordenOriginal: index,
            codigo,
            dano,
            detalle,
            severidad: '',
            fotos: '',
            ubicacion: ''
          }
        })
        .filter((item) => {
          if (!item.codigo || !item.dano) return false

          const clave = `${item.codigo}|${item.dano}|${item.detalle}`.toLowerCase()

          if (vistos.has(clave)) return false

          vistos.add(clave)
          return true
        })

      return {
        ...componente,
        items: ordenarItemsComoExcel(items)
      }
    })
    .filter((componente) => componente.items.length > 0)
}

function crearBloquesEvaluacionIniciales() {
  return bloquesEvaluacionIniciales.map((nombre) => ({
    nombre,
    descripcion: '',
    calificacion: '',
    candidatas: [],
    imagenes: []
  }))
}

function normalizarBloquesEvaluacion(lista) {
  const base = Array.isArray(lista) && lista.length
    ? lista
    : crearBloquesEvaluacionIniciales()

  return base.map((bloque) => ({
    nombre: bloque.nombre || 'Bloque sin nombre',
    descripcion: bloque.descripcion || '',
    calificacion: bloque.calificacion || '',
    candidatas: Array.isArray(bloque.candidatas) ? bloque.candidatas.slice(-20) : [],
    imagenes: Array.isArray(bloque.imagenes) ? bloque.imagenes.slice(0, 4) : []
  }))
}

function leerAutosave() {
  try {
    const raw = localStorage.getItem('sipucol-autosave-v3')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function nombreSeguro(texto) {
  return String(texto || 'INSPECCION_SIPUCOL')
    .replace(/[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ _-]+/g, '')
    .replace(/\s+/g, '_')
    .slice(0, 80)
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

export default function PanelEvaluacion({ codigoEnviado, fotoDesdePanelFotos }) {
  const autosave = leerAutosave()

  const [identificacion, setIdentificacion] = useState(
    () => autosave?.identificacion || crearIdentificacionInicial()
  )

  const [componentes, setComponentes] = useState(
    () => normalizarComponentesGuardados(autosave?.componentesEstado || crearPlantillaInicial())
  )

  const [bloquesEvaluacion, setBloquesEvaluacion] = useState(
    () => normalizarBloquesEvaluacion(autosave?.bloquesEvaluacion || crearBloquesEvaluacionIniciales())
  )

  const [componenteActivoId, setComponenteActivoId] = useState('')
  const [busqueda, setBusqueda] = useState('')
  const [filaResaltada, setFilaResaltada] = useState('')
  const [anchoScroll, setAnchoScroll] = useState(1010)
  const [estado, setEstado] = useState('Listo')
  const [progreso, setProgreso] = useState(0)
  const [trabajando, setTrabajando] = useState(false)
  const [modalImagenes, setModalImagenes] = useState(false)
  const [identificacionAbierta, setIdentificacionAbierta] = useState(() => {
    const base = autosave?.identificacion || {}

    return !['nombrePuente', 'idPuente', 'administradorVial', 'responsableDiligenciamiento'].every(
      (key) => limpiarTexto(base[key])
    )
  })
  const [bloqueActivo, setBloqueActivo] = useState(0)
  const [componentesAbierto, setComponentesAbierto] = useState(true)

  const scrollSuperiorRef = useRef(null)
  const tablaScrollRef = useRef(null)
  const tablaRef = useRef(null)
  const cargarProyectoRef = useRef(null)
  const ultimaFotoRecibidaRef = useRef(null)

  const componenteActivo = useMemo(() => {
    return componentes.find((componente) => componente.id === componenteActivoId) || componentes[0]
  }, [componentes, componenteActivoId])

  const filasVisibles = useMemo(() => {
    if (!componenteActivo) return []

    const q = busqueda.toLowerCase().trim()

    return ordenarItemsComoExcel(componenteActivo.items).filter((item) => {
      const texto = [
        item.codigo,
        item.dano,
        item.detalle,
        item.area,
        item.filaExcel
      ].join(' ').toLowerCase()

      return !q || texto.includes(q)
    })
  }, [componenteActivo, busqueda])

  const totalFilas = useMemo(() => {
    return componentes.reduce((acc, componente) => acc + componente.items.length, 0)
  }, [componentes])

  const filasLlenas = useMemo(() => {
    return componentes.reduce((acc, componente) => {
      return acc + componente.items.filter((item) =>
        item.severidad !== '' || item.fotos || item.ubicacion
      ).length
    }, 0)
  }, [componentes])

  const identificacionBasicaCompleta = useMemo(() => {
    return ['nombrePuente', 'idPuente', 'administradorVial', 'responsableDiligenciamiento'].every(
      (key) => limpiarTexto(identificacion[key])
    )
  }, [identificacion])

  useEffect(() => {
    if (!componentes.length) return
    if (!componenteActivoId) setComponenteActivoId(componentes[0].id)
  }, [componentes, componenteActivoId])

  // normalizar componentes ya cargados para corregir filas con 0 / 0 / 0
  useEffect(() => {
    setComponentes((actuales) => {
      const normalizados = normalizarComponentesGuardados(actuales)

      if (JSON.stringify(normalizados) === JSON.stringify(actuales)) {
        return actuales
      }

      return normalizados
    })
  }, [])

  useEffect(() => {
    if (identificacionBasicaCompleta && identificacionAbierta) {
      setIdentificacionAbierta(false)
      setEstado('Identificación básica completa. Se cerró para dar más espacio.')
    }
  }, [identificacionBasicaCompleta, identificacionAbierta])

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      if (!tablaRef.current) return
      setAnchoScroll(tablaRef.current.scrollWidth)
    })

    return () => cancelAnimationFrame(frame)
  }, [filasVisibles, componenteActivo?.id])

  useEffect(() => {
    const timer = setTimeout(() => {
      try {
        localStorage.setItem(
          'sipucol-autosave-v3',
          JSON.stringify({
            identificacion,
            componentesEstado: componentes,
            bloquesEvaluacion
          })
        )
      } catch {
        setEstado('Autosave no disponible. Guarda proyecto manualmente.')
      }
    }, 700)

    return () => clearTimeout(timer)
  }, [identificacion, componentes, bloquesEvaluacion])

  useEffect(() => {
    if (!codigoEnviado?.codigo) return

    const codigoBuscado = codigoEnviado.codigo.toLowerCase()
    let componenteDestino = null
    let filaDestino = null

    for (const componente of componentes) {
      const fila = componente.items.find(
        (item) => item.codigo.toLowerCase() === codigoBuscado
      )

      if (fila) {
        componenteDestino = componente
        filaDestino = fila
        break
      }
    }

    if (!componenteDestino || !filaDestino) {
      setBusqueda(codigoEnviado.codigo)
      return
    }

    setComponenteActivoId(componenteDestino.id)
    setBusqueda(codigoEnviado.codigo)
    setFilaResaltada(filaDestino.id)

    setTimeout(() => {
      document
        .getElementById(`fila-${filaDestino.id}`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 120)
  }, [codigoEnviado, componentes])

  useEffect(() => {
    if (!fotoDesdePanelFotos?.foto?.url) return
    recibirFotoDesdePanelFotosEvaluacion(fotoDesdePanelFotos)
  }, [fotoDesdePanelFotos?.token])

  function actualizarIdentificacion(key, value) {
    setIdentificacion((actual) => ({
      ...actual,
      [key]: value
    }))
  }

  function actualizarFila(id, cambios) {
    setComponentes((actuales) =>
      actuales.map((componente) => ({
        ...componente,
        items: componente.items.map((item) =>
          item.id === id ? { ...item, ...cambios } : item
        )
      }))
    )
  }

  function actualizarComponenteActivo(cambios) {
    if (!componenteActivo) return

    setComponentes((actuales) =>
      actuales.map((componente) =>
        componente.id === componenteActivo.id
          ? { ...componente, ...cambios }
          : componente
      )
    )
  }

  function seleccionarSeveridad(item, nivel) {
    const yaMarcado = String(item.severidad) === String(nivel)

    actualizarFila(item.id, {
      severidad: yaMarcado ? '' : String(nivel)
    })
  }

  function sincronizarScrollSuperior() {
    if (!scrollSuperiorRef.current || !tablaScrollRef.current) return
    tablaScrollRef.current.scrollLeft = scrollSuperiorRef.current.scrollLeft
  }

  function sincronizarScrollTabla() {
    if (!scrollSuperiorRef.current || !tablaScrollRef.current) return
    scrollSuperiorRef.current.scrollLeft = tablaScrollRef.current.scrollLeft
  }

  function crearPayload() {
    const base = nombreSeguro(identificacion.nombrePuente || 'INSPECCION_SIPUCOL')

    const tablas = componentes
      .map((componente) => ({
        nombre: componente.nombre,
        observacionesLevantamiento: componente.observacionesLevantamiento || '',
        observacionesRevisor: componente.observacionesRevisor || '',
        items: componente.items.filter((item) =>
          item.severidad !== '' || item.fotos || item.ubicacion
        )
      }))
      .filter((componente) =>
        componente.items.length > 0 ||
        componente.observacionesLevantamiento ||
        componente.observacionesRevisor
      )

    return {
      version: '1.0',
      app: 'SIPUCOL Inspector',
      projectName: base,
      nombreArchivo: `${base}.xlsm`,
      identificacion,
      componentesEstado: componentes,
      bloquesEvaluacion,
      detalleEvaluacion: bloquesEvaluacion,
      tablas,
      evaluacion: bloquesEvaluacion
    }
  }

  async function guardarBlobConVentana(blob, nombreSugerido, descripcion, mime, extension) {
    if (window.showSaveFilePicker) {
      const handle = await window.showSaveFilePicker({
        suggestedName: nombreSugerido,
        types: [
          {
            description: descripcion,
            accept: {
              [mime]: [extension]
            }
          }
        ]
      })

      const writable = await handle.createWritable()
      await writable.write(blob)
      await writable.close()

      return handle.name
    }

    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')

    link.href = url
    link.download = nombreSugerido
    document.body.appendChild(link)
    link.click()
    link.remove()

    URL.revokeObjectURL(url)

    return nombreSugerido
  }

  async function pedirArchivoAlBackend(endpoint, nombreSugerido, descripcion, mime, extension) {
    let handle = null

    if (window.showSaveFilePicker) {
      handle = await window.showSaveFilePicker({
        suggestedName: nombreSugerido,
        types: [
          {
            description: descripcion,
            accept: {
              [mime]: [extension]
            }
          }
        ]
      })
    }

    const payload = crearPayload()

    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })

    if (!res.ok) {
      let mensaje = 'Error exportando archivo'

      try {
        const errorData = await res.json()
        mensaje = errorData.detail || mensaje
      } catch {
        mensaje = await res.text()
      }

      throw new Error(mensaje)
    }

    const blob = await res.blob()

    if (handle) {
      const writable = await handle.createWritable()
      await writable.write(blob)
      await writable.close()
      return handle.name
    }

    return guardarBlobConVentana(blob, nombreSugerido, descripcion, mime, extension)
  }

  async function guardarProyecto() {
    const payload = crearPayload()
    const base = nombreSeguro(identificacion.nombrePuente || 'PROYECTO_SIPUCOL')
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: 'application/json'
    })

    setTrabajando(true)
    setProgreso(20)
    setEstado('Guardando proyecto...')

    try {
      const nombre = await guardarBlobConVentana(
        blob,
        `${base}.sipucol.json`,
        'Proyecto SIPUCOL',
        'application/json',
        '.json'
      )

      setProgreso(100)
      setEstado(`Proyecto guardado: ${nombre}`)
    } catch (error) {
      setEstado(`No se guardó el proyecto: ${error.message}`)
    } finally {
      setTrabajando(false)
    }
  }

  function cargarProyectoDesdeArchivo(event) {
    const file = event.target.files?.[0]

    if (!file) return

    const reader = new FileReader()

    reader.onload = () => {
      try {
        const proyecto = JSON.parse(reader.result)

        if (proyecto.identificacion) {
          setIdentificacion(proyecto.identificacion)
        }

        if (proyecto.componentesEstado) {
          setComponentes(normalizarComponentesGuardados(proyecto.componentesEstado))
        }

        if (proyecto.bloquesEvaluacion) {
          setBloquesEvaluacion(normalizarBloquesEvaluacion(proyecto.bloquesEvaluacion))
        } else if (proyecto.detalleEvaluacion) {
          setBloquesEvaluacion(normalizarBloquesEvaluacion(proyecto.detalleEvaluacion))
        } else if (proyecto.evaluacion) {
          setBloquesEvaluacion(normalizarBloquesEvaluacion(proyecto.evaluacion))
        }

        setBusqueda('')
        setFilaResaltada('')
        setEstado('Proyecto cargado.')
      } catch (error) {
        setEstado(`No se pudo cargar el proyecto: ${error.message}`)
      }
    }

    reader.readAsText(file, 'utf-8')
    event.target.value = ''
  }

  async function exportarExcel() {
    const base = nombreSeguro(identificacion.nombrePuente || 'INSPECCION_SIPUCOL')

    setTrabajando(true)
    setProgreso(10)
    setEstado('Preparando Excel...')

    try {
      setProgreso(40)

      const nombre = await pedirArchivoAlBackend(
        '/api/export/excel-file',
        `${base}.xlsm`,
        'Excel SIPUCOL',
        'application/vnd.ms-excel.sheet.macroEnabled.12',
        '.xlsm'
      )

      setProgreso(100)
      setEstado(`Excel guardado: ${nombre}`)
    } catch (error) {
      setEstado(`Error guardando Excel: ${error.message}`)
    } finally {
      setTrabajando(false)
    }
  }

  async function exportarPdf() {
    const base = nombreSeguro(identificacion.nombrePuente || 'INSPECCION_SIPUCOL')

    setTrabajando(true)
    setProgreso(10)
    setEstado('Preparando PDF...')

    try {
      setProgreso(40)

      const nombre = await pedirArchivoAlBackend(
        '/api/export/pdf-file',
        `${base}.pdf`,
        'PDF SIPUCOL',
        'application/pdf',
        '.pdf'
      )

      setProgreso(100)
      setEstado(`PDF guardado: ${nombre}`)
    } catch (error) {
      setEstado(`Error guardando PDF: ${error.message}`)
    } finally {
      setTrabajando(false)
    }
  }

  function normalizarNombreBloqueEvaluacion(nombre) {
    return limpiarTexto(nombre)
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
  }

  function indiceBloquePorNombre(nombre) {
    const objetivo = normalizarNombreBloqueEvaluacion(nombre)

    if (!objetivo) return 0

    const exacto = bloquesEvaluacion.findIndex(
      (bloque) => normalizarNombreBloqueEvaluacion(bloque.nombre) === objetivo
    )

    if (exacto >= 0) return exacto

    const parcial = bloquesEvaluacion.findIndex((bloque) => {
      const b = normalizarNombreBloqueEvaluacion(bloque.nombre)
      return b.includes(objetivo) || objetivo.includes(b)
    })

    return parcial >= 0 ? parcial : 0
  }

  function agregarCandidataEvaluacion(bloqueIndex, candidata) {
    const indexSeguro = Math.max(0, Math.min(Number(bloqueIndex) || 0, bloquesEvaluacion.length - 1))
    const src = candidata?.src || candidata

    if (!src) return

    setBloquesEvaluacion((actuales) =>
      actuales.map((bloque, index) => {
        if (index !== indexSeguro) return bloque

        const candidatasActuales = Array.isArray(bloque.candidatas) ? bloque.candidatas : []
        const yaExiste = candidatasActuales.some((img) => (img.src || img) === src)

        if (yaExiste) return bloque

        return {
          ...bloque,
          candidatas: [
            ...candidatasActuales,
            {
              src,
              nombre: candidata?.nombre || `foto_${candidatasActuales.length + 1}`
            }
          ].slice(-20)
        }
      })
    )

    setBloqueActivo(indexSeguro)
  }

  async function recibirFotoDesdePanelFotosEvaluacion(payload) {
    const foto = payload?.foto

    if (!foto?.url) return

    const clave = payload?.token || `${foto.id}-${payload?.bloqueNombre}`

    if (ultimaFotoRecibidaRef.current === clave) return
    ultimaFotoRecibidaRef.current = clave

    try {
      setEstado('Recibiendo foto desde Panel Fotos...')

      let dataUrl = foto.url

      if (!foto.url.startsWith('data:image')) {
        const blob = await fetch(foto.url).then((res) => res.blob())
        dataUrl = await blobToDataUrl(blob)
      }

      const bloqueIndex = indiceBloquePorNombre(payload?.bloqueNombre)

      agregarCandidataEvaluacion(bloqueIndex, {
        src: dataUrl,
        nombre: foto.nombre || 'foto_inspeccion'
      })

      setModalImagenes(true)
      setEstado('Foto recibida como candidata. Pulsa “usar” para fijarla en Excel/PDF.')
    } catch (error) {
      setEstado(`No se pudo recibir la foto: ${error.message}`)
    }
  }

  function fijarCandidataEvaluacion(candidata) {
    const src = candidata?.src || candidata

    if (!src) return

    setBloquesEvaluacion((actuales) =>
      actuales.map((bloque, index) => {
        if (index !== bloqueActivo) return bloque

        const fijas = Array.isArray(bloque.imagenes) ? bloque.imagenes : []

        if (fijas.includes(src)) return bloque

        if (fijas.length >= 4) {
          setEstado('Máximo 4 fotos usadas por bloque para no romper el formato del Excel.')
          return bloque
        }

        return {
          ...bloque,
          imagenes: [...fijas, src]
        }
      })
    )
  }

  function quitarCandidataEvaluacion(candidataIndex) {
    setBloquesEvaluacion((actuales) =>
      actuales.map((bloque, index) => {
        if (index !== bloqueActivo) return bloque

        return {
          ...bloque,
          candidatas: (bloque.candidatas || []).filter((_, i) => i !== candidataIndex)
        }
      })
    )
  }

  function moverImagenFijaEvaluacion(origen, direccion) {
    setBloquesEvaluacion((actuales) =>
      actuales.map((bloque, index) => {
        if (index !== bloqueActivo) return bloque

        const fijas = [...(bloque.imagenes || [])]
        const destino = origen + direccion

        if (destino < 0 || destino >= fijas.length) return bloque

        const temp = fijas[origen]
        fijas[origen] = fijas[destino]
        fijas[destino] = temp

        return {
          ...bloque,
          imagenes: fijas
        }
      })
    )
  }

  function actualizarBloqueEvaluacion(cambios) {
    setBloquesEvaluacion((actuales) =>
      actuales.map((bloque, index) =>
        index === bloqueActivo ? { ...bloque, ...cambios } : bloque
      )
    )
  }

  async function agregarImagenesAlBloque(event) {
    const files = Array.from(event.target.files || [])

    if (!files.length) return

    setEstado('Agregando imágenes como candidatas...')

    const candidatas = await Promise.all(
      files.map(async (file) => ({
        src: await fileToDataUrl(file),
        nombre: file.name
      }))
    )

    candidatas.forEach((candidata) => agregarCandidataEvaluacion(bloqueActivo, candidata))

    event.target.value = ''
    setEstado('Imágenes agregadas como candidatas. Pulsa “usar” para fijarlas en Excel/PDF.')
  }

  function quitarImagenDelBloque(imgIndex) {
    setBloquesEvaluacion((actuales) =>
      actuales.map((bloque, index) => {
        if (index !== bloqueActivo) return bloque

        return {
          ...bloque,
          imagenes: bloque.imagenes.filter((_, i) => i !== imgIndex)
        }
      })
    )
  }

  const bloqueActual = bloquesEvaluacion[bloqueActivo] || bloquesEvaluacion[0]

  return (
    <section style={styles.panel}>
      <header style={styles.header}>
        <div>
          <h2 style={styles.titulo}>Evaluación</h2>
          <p style={styles.subtitulo}>
            Plantilla cargada · {componentes.length} componentes · {totalFilas} filas · {filasLlenas} llenas
          </p>
        </div>
      </header>

      <section style={styles.toolbar}>
        <button disabled={trabajando} onClick={guardarProyecto} style={styles.actionBtn}>
          Guardar proyecto
        </button>

        <button disabled={trabajando} onClick={() => cargarProyectoRef.current?.click()} style={styles.actionBtn}>
          Cargar proyecto
        </button>

        <button disabled={trabajando} onClick={() => setModalImagenes(true)} style={styles.actionBtn}>
          Imágenes Evaluación
        </button>

        <button disabled={trabajando} onClick={exportarExcel} style={styles.actionBtnPrimary}>
          Guardar Excel
        </button>

        <button disabled={trabajando} onClick={exportarPdf} style={styles.actionBtnPrimary}>
          Guardar PDF
        </button>

        <input
          ref={cargarProyectoRef}
          type="file"
          accept=".json,.sipucol.json,application/json"
          onChange={cargarProyectoDesdeArchivo}
          style={{ display: 'none' }}
        />
      </section>

      <div style={styles.progressWrap}>
        <div style={{ ...styles.progressBar, width: `${progreso}%` }} />
      </div>

      <div style={styles.estado}>{estado}</div>

      <section style={styles.identificacion}>
        <button
          onClick={() => setIdentificacionAbierta(!identificacionAbierta)}
          style={styles.identificacionToggle}
        >
          <span>1. Identificación / localización</span>

          <span>
            {identificacionBasicaCompleta ? 'Completa' : 'Pendiente'} · {identificacionAbierta ? 'Ocultar' : 'Mostrar'}
          </span>
        </button>

        {!identificacionAbierta && (
          <div style={styles.identificacionResumen}>
            <strong>{identificacion.nombrePuente || 'Sin nombre de puente'}</strong>
            <span>{identificacion.idPuente || 'Sin ID'}</span>
            <span>{identificacion.administradorVial || 'Sin administrador vial'}</span>
          </div>
        )}

        {identificacionAbierta && (
          <div style={styles.gridIdentificacion}>
            {camposIdentificacion.map(([key, label]) => (
              <label key={key} style={styles.label}>
                {label}
                <input
                  value={identificacion[key]}
                  onChange={(event) => actualizarIdentificacion(key, event.target.value)}
                  style={styles.input}
                />
              </label>
            ))}
          </div>
        )}
      </section>

      <section style={styles.componentesZona}>
        <button
          onClick={() => setComponentesAbierto(!componentesAbierto)}
          style={styles.componentesToggle}
        >
          <span>Componentes / observaciones</span>

          <span>
            {componenteActivo?.nombre || 'Sin componente'} · {componentesAbierto ? 'Ocultar' : 'Mostrar'}
          </span>
        </button>

        {!componentesAbierto && (
          <div style={styles.componenteResumen}>
            <strong>{componenteActivo?.nombre || 'Sin componente'}</strong>
            <span>
              {(componenteActivo?.items || []).filter((item) =>
                item.severidad !== '' || item.fotos || item.ubicacion
              ).length}/{componenteActivo?.items?.length || 0} registros
            </span>
            <span>
              {(componenteActivo?.observacionesLevantamiento || componenteActivo?.observacionesRevisor)
                ? 'Con observaciones'
                : 'Sin observaciones'}
            </span>
          </div>
        )}

        {componentesAbierto && (
          <>
            <div style={styles.componentesScroll}>
              {componentes.map((componente) => {
                const activo = componente.id === componenteActivo?.id
                const llenas = componente.items.filter((item) =>
                  item.severidad !== '' || item.fotos || item.ubicacion
                ).length

                return (
                  <button
                    key={componente.id}
                    onClick={() => {
                      setComponenteActivoId(componente.id)
                      setBusqueda('')
                      setFilaResaltada('')
                    }}
                    style={{
                      ...styles.botonComponente,
                      background: activo ? '#065f46' : '#03180f',
                      borderColor: activo ? '#34d399' : '#064e3b'
                    }}
                  >
                    <strong>{componente.nombre}</strong>
                    <span>{llenas}/{componente.items.length}</span>
                  </button>
                )
              })}
            </div>

            <div style={styles.observacionesComponente}>
              <label style={styles.label}>
                Observaciones del levantamiento
                <textarea
                  value={componenteActivo?.observacionesLevantamiento || ''}
                  onChange={(event) =>
                    actualizarComponenteActivo({
                      observacionesLevantamiento: event.target.value
                    })
                  }
                  placeholder="Observaciones del levantamiento para este componente..."
                  style={styles.observacionTextarea}
                />
              </label>

              <label style={styles.label}>
                Observaciones del revisor / equipo técnico
                <textarea
                  value={componenteActivo?.observacionesRevisor || ''}
                  onChange={(event) =>
                    actualizarComponenteActivo({
                      observacionesRevisor: event.target.value
                    })
                  }
                  placeholder="Observaciones del revisor o equipo técnico..."
                  style={styles.observacionTextarea}
                />
              </label>
            </div>
          </>
        )}
      </section>

      <section style={styles.tablaZona}>
        <div style={styles.tablaHeader}>
          <div>
            <h3 style={styles.componenteTitulo}>
              2. Registro de daños / deterioro / defectos
            </h3>

            <p style={styles.componenteMeta}>
              Componente: <strong>{componenteActivo?.nombre}</strong>
            </p>
          </div>

          <input
            value={busqueda}
            onChange={(event) => setBusqueda(event.target.value)}
            placeholder="Buscar código o daño..."
            style={styles.buscador}
          />
        </div>

        <div
          ref={scrollSuperiorRef}
          onScroll={sincronizarScrollSuperior}
          style={styles.scrollSuperior}
        >
          <div style={{ width: anchoScroll, height: 1 }} />
        </div>

        <div
          ref={tablaScrollRef}
          onScroll={sincronizarScrollTabla}
          style={styles.tablaScroll}
        >
          <table ref={tablaRef} style={styles.tabla}>
            <colgroup>
              <col style={{ width: 80 }} />
              <col style={{ width: 230 }} />
              <col style={{ width: 190 }} />
              <col style={{ width: 165 }} />
              <col style={{ width: 85 }} />
              <col style={{ width: 260 }} />
            </colgroup>

            <thead>
              <tr>
                <th style={styles.th}>Código</th>
                <th style={styles.th}>Deterioro / daño</th>
                <th style={styles.th}>Material / detalle</th>
                <th style={styles.th}>Severidad</th>
                <th style={styles.th}>N. fotos</th>
                <th style={styles.th}>Ubicación / observación</th>
              </tr>
            </thead>

            <tbody>
              {filasVisibles.map((item) => (
                <tr
                  key={item.id}
                  id={`fila-${item.id}`}
                  style={{
                    ...styles.tr,
                    outline: item.id === filaResaltada ? '2px solid #fbbf24' : 'none'
                  }}
                >
                  <td style={styles.tdCodigo}>{item.codigo}</td>

                  <td style={styles.td}>{item.dano}</td>

                  <td style={styles.td}>{item.detalle || '-'}</td>

                  <td style={styles.td}>
                    <div style={styles.severidades}>
                      {severidades.map((nivel) => {
                        const activo = String(item.severidad) === String(nivel)

                        return (
                          <button
                            key={nivel}
                            onClick={() => seleccionarSeveridad(item, nivel)}
                            style={{
                              ...styles.sevBtn,
                              background: activo ? '#fbbf24' : '#020617',
                              color: activo ? '#111827' : '#dcfce7',
                              borderColor: activo ? '#fbbf24' : '#065f46'
                            }}
                          >
                            {nivel}
                          </button>
                        )
                      })}
                    </div>
                  </td>

                  <td style={styles.td}>
                    <input
                      value={item.fotos}
                      onChange={(event) =>
                        actualizarFila(item.id, { fotos: event.target.value })
                      }
                      placeholder="1,2"
                      style={styles.inputMini}
                    />
                  </td>

                  <td style={styles.td}>
                    <textarea
                      value={item.ubicacion}
                      onChange={(event) =>
                        actualizarFila(item.id, { ubicacion: event.target.value })
                      }
                      placeholder="Descripción de la ubicación del daño principal..."
                      style={styles.textarea}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {modalImagenes && (
        <div style={styles.modalOverlay}>
          <div style={styles.modal}>
            <div style={styles.modalHeader}>
              <div>
                <h3 style={styles.modalTitle}>Imágenes para hoja Evaluación</h3>
                <p style={styles.modalSub}>
                  Estas imágenes se insertan dentro del Excel en la hoja Evaluación.
                </p>
              </div>

              <button onClick={() => setModalImagenes(false)} style={styles.closeBtn}>
                Cerrar
              </button>
            </div>

            <div style={styles.modalBody}>
              <aside style={styles.bloquesLista}>
                {bloquesEvaluacion.map((bloque, index) => (
                  <button
                    key={bloque.nombre}
                    onClick={() => setBloqueActivo(index)}
                    style={{
                      ...styles.bloqueBtn,
                      background: index === bloqueActivo ? '#065f46' : '#020617',
                      borderColor: index === bloqueActivo ? '#34d399' : '#064e3b'
                    }}
                  >
                    <strong>{bloque.nombre}</strong>
                    <span>{bloque.imagenes.length}/4 imágenes</span>
                  </button>
                ))}
              </aside>

              <main style={styles.bloqueEditor}>
                <h4 style={styles.bloqueTitle}>{bloqueActual?.nombre}</h4>

                <div style={styles.evalHint}>
                  Las fotos enviadas desde Panel Fotos llegan como candidatas. Pulsa “usar” para fijarlas. El número indica el orden final en Excel/PDF.
                </div>

                <label style={styles.label}>
                  Descripción
                  <textarea
                    value={bloqueActual?.descripcion || ''}
                    onChange={(event) => actualizarBloqueEvaluacion({ descripcion: event.target.value })}
                    style={styles.detalleTextarea}
                    placeholder="Descripción que irá en la hoja Evaluación..."
                  />
                </label>

                <label style={styles.label}>
                  Calificación
                  <input
                    value={bloqueActual?.calificacion || ''}
                    onChange={(event) => actualizarBloqueEvaluacion({ calificacion: event.target.value })}
                    style={styles.input}
                    placeholder="Ej: 1.75"
                  />
                </label>

                <label style={styles.fileBtn}>
                  Añadir candidatas desde archivo
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    onChange={agregarImagenesAlBloque}
                    style={{ display: 'none' }}
                  />
                </label>

                <div style={styles.evalImagenesGrid}>
                  <section style={styles.evalCaja}>
                    <div style={styles.evalCajaHeader}>
                      <strong>Candidatas recibidas</strong>
                      <span>{bloqueActual?.candidatas?.length || 0}</span>
                    </div>

                    <div style={styles.previewGrid}>
                      {(bloqueActual?.candidatas || []).map((img, index) => {
                        const src = img.src || img
                        const orden = (bloqueActual?.imagenes || []).indexOf(src)

                        return (
                          <div key={index} style={styles.previewBox}>
                            {orden >= 0 && (
                              <div style={styles.badgeOrden}>{orden + 1}</div>
                            )}

                            <img src={src} style={styles.previewImg} />

                            <div style={styles.previewActions}>
                              <button
                                onClick={() => fijarCandidataEvaluacion(img)}
                                style={styles.previewFix}
                              >
                                {orden >= 0 ? 'usada' : 'usar'}
                              </button>

                              <button
                                onClick={() => quitarCandidataEvaluacion(index)}
                                style={styles.previewDelete}
                              >
                                quitar
                              </button>
                            </div>
                          </div>
                        )
                      })}

                      {(bloqueActual?.candidatas || []).length === 0 && (
                        <div style={styles.sinImagenes}>
                          Sin candidatas. En Fotos usa la pestaña “Enviar a Evaluación”.
                        </div>
                      )}
                    </div>
                  </section>

                  <section style={styles.evalCajaFijas}>
                    <div style={styles.evalCajaHeader}>
                      <strong>Usadas en Excel/PDF</strong>
                      <span>{bloqueActual?.imagenes?.length || 0}/4</span>
                    </div>

                    <div style={styles.previewGrid}>
                      {(bloqueActual?.imagenes || []).map((img, index) => (
                        <div key={index} style={styles.previewBoxFija}>
                          <div style={styles.badgeOrden}>{index + 1}</div>

                          <img src={img} style={styles.previewImg} />

                          <div style={styles.previewActionsTres}>
                            <button
                              onClick={() => moverImagenFijaEvaluacion(index, -1)}
                              style={styles.previewMove}
                            >
                              ↑
                            </button>

                            <button
                              onClick={() => moverImagenFijaEvaluacion(index, 1)}
                              style={styles.previewMove}
                            >
                              ↓
                            </button>

                            <button
                              onClick={() => quitarImagenDelBloque(index)}
                              style={styles.previewDelete}
                            >
                              quitar
                            </button>
                          </div>
                        </div>
                      ))}

                      {(bloqueActual?.imagenes || []).length === 0 && (
                        <div style={styles.sinImagenes}>
                          Todavía no hay fotos usadas para este bloque.
                        </div>
                      )}
                    </div>
                  </section>
                </div>
              </main>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

const styles = {
  panel: {
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    background: '#06120d',
    color: '#dcfce7',
    overflow: 'hidden'
  },
  header: {
    padding: '12px 18px 8px',
    borderBottom: '1px solid #065f46',
    flexShrink: 0
  },
  titulo: {
    margin: 0,
    color: '#34d399',
    fontSize: 30
  },
  subtitulo: {
    margin: '4px 0 0',
    color: '#bfdbfe',
    fontSize: 12
  },
  toolbar: {
    display: 'flex',
    gap: 8,
    padding: '8px 12px',
    borderBottom: '1px solid #064e3b',
    background: '#03180f',
    flexShrink: 0,
    flexWrap: 'wrap'
  },
  actionBtn: {
    background: '#020617',
    color: '#bbf7d0',
    border: '1px solid #065f46',
    borderRadius: 8,
    padding: '8px 10px',
    cursor: 'pointer'
  },
  actionBtnPrimary: {
    background: '#065f46',
    color: '#ffffff',
    border: '1px solid #34d399',
    borderRadius: 8,
    padding: '8px 10px',
    cursor: 'pointer',
    fontWeight: 'bold'
  },
  progressWrap: {
    height: 5,
    background: '#020617',
    borderBottom: '1px solid #064e3b',
    flexShrink: 0
  },
  progressBar: {
    height: '100%',
    background: '#34d399',
    transition: 'width 0.25s ease'
  },
  estado: {
    color: '#93c5fd',
    fontSize: 11,
    padding: '5px 12px',
    borderBottom: '1px solid #064e3b',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    flexShrink: 0
  },
  identificacion: {
    margin: 10,
    marginBottom: 8,
    border: '1px solid #065f46',
    borderRadius: 12,
    background: '#03180f',
    padding: 10,
    flexShrink: 0
  },
  seccionTitulo: {
    margin: '0 0 8px',
    color: '#34d399',
    fontSize: 13
  },
  identificacionToggle: {
    width: '100%',
    background: '#020617',
    color: '#34d399',
    border: '1px solid #065f46',
    borderRadius: 8,
    padding: '8px 10px',
    cursor: 'pointer',
    display: 'flex',
    justifyContent: 'space-between',
    gap: 10,
    alignItems: 'center',
    fontWeight: 'bold',
    marginBottom: 8
  },
  identificacionResumen: {
    display: 'flex',
    gap: 10,
    flexWrap: 'wrap',
    color: '#93c5fd',
    fontSize: 12,
    padding: '3px 2px 0'
  },
  gridIdentificacion: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
    gap: 8
  },
  label: {
    color: '#86efac',
    fontSize: 11,
    display: 'flex',
    flexDirection: 'column',
    gap: 5
  },
  input: {
    background: '#020617',
    color: '#dcfce7',
    border: '1px solid #065f46',
    borderRadius: 7,
    padding: '7px',
    outline: 'none'
  },
  componentesZona: {
    margin: '0 10px 8px',
    border: '1px solid #065f46',
    borderRadius: 12,
    background: '#03180f',
    padding: 8,
    flexShrink: 0
  },
  componentesToggle: {
    width: '100%',
    background: '#020617',
    color: '#34d399',
    border: '1px solid #065f46',
    borderRadius: 8,
    padding: '8px 10px',
    cursor: 'pointer',
    display: 'flex',
    justifyContent: 'space-between',
    gap: 10,
    alignItems: 'center',
    fontWeight: 'bold',
    marginBottom: 8
  },
  componenteResumen: {
    display: 'flex',
    gap: 12,
    flexWrap: 'wrap',
    color: '#93c5fd',
    fontSize: 12,
    padding: '2px 2px 0'
  },
  observacionesComponente: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 8,
    marginTop: 8
  },
  observacionTextarea: {
    minHeight: 58,
    background: '#020617',
    color: '#dcfce7',
    border: '1px solid #065f46',
    borderRadius: 7,
    padding: 7,
    outline: 'none',
    resize: 'vertical'
  },
  componentesTitulo: {
    color: '#34d399',
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: 6
  },
  componentesScroll: {
    display: 'flex',
    gap: 8,
    overflowX: 'auto',
    overflowY: 'hidden',
    paddingBottom: 5
  },
  botonComponente: {
    minWidth: 145,
    maxWidth: 170,
    border: '1px solid #064e3b',
    borderRadius: 9,
    color: '#dcfce7',
    padding: 8,
    cursor: 'pointer',
    textAlign: 'left',
    display: 'flex',
    flexDirection: 'column',
    gap: 3,
    fontSize: 11,
    flexShrink: 0
  },
  tablaZona: {
    margin: '0 10px 10px',
    minHeight: 260,
    flex: '1 1 0',
    border: '1px solid #065f46',
    borderRadius: 12,
    background: '#03180f',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column'
  },
  tablaHeader: {
    padding: 9,
    borderBottom: '1px solid #065f46',
    display: 'flex',
    justifyContent: 'space-between',
    gap: 10,
    alignItems: 'center',
    flexShrink: 0
  },
  componenteTitulo: {
    margin: 0,
    color: '#bbf7d0',
    fontSize: 15
  },
  componenteMeta: {
    margin: '3px 0 0',
    color: '#93c5fd',
    fontSize: 12
  },
  buscador: {
    width: 190,
    background: '#020617',
    color: '#dcfce7',
    border: '1px solid #065f46',
    borderRadius: 7,
    padding: 8,
    outline: 'none'
  },
  scrollSuperior: {
    height: 14,
    overflowX: 'auto',
    overflowY: 'hidden',
    borderBottom: '1px solid #065f46',
    background: '#020617',
    flexShrink: 0
  },
  tablaScroll: {
    overflowX: 'auto',
    overflowY: 'scroll',
    flex: 1,
    minHeight: 0,
    scrollbarGutter: 'stable'
  },
  tabla: {
    width: 1010,
    borderCollapse: 'collapse',
    tableLayout: 'fixed',
    fontSize: 12
  },
  th: {
    position: 'sticky',
    top: 0,
    background: '#064e3b',
    color: '#dcfce7',
    padding: 7,
    border: '1px solid #065f46',
    textAlign: 'left',
    zIndex: 1
  },
  tr: {
    background: '#03180f'
  },
  td: {
    border: '1px solid #065f46',
    padding: 6,
    verticalAlign: 'top',
    overflow: 'hidden'
  },
  tdCodigo: {
    border: '1px solid #065f46',
    padding: 6,
    verticalAlign: 'top',
    color: '#fbbf24',
    fontWeight: 'bold',
    whiteSpace: 'nowrap'
  },
  severidades: {
    display: 'grid',
    gridTemplateColumns: 'repeat(6, 22px)',
    gap: 4
  },
  sevBtn: {
    border: '1px solid #065f46',
    borderRadius: 5,
    padding: '5px 0',
    cursor: 'pointer',
    fontWeight: 'bold'
  },
  inputMini: {
    width: '100%',
    background: '#020617',
    color: '#dcfce7',
    border: '1px solid #065f46',
    borderRadius: 6,
    padding: 6,
    outline: 'none',
    boxSizing: 'border-box'
  },
  textarea: {
    width: '100%',
    minHeight: 52,
    background: '#020617',
    color: '#dcfce7',
    border: '1px solid #065f46',
    borderRadius: 6,
    padding: 7,
    outline: 'none',
    resize: 'vertical',
    boxSizing: 'border-box'
  },
  modalOverlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.78)',
    zIndex: 9999,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24
  },
  modal: {
    width: 'min(980px, 92vw)',
    height: 'min(680px, 88vh)',
    background: '#03180f',
    border: '1px solid #34d399',
    borderRadius: 14,
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column'
  },
  modalHeader: {
    padding: 14,
    borderBottom: '1px solid #065f46',
    display: 'flex',
    justifyContent: 'space-between',
    gap: 12,
    alignItems: 'flex-start'
  },
  modalTitle: {
    margin: 0,
    color: '#34d399',
    fontSize: 20
  },
  modalSub: {
    margin: '4px 0 0',
    color: '#93c5fd',
    fontSize: 12
  },
  closeBtn: {
    background: '#7f1d1d',
    color: '#ffffff',
    border: '1px solid #fecaca',
    borderRadius: 8,
    padding: '8px 12px',
    cursor: 'pointer'
  },
  modalBody: {
    flex: 1,
    minHeight: 0,
    display: 'grid',
    gridTemplateColumns: '240px 1fr',
    gap: 12,
    padding: 12
  },
  bloquesLista: {
    overflowY: 'auto',
    borderRight: '1px solid #065f46',
    paddingRight: 10
  },
  bloqueBtn: {
    width: '100%',
    color: '#dcfce7',
    border: '1px solid #064e3b',
    borderRadius: 9,
    padding: 9,
    marginBottom: 7,
    cursor: 'pointer',
    textAlign: 'left',
    display: 'flex',
    flexDirection: 'column',
    gap: 4
  },
  bloqueEditor: {
    minWidth: 0,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 10
  },
  bloqueTitle: {
    margin: 0,
    color: '#fbbf24',
    fontSize: 18
  },
  detalleTextarea: {
    minHeight: 110,
    background: '#020617',
    color: '#dcfce7',
    border: '1px solid #065f46',
    borderRadius: 7,
    padding: 8,
    outline: 'none',
    resize: 'vertical'
  },
  fileInput: {
    color: '#bfdbfe',
    fontSize: 12
  },
  evalHint: {
    background: '#020617',
    color: '#93c5fd',
    border: '1px solid #065f46',
    borderRadius: 8,
    padding: 8,
    fontSize: 12,
    lineHeight: 1.35
  },
  fileBtn: {
    width: 'fit-content',
    background: '#065f46',
    color: '#ffffff',
    border: '1px solid #34d399',
    borderRadius: 8,
    padding: '8px 10px',
    cursor: 'pointer',
    fontWeight: 'bold',
    fontSize: 12
  },
  evalImagenesGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 12,
    minHeight: 0
  },
  evalCaja: {
    border: '1px solid #065f46',
    borderRadius: 10,
    padding: 10,
    background: '#020617',
    minHeight: 240
  },
  evalCajaFijas: {
    border: '1px solid #34d399',
    borderRadius: 10,
    padding: 10,
    background: '#03180f',
    minHeight: 240
  },
  evalCajaHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    color: '#34d399',
    marginBottom: 8,
    fontSize: 13
  },
  previewGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))',
    gap: 10
  },
  previewBox: {
    border: '1px solid #065f46',
    borderRadius: 10,
    overflow: 'hidden',
    background: '#020617'
  },
  previewImg: {
    width: '100%',
    height: 110,
    objectFit: 'cover',
    display: 'block'
  },
  previewActions: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr'
  },
  previewActionsTres: {
    display: 'grid',
    gridTemplateColumns: '34px 34px 1fr'
  },
  previewFix: {
    border: 0,
    background: '#065f46',
    color: '#ffffff',
    padding: 6,
    cursor: 'pointer',
    fontWeight: 'bold'
  },
  previewMove: {
    border: 0,
    background: '#1d4ed8',
    color: '#ffffff',
    padding: 6,
    cursor: 'pointer',
    fontWeight: 'bold'
  },
  previewBoxFija: {
    position: 'relative',
    border: '1px solid #34d399',
    borderRadius: 10,
    overflow: 'hidden',
    background: '#020617'
  },
  badgeOrden: {
    position: 'absolute',
    top: 6,
    left: 6,
    background: '#fbbf24',
    color: '#111827',
    borderRadius: 999,
    width: 24,
    height: 24,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: 'bold',
    fontSize: 12,
    zIndex: 2
  },
  previewDelete: {
    width: '100%',
    border: 0,
    background: '#7f1d1d',
    color: '#fecaca',
    padding: 6,
    cursor: 'pointer'
  },
  sinImagenes: {
    border: '1px dashed #065f46',
    borderRadius: 10,
    padding: 18,
    color: '#93c5fd',
    textAlign: 'center'
  }
}
