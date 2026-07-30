import { useEffect, useMemo, useState } from 'react'
import FotoViewer from './FotoViewer'

const extensionesValidas = ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'gif']

const ESTADOS = {
  SIN_USAR: 'Sin usar',
  REVISADA: 'Revisada',
  DESCARTADA: 'Descartada'
}

const BLOQUES_EVALUACION_FOTOS = [
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

function normalizarRuta(ruta) {
  return ruta.replaceAll('\\', '/')
}

function obtenerPartesRuta(ruta) {
  return normalizarRuta(ruta).split('/').filter(Boolean)
}

function obtenerCarpetaDeFoto(foto) {
  const partes = obtenerPartesRuta(foto.rutaRelativa)
  return partes.slice(0, -1).join('/')
}

function obtenerNombreCarpeta(path) {
  const partes = path.split('/').filter(Boolean)
  return partes[partes.length - 1] || 'Inicio'
}

function esDescendienteDe(path, base) {
  if (!base) return true
  return path === base || path.startsWith(base + '/')
}

function obtenerCarpetasHijas(fotos, carpetaActual) {
  const mapa = new Map()

  fotos.forEach((foto) => {
    const carpetaFoto = obtenerCarpetaDeFoto(foto)

    // Si la foto está directamente en la carpeta actual,
    // NO debe crear una "subcarpeta" con el mismo nombre.
    if (carpetaFoto === carpetaActual) return

    // Solo miramos fotos que estén dentro de la carpeta actual.
    if (!esDescendienteDe(carpetaFoto, carpetaActual)) return

    const restante = carpetaActual
      ? carpetaFoto.slice(carpetaActual.length + 1)
      : carpetaFoto

    if (!restante) return

    const nombreHijo = restante.split('/')[0]
    const pathHijo = carpetaActual ? `${carpetaActual}/${nombreHijo}` : nombreHijo

    if (!mapa.has(pathHijo)) {
      mapa.set(pathHijo, {
        path: pathHijo,
        nombre: nombreHijo,
        cantidad: 0
      })
    }

    mapa.get(pathHijo).cantidad += 1
  })

  return Array.from(mapa.values()).sort((a, b) =>
    a.nombre.localeCompare(b.nombre)
  )
}

export default function PanelFotos({ onEnviarFotoAEvaluacion }) {
  const [fotos, setFotos] = useState([])
  const [fotoSeleccionada, setFotoSeleccionada] = useState(null)
  const [busqueda, setBusqueda] = useState('')
  const [filtroEstado, setFiltroEstado] = useState('Todas')
  const [fotoEnViewer, setFotoEnViewer] = useState(null)
  const [tamanoMiniatura, setTamanoMiniatura] = useState(120)
  const [carpetaRaiz, setCarpetaRaiz] = useState('')
  const [carpetaActual, setCarpetaActual] = useState('')
  const [destinoEvaluacion, setDestinoEvaluacion] = useState(BLOQUES_EVALUACION_FOTOS[0])

  function cargarFotos(event) {
    const archivos = Array.from(event.target.files || [])

    const imagenes = archivos
      .filter((archivo) => {
        const extension = archivo.name.split('.').pop().toLowerCase()
        return extensionesValidas.includes(extension)
      })
      .map((archivo, index) => ({
        id: `${archivo.name}-${archivo.lastModified}-${index}`,
        numero: index + 1,
        nombre: archivo.name,
        rutaRelativa: archivo.webkitRelativePath || archivo.name,
        url: URL.createObjectURL(archivo),
        estado: ESTADOS.SIN_USAR,
        favorita: false,
        asignaciones: []
      }))

    const primeraRuta = imagenes[0]?.rutaRelativa || ''
    const primeraParte = obtenerPartesRuta(primeraRuta)[0] || ''
    const raiz = primeraParte || ''

    const primeraFotoDirecta =
      imagenes.find((foto) => obtenerCarpetaDeFoto(foto) === raiz) ||
      imagenes[0] ||
      null

    setFotos(imagenes)
    setCarpetaRaiz(raiz)
    setCarpetaActual(raiz)
    setFotoSeleccionada(primeraFotoDirecta)
    setFotoEnViewer(null)
    setFiltroEstado('Todas')
    setBusqueda('')
  }

  function actualizarFoto(id, cambios) {
    setFotos((prevFotos) =>
      prevFotos.map((foto) =>
        foto.id === id ? { ...foto, ...cambios } : foto
      )
    )

    setFotoSeleccionada((prev) =>
      prev?.id === id ? { ...prev, ...cambios } : prev
    )

    setFotoEnViewer((prev) =>
      prev?.id === id ? { ...prev, ...cambios } : prev
    )
  }

  function cambiarEstado(nuevoEstado) {
    if (!fotoSeleccionada) return
    actualizarFoto(fotoSeleccionada.id, { estado: nuevoEstado })
  }

  function toggleFavorita() {
    if (!fotoSeleccionada) return
    actualizarFoto(fotoSeleccionada.id, {
      favorita: !fotoSeleccionada.favorita
    })
  }

  function enviarFotoSeleccionadaAEvaluacion() {
    if (typeof setEstado === 'function') {
      setEstado('Las fotos quedan como apoyo visual para evaluar daños. No se envían al Excel.')
    }

    return null
  }

  function limpiarFotos() {
    fotos.forEach((foto) => URL.revokeObjectURL(foto.url))
    setFotos([])
    setFotoSeleccionada(null)
    setFotoEnViewer(null)
    setBusqueda('')
    setFiltroEstado('Todas')
    setCarpetaRaiz('')
    setCarpetaActual('')
  }

  function abrirViewerConFoto(foto) {
    setFotoSeleccionada(foto)
    setFotoEnViewer(foto)
  }

  function seleccionarDesdeViewer(foto) {
    setFotoSeleccionada(foto)
    setFotoEnViewer(foto)
  }

  function abrirCarpeta(path) {
    const primeraFotoDirecta =
      fotos.find((foto) => obtenerCarpetaDeFoto(foto) === path) || null

    setCarpetaActual(path)
    setBusqueda('')
    setFotoSeleccionada(primeraFotoDirecta)
    setFotoEnViewer(null)
  }

  function subirCarpeta() {
    if (carpetaActual === carpetaRaiz) return

    const partes = carpetaActual.split('/').filter(Boolean)
    partes.pop()

    const nuevaCarpeta = partes.join('/')
    abrirCarpeta(nuevaCarpeta || carpetaRaiz)
  }

  const conteo = useMemo(() => {
    return {
      total: fotos.length,
      sinUsar: fotos.filter((f) => f.estado === ESTADOS.SIN_USAR).length,
      revisadas: fotos.filter((f) => f.estado === ESTADOS.REVISADA).length,
      descartadas: fotos.filter((f) => f.estado === ESTADOS.DESCARTADA).length,
      favoritas: fotos.filter((f) => f.favorita).length
    }
  }, [fotos])

  const hayBusqueda = busqueda.trim().length > 0

  const carpetasVisibles = useMemo(() => {
    if (hayBusqueda) return []
    return obtenerCarpetasHijas(fotos, carpetaActual)
  }, [fotos, carpetaActual, hayBusqueda])

  const fotosVisibles = useMemo(() => {
    return fotos.filter((foto) => {
      const carpetaFoto = obtenerCarpetaDeFoto(foto)

      const coincideCarpeta = hayBusqueda
        ? esDescendienteDe(carpetaFoto, carpetaActual)
        : carpetaFoto === carpetaActual

      const coincideBusqueda = foto.nombre
        .toLowerCase()
        .includes(busqueda.toLowerCase())

      return coincideCarpeta && coincideBusqueda
    })
  }, [fotos, carpetaActual, busqueda, filtroEstado, hayBusqueda])

  const indiceSeleccionado = useMemo(() => {
    if (!fotoSeleccionada) return -1
    return fotosVisibles.findIndex((foto) => foto.id === fotoSeleccionada.id)
  }, [fotosVisibles, fotoSeleccionada])

  function seleccionarAnterior() {
    if (indiceSeleccionado <= 0) return
    setFotoSeleccionada(fotosVisibles[indiceSeleccionado - 1])
  }

  function seleccionarSiguiente() {
    if (indiceSeleccionado < 0 || indiceSeleccionado >= fotosVisibles.length - 1) return
    setFotoSeleccionada(fotosVisibles[indiceSeleccionado + 1])
  }

  useEffect(() => {
    if (!fotoSeleccionada) return
    const sigueVisible = fotosVisibles.some((foto) => foto.id === fotoSeleccionada.id)

    if (!sigueVisible) {
      setFotoSeleccionada(fotosVisibles[0] || null)
    }
  }, [fotosVisibles, fotoSeleccionada])

  useEffect(() => {
    function manejarTeclas(event) {
      if (fotoEnViewer) return
      if (event.target.tagName === 'INPUT') return

      if (event.key === 'ArrowLeft') seleccionarAnterior()
      if (event.key === 'ArrowRight') seleccionarSiguiente()
      if (event.key === 'Enter' && fotoSeleccionada) abrirViewerConFoto(fotoSeleccionada)
    }

    window.addEventListener('keydown', manejarTeclas)
    return () => window.removeEventListener('keydown', manejarTeclas)
  }, [fotoEnViewer, indiceSeleccionado, fotosVisibles, fotoSeleccionada])

  const altoMiniatura = Math.round(tamanoMiniatura * 0.72)

  return (
    <section style={styles.panel}>
      <header style={styles.header}>
        <div style={styles.headerTexto}>
          <h2 style={styles.titulo}>Fotos</h2>
          <p style={styles.subtitulo}>
            {conteo.total} cargadas · {fotosVisibles.length} visibles · {conteo.revisadas} enviadas
          </p>
        </div>

        <div style={styles.headerBotones}>
          <label style={styles.botonCargar}>
            Cargar
            <input
              type="file"
              accept="image/*"
              multiple
              webkitdirectory="true"
              directory="true"
              onChange={cargarFotos}
              style={{ display: 'none' }}
            />
          </label>

          {fotos.length > 0 && (
            <button onClick={limpiarFotos} style={styles.botonLimpiar}>
              Limpiar
            </button>
          )}
        </div>
      </header>

      <div style={styles.barraSuperior}>
        <input
          value={busqueda}
          onChange={(event) => setBusqueda(event.target.value)}
          placeholder="Buscar foto..."
          style={styles.buscador}
        />

        <div style={styles.asignacionEvaluacion}>
          <div style={styles.asignacionHeader}>
            <strong>Enviar foto a Evaluación</strong>
            <span>
              Destino: {destinoEvaluacion}
            </span>
          </div>

          <div style={styles.componentesAsignacion}>
            {BLOQUES_EVALUACION_FOTOS.map((bloque) => (
              <button
                key={bloque}
                onClick={() => setDestinoEvaluacion(bloque)}
                style={{
                  ...styles.componenteDestinoBtn,
                  background: destinoEvaluacion === bloque ? '#1d4ed8' : '#0f172a',
                  borderColor: destinoEvaluacion === bloque ? '#60a5fa' : '#334155',
                  color: destinoEvaluacion === bloque ? '#ffffff' : '#bfdbfe'
                }}
              >
                {bloque}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div style={styles.rutaBarra}>
        <button
          onClick={subirCarpeta}
          disabled={carpetaActual === carpetaRaiz}
          style={{
            ...styles.botonAtras,
            opacity: carpetaActual === carpetaRaiz ? 0.35 : 1,
            cursor: carpetaActual === carpetaRaiz ? 'not-allowed' : 'pointer'
          }}
        >
          Atrás
        </button>

        <div style={styles.rutaTexto}>
          Carpeta actual: {obtenerNombreCarpeta(carpetaActual)}
        </div>
      </div>

      <div style={styles.preview}>
        {fotoSeleccionada ? (
          <>
            <div style={styles.previewTop}>
              <button
                onClick={seleccionarAnterior}
                disabled={indiceSeleccionado <= 0}
                style={{
                  ...styles.flechaPanel,
                  opacity: indiceSeleccionado > 0 ? 1 : 0.25
                }}
              >
                ‹
              </button>

              <div
                style={styles.imagenPreviewWrap}
                onDoubleClick={() => abrirViewerConFoto(fotoSeleccionada)}
                title="Doble click para ver grande"
              >
                <img
                  src={fotoSeleccionada.url}
                  alt={fotoSeleccionada.nombre}
                  style={styles.imagenPreview}
                />
              </div>

              <button
                onClick={seleccionarSiguiente}
                disabled={indiceSeleccionado >= fotosVisibles.length - 1}
                style={{
                  ...styles.flechaPanel,
                  opacity: indiceSeleccionado < fotosVisibles.length - 1 ? 1 : 0.25
                }}
              >
                ›
              </button>
            </div>

            <div style={styles.infoFoto}>
              <div style={styles.infoTexto}>
                <strong>
                  #{fotoSeleccionada.numero} · {fotoSeleccionada.nombre}
                </strong>
                <span>{fotoSeleccionada.rutaRelativa}</span>
                <span>
                  Estado: <b>{fotoSeleccionada.asignaciones?.length > 0 ? 'Enviada a Evaluación' : 'Sin enviar'}</b>
                  {fotoSeleccionada.favorita ? ' · Favorita' : ''}
                </span>

                {fotoSeleccionada.asignaciones?.length > 0 && (
                  <span style={styles.asignacionesTexto}>
                    Asignada a: {fotoSeleccionada.asignaciones.join(', ')}
                  </span>
                )}
              </div>

              <div style={styles.acciones}>
                <button
                  onClick={() => abrirViewerConFoto(fotoSeleccionada)}
                  style={styles.botonAzul}
                >
                  Ver grande
                </button>
              </div>
            </div>
          </>
        ) : (
          <div style={styles.vacio}>
            <strong>No hay foto seleccionada en esta carpeta.</strong>
            <span>Abre una subcarpeta o selecciona una foto abajo.</span>
          </div>
        )}
      </div>

      <div style={styles.mediaHeader}>
        <div style={styles.resultadosTexto}>
          <span>{carpetasVisibles.length} carpetas · {fotosVisibles.length} fotos</span>
          <span>Filtro: {filtroEstado}</span>
        </div>

        <div style={styles.sliderWrap}>
          <span style={styles.sliderLabel}>Tamaño</span>
          <input
            type="range"
            min="90"
            max="210"
            step="10"
            value={tamanoMiniatura}
            onChange={(event) => setTamanoMiniatura(Number(event.target.value))}
            style={styles.slider}
          />
        </div>
      </div>

      <div style={styles.mediaScroller}>
        <div style={styles.mediaFlex}>
          {carpetasVisibles.map((carpeta) => (
            <button
              key={carpeta.path}
              onClick={() => abrirCarpeta(carpeta.path)}
              style={{
                ...styles.folderCard,
                width: tamanoMiniatura
              }}
              title="Abrir carpeta"
            >
              <div
                style={{
                  ...styles.folderThumbBox,
                  width: tamanoMiniatura - 14,
                  height: altoMiniatura
                }}
              >
                <div style={styles.folderShape}>
                  <div style={styles.folderTab}></div>
                  <div style={styles.folderBody}></div>
                </div>
              </div>

              <span style={styles.nombreThumb}>{carpeta.nombre}</span>
              <span style={styles.cantidadCarpeta}>{carpeta.cantidad} fotos</span>
            </button>
          ))}

          {fotosVisibles.map((foto) => {
            const activa = fotoSeleccionada?.id === foto.id

            return (
              <button
                key={foto.id}
                onClick={() => setFotoSeleccionada(foto)}
                onDoubleClick={() => abrirViewerConFoto(foto)}
                style={{
                  ...styles.mediaCard,
                  width: tamanoMiniatura,
                  borderColor: activa ? '#3b82f6' : '#1e293b',
                  background: activa ? '#102554' : '#0f172a',
                  boxShadow: activa ? '0 0 0 1px #3b82f6 inset' : 'none'
                }}
                title="Click para seleccionar · doble click para ver grande"
              >
                <div
                  style={{
                    ...styles.mediaThumbBox,
                    width: tamanoMiniatura - 14,
                    height: altoMiniatura
                  }}
                >
                  <img
                    src={foto.url}
                    alt={foto.nombre}
                    style={styles.mediaImg}
                  />

                  <span style={styles.numeroBadge}>#{foto.numero}</span>

                  {foto.favorita && (
                    <span style={styles.favBadge}>Fav</span>
                  )}

                  {foto.asignaciones?.length > 0 && (
                    <span style={styles.asignadaBadge}>Eval {foto.asignaciones.length}</span>
                  )}

                  <span
                    style={{
                      ...styles.estadoBadge,
                      background:
                        foto.estado === ESTADOS.REVISADA
                          ? '#065f46'
                          : foto.estado === ESTADOS.DESCARTADA
                          ? '#7f1d1d'
                          : '#334155'
                    }}
                  >
                    {foto.estado}
                  </span>
                </div>

                <span style={styles.nombreThumb}>{foto.nombre}</span>
              </button>
            )
          })}

          {fotos.length > 0 &&
            carpetasVisibles.length === 0 &&
            fotosVisibles.length === 0 && (
              <div style={styles.sinResultados}>
                No hay carpetas o fotos con ese filtro/búsqueda.
              </div>
            )}
        </div>
      </div>

      <FotoViewer
        foto={fotoEnViewer}
        fotos={fotosVisibles}
        onClose={() => setFotoEnViewer(null)}
        onSelectFoto={seleccionarDesdeViewer}
      />
    </section>
  )
}

const styles = {
  panel: {
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    background: '#080d1a',
    color: '#dbeafe',
    overflow: 'hidden'
  },
  header: {
    padding: '8px 12px',
    borderBottom: '1px solid #1e3a5f',
    display: 'flex',
    justifyContent: 'space-between',
    gap: 10,
    alignItems: 'center',
    flexShrink: 0
  },
  headerTexto: {
    minWidth: 0
  },
  titulo: {
    margin: 0,
    fontSize: 22,
    color: '#60a5fa',
    lineHeight: 1.1
  },
  subtitulo: {
    margin: '4px 0 0',
    fontSize: 11,
    color: '#93c5fd',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis'
  },
  headerBotones: {
    display: 'flex',
    gap: 6,
    flexShrink: 0
  },
  botonCargar: {
    background: '#1d4ed8',
    color: 'white',
    padding: '8px 12px',
    borderRadius: 8,
    cursor: 'pointer',
    fontSize: 12,
    whiteSpace: 'nowrap'
  },
  botonLimpiar: {
    background: '#111827',
    color: '#cbd5e1',
    border: '1px solid #334155',
    padding: '8px 10px',
    borderRadius: 8,
    cursor: 'pointer',
    fontSize: 12
  },
  barraSuperior: {
    padding: 10,
    borderBottom: '1px solid #1e293b',
    flexShrink: 0
  },
  buscador: {
    width: '100%',
    boxSizing: 'border-box',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid #334155',
    background: '#020617',
    color: '#e5e7eb',
    outline: 'none',
    marginBottom: 8,
    fontSize: 13
  },
  modoFotos: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 6,
    marginBottom: 7
  },
  modoBtn: {
    border: '1px solid #334155',
    borderRadius: 7,
    padding: '5px 8px',
    fontSize: 10,
    cursor: 'pointer',
    fontWeight: 'bold'
  },
  filtros: {
    display: 'flex',
    gap: 6,
    overflowX: 'auto',
    paddingBottom: 2
  },
  asignacionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: 8,
    color: '#60a5fa',
    fontSize: 11,
    marginBottom: 2
  },
  asignacionEvaluacion: {
    display: 'flex',
    flexDirection: 'column',
    gap: 7
  },
  componentesAsignacion: {
    display: 'flex',
    gap: 6,
    overflowX: 'auto',
    paddingBottom: 3
  },
  componenteDestinoBtn: {
    border: '1px solid #334155',
    borderRadius: 8,
    padding: '6px 8px',
    fontSize: 10,
    whiteSpace: 'nowrap',
    cursor: 'pointer',
    flexShrink: 0
  },
  enviarEvaluacionBtn: {
    background: '#1d4ed8',
    color: '#ffffff',
    border: '1px solid #60a5fa',
    borderRadius: 8,
    padding: '7px 9px',
    fontSize: 11,
    fontWeight: 'bold'
  },
  asignacionesTexto: {
    color: '#34d399',
    fontWeight: 'bold'
  },
  filtroBtn: {
    border: '1px solid #334155',
    borderRadius: 999,
    padding: '4px 9px',
    fontSize: 10,
    cursor: 'pointer',
    whiteSpace: 'nowrap'
  },
  rutaBarra: {
    padding: '7px 10px',
    borderBottom: '1px solid #1e293b',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    flexShrink: 0
  },
  botonAtras: {
    background: '#0f172a',
    color: '#bfdbfe',
    border: '1px solid #334155',
    borderRadius: 6,
    padding: '5px 9px',
    fontSize: 11
  },
  rutaTexto: {
    color: '#93c5fd',
    fontSize: 11,
    overflow: 'hidden',
    whiteSpace: 'nowrap',
    textOverflow: 'ellipsis'
  },
  preview: {
    padding: 10,
    borderBottom: '1px solid #1e293b',
    flexShrink: 0
  },
  previewTop: {
    display: 'grid',
    gridTemplateColumns: '30px 1fr 30px',
    gap: 6,
    alignItems: 'stretch'
  },
  flechaPanel: {
    border: '1px solid #1e293b',
    borderRadius: 8,
    background: '#020617',
    color: '#bfdbfe',
    fontSize: 30,
    cursor: 'pointer'
  },
  imagenPreviewWrap: {
    height: 150,
    border: '1px solid #1e293b',
    borderRadius: 10,
    background: '#020617',
    overflow: 'hidden',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'zoom-in'
  },
  imagenPreview: {
    maxWidth: '100%',
    maxHeight: '100%',
    objectFit: 'contain'
  },
  infoFoto: {
    marginTop: 8,
    display: 'flex',
    flexDirection: 'column',
    gap: 7
  },
  infoTexto: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    fontSize: 11,
    color: '#93c5fd',
    overflow: 'hidden'
  },
  acciones: {
    display: 'flex',
    gap: 6,
    flexWrap: 'wrap'
  },
  botonAzulFuerte: {
    background: '#1d4ed8',
    color: '#ffffff',
    border: '1px solid #60a5fa',
    borderRadius: 6,
    padding: '6px 9px',
    fontSize: 11,
    cursor: 'pointer',
    fontWeight: 'bold'
  },
  botonAzul: {
    background: '#1d4ed8',
    color: '#ffffff',
    border: '1px solid #3b82f6',
    borderRadius: 6,
    padding: '6px 9px',
    fontSize: 11,
    cursor: 'pointer'
  },
  botonNormal: {
    background: '#0f172a',
    color: '#cbd5e1',
    border: '1px solid #334155',
    borderRadius: 6,
    padding: '6px 9px',
    fontSize: 11,
    cursor: 'pointer'
  },
  botonRojo: {
    background: '#450a0a',
    color: '#fecaca',
    border: '1px solid #7f1d1d',
    borderRadius: 6,
    padding: '6px 9px',
    fontSize: 11,
    cursor: 'pointer'
  },
  vacio: {
    height: 150,
    border: '1px dashed #334155',
    borderRadius: 10,
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    alignItems: 'center',
    justifyContent: 'center',
    color: '#64748b',
    textAlign: 'center',
    padding: 20,
    fontSize: 13
  },
  mediaHeader: {
    padding: '7px 10px',
    borderBottom: '1px solid #1e293b',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 10,
    flexShrink: 0
  },
  resultadosTexto: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    color: '#64748b',
    fontSize: 10
  },
  sliderWrap: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    width: 150,
    flexShrink: 0
  },
  sliderLabel: {
    color: '#64748b',
    fontSize: 10
  },
  slider: {
    width: '100%'
  },
  mediaScroller: {
    flex: 1,
    minHeight: 0,
    overflowY: 'auto',
    overflowX: 'hidden',
    padding: 12
  },
  mediaFlex: {
    display: 'flex',
    flexWrap: 'wrap',
    alignContent: 'flex-start',
    alignItems: 'flex-start',
    gap: 12
  },
  mediaCard: {
    border: '1px solid #1e293b',
    borderRadius: 10,
    padding: 7,
    cursor: 'pointer',
    textAlign: 'left',
    overflow: 'hidden',
    flex: '0 0 auto'
  },
  folderCard: {
    border: '1px solid #334155',
    borderRadius: 10,
    padding: 7,
    cursor: 'pointer',
    textAlign: 'left',
    overflow: 'hidden',
    flex: '0 0 auto',
    background: '#0b1324'
  },
  mediaThumbBox: {
    position: 'relative',
    borderRadius: 8,
    overflow: 'hidden',
    background: '#020617',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  folderThumbBox: {
    borderRadius: 8,
    overflow: 'hidden',
    background: '#111827',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  folderShape: {
    width: '60%',
    height: '48%',
    position: 'relative'
  },
  folderTab: {
    width: '42%',
    height: '24%',
    background: '#60a5fa',
    borderRadius: '4px 4px 0 0'
  },
  folderBody: {
    width: '100%',
    height: '76%',
    background: '#2563eb',
    borderRadius: '0 6px 6px 6px'
  },
  mediaImg: {
    width: '100%',
    height: '100%',
    objectFit: 'contain',
    display: 'block'
  },
  nombreThumb: {
    marginTop: 6,
    display: 'block',
    fontSize: 10,
    color: '#bfdbfe',
    lineHeight: 1.2,
    height: 24,
    overflow: 'hidden',
    wordBreak: 'break-word'
  },
  cantidadCarpeta: {
    marginTop: 2,
    display: 'block',
    fontSize: 10,
    color: '#64748b'
  },
  numeroBadge: {
    position: 'absolute',
    top: 6,
    left: 6,
    background: 'rgba(15, 23, 42, 0.86)',
    color: '#bfdbfe',
    fontSize: 10,
    padding: '2px 6px',
    borderRadius: 999
  },
  favBadge: {
    position: 'absolute',
    top: 6,
    right: 6,
    background: 'rgba(113, 63, 18, 0.92)',
    color: '#fde68a',
    fontSize: 10,
    padding: '2px 6px',
    borderRadius: 999
  },
  asignadaBadge: {
    position: 'absolute',
    top: 28,
    right: 6,
    background: 'rgba(29, 78, 216, 0.92)',
    color: '#dbeafe',
    fontSize: 10,
    padding: '2px 6px',
    borderRadius: 999
  },
  estadoBadge: {
    position: 'absolute',
    bottom: 6,
    left: 6,
    color: '#ffffff',
    fontSize: 10,
    padding: '2px 6px',
    borderRadius: 999
  },
  sinResultados: {
    width: '100%',
    border: '1px dashed #334155',
    borderRadius: 10,
    padding: 16,
    color: '#64748b',
    textAlign: 'center',
    fontSize: 12
  }
}
