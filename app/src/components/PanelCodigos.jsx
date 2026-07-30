import { useEffect, useMemo, useRef, useState } from 'react'
import { areasCodigos, codigosSIPUCOL } from '../data/codigosSIPUCOL'

const coloresArea = {
  Durabilidad: '#2563eb',
  Estabilidad: '#059669',
  'Seguridad vial': '#d97706',
  'Daños relevantes': '#dc2626',
  Todas: '#fbbf24'
}

const etiquetasSeveridad = {
  0: 'Insignificante',
  1: 'Ligero',
  2: 'Leve',
  3: 'Fuerte',
  4: 'Severo',
  5: 'Extremo'
}

const ZOOM_MIN = 0.75
const ZOOM_MAX = 3
const ZOOM_STEP = 0.25

export default function PanelCodigos({ onUsarCodigo }) {
  const [busqueda, setBusqueda] = useState('')
  const [areaActiva, setAreaActiva] = useState('Todas')
  const [codigoSeleccionado, setCodigoSeleccionado] = useState(codigosSIPUCOL[0] || null)
  const [copiado, setCopiado] = useState(false)
  const [imagenGrande, setImagenGrande] = useState(false)
  const [zoomCatalogo, setZoomCatalogo] = useState(1)

  const modalScrollRef = useRef(null)

  const imagenActual =
    codigoSeleccionado?.imagenCodigo ||
    codigoSeleccionado?.imagenPagina ||
    ''

  const conteoPorArea = useMemo(() => {
    return codigosSIPUCOL.reduce((acc, item) => {
      acc[item.area] = (acc[item.area] || 0) + 1
      return acc
    }, {})
  }, [])

  const codigosFiltrados = useMemo(() => {
    const q = busqueda.trim().toLowerCase()

    return codigosSIPUCOL.filter((item) => {
      const coincideArea = areaActiva === 'Todas' || item.area === areaActiva

      const textoBuscable = [
        item.codigo,
        item.nombre,
        item.area,
        item.numero,
        item.pagina,
        item.extracto
      ]
        .join(' ')
        .toLowerCase()

      return coincideArea && (q.length === 0 || textoBuscable.includes(q))
    })
  }, [busqueda, areaActiva])

  function seleccionarCodigo(item) {
    setCodigoSeleccionado(item)
    setCopiado(false)
    setImagenGrande(false)
    setZoomCatalogo(1)
  }

  function limpiarFiltros() {
    setBusqueda('')
    setAreaActiva('Todas')
  }

  async function copiarCodigo() {
    if (!codigoSeleccionado) return

    const texto = `${codigoSeleccionado.codigo} - ${codigoSeleccionado.nombre}`

    try {
      await navigator.clipboard.writeText(texto)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 1400)
    } catch {
      setCopiado(false)
    }
  }

  function abrirPaginaPDF() {
    if (!codigoSeleccionado || !imagenActual) return

    const url =
      `/catalogo-viewer.html?img=${encodeURIComponent(imagenActual)}&codigo=${encodeURIComponent(codigoSeleccionado.codigo)}&page=${codigoSeleccionado.pagina || 1}`

    window.open(url, '_blank', 'noopener,noreferrer')
  }

  function abrirImagenGrande() {
    setZoomCatalogo(1)
    setImagenGrande(true)
  }

  function acercarCatalogo() {
    setZoomCatalogo((prev) => {
      const nuevo = Number((prev + ZOOM_STEP).toFixed(2))
      return Math.min(ZOOM_MAX, nuevo)
    })
  }

  function alejarCatalogo() {
    setZoomCatalogo((prev) => {
      const nuevo = Number((prev - ZOOM_STEP).toFixed(2))
      return Math.max(ZOOM_MIN, nuevo)
    })
  }

  function resetZoomCatalogo() {
    setZoomCatalogo(1)
  }

  function manejarRuedaZoom(event) {
    if (!event.ctrlKey) return

    event.preventDefault()

    if (event.deltaY < 0) {
      acercarCatalogo()
    } else {
      alejarCatalogo()
    }
  }

  useEffect(() => {
    if (!imagenGrande) return

    const contenedor = modalScrollRef.current
    if (!contenedor) return

    const frame = requestAnimationFrame(() => {
      const maxScrollX = Math.max(0, contenedor.scrollWidth - contenedor.clientWidth)
      contenedor.scrollLeft = maxScrollX / 2
    })

    return () => cancelAnimationFrame(frame)
  }, [zoomCatalogo, imagenGrande, codigoSeleccionado?.id])

  return (
    <section style={styles.panel}>
      <header style={styles.header}>
        <h2 style={styles.titulo}>Códigos de daño</h2>
        <p style={styles.subtitulo}>
          {codigosSIPUCOL.length} códigos cargados · {codigosFiltrados.length} visibles
        </p>
      </header>

      <div style={styles.controles}>
        <input
          value={busqueda}
          onChange={(event) => setBusqueda(event.target.value)}
          placeholder="Buscar código, corrosión, infiltración, barandas..."
          style={styles.buscador}
        />

        <div style={styles.filtros}>
          {areasCodigos.map((area) => {
            const activo = areaActiva === area
            const cantidad =
              area === 'Todas'
                ? codigosSIPUCOL.length
                : conteoPorArea[area] || 0

            return (
              <button
                key={area}
                onClick={() => setAreaActiva(area)}
                style={{
                  ...styles.filtroBtn,
                  background: activo ? coloresArea[area] || '#d97706' : '#120c00',
                  color: activo ? '#ffffff' : '#fcd34d',
                  borderColor: activo ? coloresArea[area] || '#fbbf24' : '#78350f'
                }}
              >
                {area} {cantidad}
              </button>
            )
          })}
        </div>

        <button onClick={limpiarFiltros} style={styles.botonLimpiar}>
          Limpiar filtros
        </button>
      </div>

      <div style={styles.contenido}>
        <div style={styles.lista}>
          {codigosFiltrados.map((item) => {
            const activo = codigoSeleccionado?.id === item.id
            const colorArea = coloresArea[item.area] || '#d97706'

            return (
              <button
                key={item.id}
                onClick={() => seleccionarCodigo(item)}
                style={{
                  ...styles.codigoCard,
                  background: activo ? '#3a2603' : '#160f02',
                  borderColor: activo ? '#fbbf24' : '#3f2a05'
                }}
              >
                <div style={styles.cardTop}>
                  <span style={{ ...styles.codigoBadge, background: colorArea }}>
                    {item.codigo}
                  </span>
                  <span style={styles.pagina}>p. {item.pagina}</span>
                </div>

                <strong style={styles.nombreCodigo}>{item.nombre}</strong>

                <div style={styles.cardBottom}>
                  <span style={styles.area}>{item.area}</span>
                  <span style={styles.numeral}>{item.numero}</span>
                </div>
              </button>
            )
          })}

          {codigosFiltrados.length === 0 && (
            <div style={styles.vacio}>No hay códigos con esa búsqueda.</div>
          )}
        </div>

        <div style={styles.detalle}>
          {codigoSeleccionado ? (
            <>
              <div style={styles.detalleTop}>
                <span
                  style={{
                    ...styles.codigoGrande,
                    background: coloresArea[codigoSeleccionado.area] || '#d97706'
                  }}
                >
                  {codigoSeleccionado.codigo}
                </span>

                <span style={styles.areaDetalle}>{codigoSeleccionado.area}</span>
              </div>

              <h3 style={styles.detalleTitulo}>{codigoSeleccionado.nombre}</h3>

              <div style={styles.metaGrid}>
                <div style={styles.metaBox}>
                  <span style={styles.metaLabel}>Página PDF</span>
                  <strong style={styles.metaValor}>{codigoSeleccionado.pagina}</strong>
                </div>

                <div style={styles.metaBox}>
                  <span style={styles.metaLabel}>Numeral</span>
                  <strong style={styles.metaValor}>{codigoSeleccionado.numero}</strong>
                </div>
              </div>

              <div style={styles.accionesDetalle}>
                <button onClick={copiarCodigo} style={styles.botonAccion}>
                  {copiado ? 'Copiado' : 'Copiar código'}
                </button>

                <button onClick={abrirPaginaPDF} style={styles.botonAccion}>
                  Abrir ficha
                </button>
              </div>

              {imagenActual && (
                <div style={styles.previewCatalogo}>
                  <div style={styles.previewHeader}>
                    <h4 style={styles.seccionTitulo}>Vista visual del catálogo</h4>

                    <button onClick={abrirImagenGrande} style={styles.botonVerGrande}>
                      Ver grande
                    </button>
                  </div>

                  <button
                    onClick={abrirImagenGrande}
                    style={styles.previewBoton}
                    title="Click para ampliar"
                  >
                    <img
                      src={imagenActual}
                      alt={codigoSeleccionado.codigo}
                      style={styles.previewImagen}
                    />
                  </button>
                </div>
              )}

              <div style={styles.severidades}>
                <h4 style={styles.seccionTitulo}>Escala de calificación</h4>

                {Object.entries(etiquetasSeveridad).map(([nivel, etiqueta]) => (
                  <div key={nivel} style={styles.severidadRow}>
                    <span style={styles.nivel}>{nivel}</span>
                    <div>
                      <strong style={styles.etiquetaSeveridad}>{etiqueta}</strong>
                      <p style={styles.textoSeveridad}>
                        {codigoSeleccionado.severidades?.[nivel] || etiqueta}
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              <div style={styles.extracto}>
                <h4 style={styles.seccionTitulo}>Extracto del catálogo</h4>
                <p style={styles.extractoTexto}>
                  {codigoSeleccionado.extracto || 'Sin extracto disponible.'}
                </p>
              </div>

              <button
                onClick={() => onUsarCodigo?.(codigoSeleccionado)}
                style={styles.botonUsar}
              >
                Usar este código en Evaluación
              </button>
            </>
          ) : (
            <div style={styles.vacio}>Selecciona un código.</div>
          )}
        </div>
      </div>

      {imagenGrande && imagenActual && codigoSeleccionado && (
        <div style={styles.modalOverlay} onClick={() => setImagenGrande(false)}>
          <div style={styles.modalContenido} onClick={(event) => event.stopPropagation()}>
            <div style={styles.modalHeader}>
              <strong style={styles.modalTitulo}>
                {codigoSeleccionado.codigo} · {codigoSeleccionado.nombre}
              </strong>

              <div style={styles.modalControles}>
                <button
                  onClick={alejarCatalogo}
                  disabled={zoomCatalogo <= ZOOM_MIN}
                  style={{
                    ...styles.modalZoomBtn,
                    opacity: zoomCatalogo <= ZOOM_MIN ? 0.45 : 1,
                    cursor: zoomCatalogo <= ZOOM_MIN ? 'not-allowed' : 'pointer'
                  }}
                >
                  -
                </button>

                <button onClick={resetZoomCatalogo} style={styles.modalZoomBtn}>
                  {Math.round(zoomCatalogo * 100)}%
                </button>

                <button
                  onClick={acercarCatalogo}
                  disabled={zoomCatalogo >= ZOOM_MAX}
                  style={{
                    ...styles.modalZoomBtn,
                    opacity: zoomCatalogo >= ZOOM_MAX ? 0.45 : 1,
                    cursor: zoomCatalogo >= ZOOM_MAX ? 'not-allowed' : 'pointer'
                  }}
                >
                  +
                </button>

                <button
                  onClick={() => setImagenGrande(false)}
                  style={styles.modalCerrar}
                >
                  Cerrar
                </button>
              </div>
            </div>

            <div
              ref={modalScrollRef}
              style={styles.modalImagenWrap}
              onWheel={manejarRuedaZoom}
            >
              <div
                style={{
                  ...styles.modalCanvas,
                  width: `${zoomCatalogo * 100}%`
                }}
              >
                <img
                  src={imagenActual}
                  alt={codigoSeleccionado.codigo}
                  style={styles.modalImagen}
                />
              </div>
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
    background: '#151000',
    color: '#fef3c7',
    overflow: 'hidden'
  },
  header: {
    padding: '16px 18px 11px',
    borderBottom: '1px solid #3f2a05',
    flexShrink: 0
  },
  titulo: {
    margin: 0,
    color: '#fbbf24',
    fontSize: 30,
    lineHeight: 1.1
  },
  subtitulo: {
    margin: '6px 0 0',
    color: '#fcd34d',
    fontSize: 12
  },
  controles: {
    padding: 12,
    borderBottom: '1px solid #3f2a05',
    flexShrink: 0
  },
  buscador: {
    width: '100%',
    padding: '9px 10px',
    borderRadius: 8,
    border: '1px solid #78350f',
    background: '#080500',
    color: '#fff7ed',
    outline: 'none',
    fontSize: 13,
    marginBottom: 8
  },
  filtros: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
    marginBottom: 8
  },
  filtroBtn: {
    border: '1px solid #78350f',
    borderRadius: 999,
    padding: '5px 9px',
    fontSize: 10,
    cursor: 'pointer'
  },
  botonLimpiar: {
    background: '#120c00',
    color: '#fcd34d',
    border: '1px solid #78350f',
    borderRadius: 7,
    padding: '6px 9px',
    fontSize: 11,
    cursor: 'pointer'
  },
  contenido: {
    flex: 1,
    minHeight: 0,
    display: 'grid',
    gridTemplateRows: '42% 58%'
  },
  lista: {
    minHeight: 0,
    overflowY: 'auto',
    padding: 10,
    borderBottom: '1px solid #3f2a05',
    display: 'flex',
    flexDirection: 'column',
    gap: 8
  },
  codigoCard: {
    border: '1px solid #3f2a05',
    borderRadius: 10,
    padding: 9,
    textAlign: 'left',
    cursor: 'pointer',
    color: '#fef3c7'
  },
  cardTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6
  },
  codigoBadge: {
    color: '#ffffff',
    borderRadius: 999,
    padding: '3px 7px',
    fontSize: 11,
    fontWeight: 'bold'
  },
  pagina: {
    color: '#f59e0b',
    fontSize: 10
  },
  nombreCodigo: {
    display: 'block',
    color: '#fde68a',
    fontSize: 12,
    lineHeight: 1.25,
    marginBottom: 7
  },
  cardBottom: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: 8
  },
  area: {
    color: '#d6a738',
    fontSize: 10
  },
  numeral: {
    color: '#a16207',
    fontSize: 10
  },
  detalle: {
    minHeight: 0,
    overflowY: 'auto',
    padding: 14
  },
  detalleTop: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: 10,
    alignItems: 'center',
    marginBottom: 8
  },
  codigoGrande: {
    color: '#ffffff',
    borderRadius: 9,
    padding: '5px 9px',
    fontWeight: 'bold',
    fontSize: 15
  },
  areaDetalle: {
    color: '#fcd34d',
    fontSize: 11,
    textAlign: 'right'
  },
  detalleTitulo: {
    margin: '0 0 12px',
    color: '#fef3c7',
    fontSize: 17,
    lineHeight: 1.25
  },
  metaGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 8,
    marginBottom: 10
  },
  metaBox: {
    background: '#100a00',
    border: '1px solid #3f2a05',
    borderRadius: 8,
    padding: 8
  },
  metaLabel: {
    display: 'block',
    color: '#a16207',
    fontSize: 10
  },
  metaValor: {
    display: 'block',
    color: '#fde68a',
    fontSize: 13
  },
  accionesDetalle: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 8,
    marginBottom: 12
  },
  botonAccion: {
    background: '#120c00',
    color: '#fcd34d',
    border: '1px solid #78350f',
    borderRadius: 7,
    padding: '7px 8px',
    fontSize: 11,
    cursor: 'pointer'
  },
  previewCatalogo: {
    border: '1px solid #3f2a05',
    borderRadius: 10,
    padding: 10,
    background: '#100a00',
    marginBottom: 12
  },
  previewHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: 8,
    alignItems: 'center',
    marginBottom: 8
  },
  seccionTitulo: {
    margin: '0 0 8px',
    color: '#fbbf24',
    fontSize: 13
  },
  botonVerGrande: {
    background: '#120c00',
    color: '#fcd34d',
    border: '1px solid #78350f',
    borderRadius: 7,
    padding: '5px 8px',
    fontSize: 10,
    cursor: 'pointer',
    whiteSpace: 'nowrap'
  },
  previewBoton: {
    width: '100%',
    height: 180,
    border: '1px solid #78350f',
    borderRadius: 8,
    background: '#050300',
    overflow: 'hidden',
    padding: 0,
    cursor: 'zoom-in',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  previewImagen: {
    width: '100%',
    height: '100%',
    objectFit: 'contain',
    display: 'block'
  },
  severidades: {
    border: '1px solid #3f2a05',
    borderRadius: 10,
    padding: 10,
    marginBottom: 12,
    background: '#100a00'
  },
  severidadRow: {
    display: 'grid',
    gridTemplateColumns: '28px 1fr',
    gap: 8,
    marginBottom: 8,
    alignItems: 'start'
  },
  nivel: {
    background: '#3f2a05',
    color: '#fef3c7',
    borderRadius: 6,
    textAlign: 'center',
    padding: '4px 0',
    fontSize: 11,
    fontWeight: 'bold'
  },
  etiquetaSeveridad: {
    display: 'block',
    color: '#fde68a',
    fontSize: 11,
    marginBottom: 2
  },
  textoSeveridad: {
    margin: 0,
    color: '#fef3c7',
    fontSize: 11,
    lineHeight: 1.35
  },
  extracto: {
    border: '1px solid #3f2a05',
    borderRadius: 10,
    padding: 10,
    background: '#100a00',
    marginBottom: 12
  },
  extractoTexto: {
    margin: 0,
    color: '#fef3c7',
    fontSize: 11,
    lineHeight: 1.45
  },
  botonUsar: {
    width: '100%',
    background: '#d97706',
    color: '#fff7ed',
    border: '1px solid #fbbf24',
    borderRadius: 8,
    padding: '9px 10px',
    fontSize: 12,
    fontWeight: 'bold',
    cursor: 'pointer'
  },
  vacio: {
    border: '1px dashed #78350f',
    borderRadius: 10,
    padding: 16,
    color: '#a16207',
    textAlign: 'center',
    fontSize: 12
  },
  modalOverlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0, 0, 0, 0.82)',
    zIndex: 9999,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24
  },
  modalContenido: {
    width: 'min(1100px, 94vw)',
    height: 'min(860px, 92vh)',
    background: '#0f0a00',
    border: '1px solid #f59e0b',
    borderRadius: 12,
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column'
  },
  modalHeader: {
    padding: '10px 12px',
    borderBottom: '1px solid #78350f',
    display: 'flex',
    justifyContent: 'space-between',
    gap: 12,
    alignItems: 'center',
    color: '#fde68a',
    fontSize: 13,
    flexShrink: 0
  },
  modalTitulo: {
    minWidth: 0,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap'
  },
  modalControles: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    flexShrink: 0
  },
  modalZoomBtn: {
    background: '#120c00',
    color: '#fcd34d',
    border: '1px solid #78350f',
    borderRadius: 7,
    padding: '6px 9px',
    fontSize: 12,
    minWidth: 42
  },
  modalCerrar: {
    background: '#7f1d1d',
    color: '#fee2e2',
    border: '1px solid #ef4444',
    borderRadius: 7,
    padding: '6px 10px',
    fontSize: 12,
    cursor: 'pointer'
  },
  modalImagenWrap: {
    flex: 1,
    minHeight: 0,
    overflow: 'auto',
    background: '#050300',
    padding: 14
  },
  modalCanvas: {
    margin: '0 auto',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'flex-start'
  },
  modalImagen: {
    width: '100%',
    height: 'auto',
    display: 'block',
    borderRadius: 6,
    background: '#ffffff'
  }
}
