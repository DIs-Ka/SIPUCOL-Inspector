import { useEffect, useState } from 'react'

export default function FotoViewer({ foto, fotos = [], onClose, onSelectFoto }) {
  const [zoom, setZoom] = useState(1)

  const indiceActual = foto
    ? fotos.findIndex((item) => item.id === foto.id)
    : -1

  const hayAnterior = indiceActual > 0
  const haySiguiente = indiceActual >= 0 && indiceActual < fotos.length - 1

  function cerrar() {
    onClose?.()
  }

  function irAnterior() {
    if (!hayAnterior) return
    onSelectFoto?.(fotos[indiceActual - 1])
  }

  function irSiguiente() {
    if (!haySiguiente) return
    onSelectFoto?.(fotos[indiceActual + 1])
  }

  function acercar() {
    setZoom((prev) => Math.min(4, Number((prev + 0.25).toFixed(2))))
  }

  function alejar() {
    setZoom((prev) => Math.max(0.5, Number((prev - 0.25).toFixed(2))))
  }

  function resetZoom() {
    setZoom(1)
  }

  function manejarRueda(event) {
    if (!event.ctrlKey) return

    event.preventDefault()

    if (event.deltaY < 0) {
      acercar()
    } else {
      alejar()
    }
  }

  useEffect(() => {
    setZoom(1)
  }, [foto?.id])

  useEffect(() => {
    function manejarTeclas(event) {
      if (!foto) return

      if (event.key === 'Escape') cerrar()
      if (event.key === 'ArrowLeft') irAnterior()
      if (event.key === 'ArrowRight') irSiguiente()
      if (event.key === '+' || event.key === '=') acercar()
      if (event.key === '-') alejar()
      if (event.key === '0') resetZoom()
    }

    window.addEventListener('keydown', manejarTeclas)

    return () => {
      window.removeEventListener('keydown', manejarTeclas)
    }
  }, [foto, indiceActual, hayAnterior, haySiguiente])

  if (!foto) return null

  return (
    <div style={styles.overlay} onClick={cerrar}>
      <div style={styles.viewer} onClick={(event) => event.stopPropagation()}>
        <header style={styles.header}>
          <div style={styles.tituloWrap}>
            <h3 style={styles.titulo}>{foto.nombre}</h3>
            <p style={styles.ruta}>{foto.rutaRelativa}</p>
          </div>

          <div style={styles.controles}>
            <button
              style={{
                ...styles.boton,
                opacity: zoom <= 0.5 ? 0.45 : 1,
                cursor: zoom <= 0.5 ? 'not-allowed' : 'pointer'
              }}
              disabled={zoom <= 0.5}
              onClick={alejar}
            >
              -
            </button>

            <button style={styles.boton} onClick={resetZoom}>
              {Math.round(zoom * 100)}%
            </button>

            <button
              style={{
                ...styles.boton,
                opacity: zoom >= 4 ? 0.45 : 1,
                cursor: zoom >= 4 ? 'not-allowed' : 'pointer'
              }}
              disabled={zoom >= 4}
              onClick={acercar}
            >
              +
            </button>

            <button style={styles.botonCerrar} onClick={cerrar}>
              Cerrar
            </button>
          </div>
        </header>

        <main style={styles.main}>
          <button
            onClick={irAnterior}
            disabled={!hayAnterior}
            style={{
              ...styles.flecha,
              opacity: hayAnterior ? 1 : 0.25,
              cursor: hayAnterior ? 'pointer' : 'not-allowed'
            }}
          >
            ‹
          </button>

          <div style={styles.imagenZona} onWheel={manejarRueda}>
            <div
              style={{
                ...styles.canvas,
                width: `${zoom * 100}%`
              }}
            >
              <img
                src={foto.url}
                alt={foto.nombre}
                style={styles.imagen}
              />
            </div>
          </div>

          <button
            onClick={irSiguiente}
            disabled={!haySiguiente}
            style={{
              ...styles.flecha,
              opacity: haySiguiente ? 1 : 0.25,
              cursor: haySiguiente ? 'pointer' : 'not-allowed'
            }}
          >
            ›
          </button>
        </main>

        <footer style={styles.footer}>
          <span>
            Foto {indiceActual + 1} de {fotos.length}
          </span>

          <span>
            Flechas: anterior/siguiente · Esc: cerrar · + / -: zoom · Ctrl + rueda: zoom · 0: reset
          </span>
        </footer>
      </div>
    </div>
  )
}

const styles = {
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0, 0, 0, 0.94)',
    zIndex: 9999,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 22,
    boxSizing: 'border-box'
  },
  viewer: {
    width: '94vw',
    height: '94vh',
    background: '#020617',
    border: '1px solid #334155',
    borderRadius: 14,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    boxShadow: '0 20px 80px rgba(0,0,0,0.75)'
  },
  header: {
    minHeight: 64,
    padding: '10px 16px',
    borderBottom: '1px solid #1e293b',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 16,
    flexShrink: 0
  },
  tituloWrap: {
    minWidth: 0
  },
  titulo: {
    margin: 0,
    color: '#bfdbfe',
    fontSize: 15,
    maxWidth: '58vw',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis'
  },
  ruta: {
    margin: '4px 0 0',
    color: '#64748b',
    fontSize: 11,
    maxWidth: '58vw',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis'
  },
  controles: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    flexShrink: 0
  },
  boton: {
    minWidth: 38,
    height: 34,
    borderRadius: 8,
    border: '1px solid #334155',
    background: '#0f172a',
    color: '#dbeafe',
    cursor: 'pointer',
    fontSize: 13
  },
  botonCerrar: {
    height: 34,
    borderRadius: 8,
    border: '1px solid #7f1d1d',
    background: '#7f1d1d',
    color: '#fff',
    cursor: 'pointer',
    fontSize: 13,
    padding: '0 12px'
  },
  main: {
    flex: 1,
    minHeight: 0,
    display: 'grid',
    gridTemplateColumns: '58px 1fr 58px',
    background: '#000'
  },
  flecha: {
    border: 0,
    background: '#020617',
    color: '#bfdbfe',
    fontSize: 46,
    cursor: 'pointer'
  },
  imagenZona: {
    minWidth: 0,
    minHeight: 0,
    overflow: 'auto',
    background: '#000',
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'center',
    padding: 16,
    boxSizing: 'border-box'
  },
  canvas: {
    margin: '0 auto',
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'center'
  },
  imagen: {
    width: '100%',
    height: 'auto',
    display: 'block',
    objectFit: 'contain',
    borderRadius: 8
  },
  footer: {
    minHeight: 38,
    padding: '8px 14px',
    borderTop: '1px solid #1e293b',
    color: '#93c5fd',
    fontSize: 12,
    display: 'flex',
    justifyContent: 'space-between',
    gap: 12,
    flexShrink: 0
  }
}
