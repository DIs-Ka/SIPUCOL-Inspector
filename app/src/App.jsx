import { useEffect, useState } from 'react'
import PanelFotos from './components/PanelFotos'
import PanelEvaluacion from './components/PanelEvaluacion'
import PanelCodigos from './components/PanelCodigos'

const STORAGE_PANEL_KEY = 'inspector-sipucol-panel-activo'

const paneles = [
  {
    id: 'fotos',
    etiqueta: 'Fotos',
    descripcion: 'Archivo fotográfico'
  },
  {
    id: 'evaluacion',
    etiqueta: 'Evaluación',
    descripcion: 'Inspección y daños'
  },
  {
    id: 'codigos',
    etiqueta: 'Códigos',
    descripcion: 'Catálogo SIPUCOL'
  }
]

function obtenerPanelInicial() {
  try {
    const guardado = sessionStorage.getItem(STORAGE_PANEL_KEY)

    if (paneles.some((panel) => panel.id === guardado)) {
      return guardado
    }
  } catch {
    // El navegador puede bloquear sessionStorage.
  }

  return 'evaluacion'
}

export default function App() {
  const [fotoParaEvaluacion, setFotoParaEvaluacion] = useState(null)
  const [codigoEnviado, setCodigoEnviado] = useState(null)
  const [panelActivo, setPanelActivo] = useState(obtenerPanelInicial)

  function enviarFotoAEvaluacion(payload) {
    setFotoParaEvaluacion({
      ...payload,
      token: Date.now()
    })
  }

  function buscarCodigoEnEvaluacion(codigo) {
    if (!codigo) return

    setCodigoEnviado({
      ...codigo,
      enviadoEn: Date.now()
    })

    setPanelActivo('evaluacion')
  }

  function seleccionarPanel(panelId) {
    if (!paneles.some((panel) => panel.id === panelId)) {
      return
    }

    setPanelActivo(panelId)
  }

  function manejarTecladoTabs(event) {
    if (
      event.key !== 'ArrowLeft' &&
      event.key !== 'ArrowRight'
    ) {
      return
    }

    event.preventDefault()

    const indiceActual = paneles.findIndex(
      (panel) => panel.id === panelActivo
    )

    const movimiento = event.key === 'ArrowRight' ? 1 : -1

    const siguienteIndice =
      (indiceActual + movimiento + paneles.length) %
      paneles.length

    const siguientePanel = paneles[siguienteIndice]

    seleccionarPanel(siguientePanel.id)

    requestAnimationFrame(() => {
      document
        .getElementById(`inspector-tab-${siguientePanel.id}`)
        ?.focus()
    })
  }

  useEffect(() => {
    try {
      sessionStorage.setItem(
        STORAGE_PANEL_KEY,
        panelActivo
      )
    } catch {
      // La navegación continúa aunque sessionStorage falle.
    }
  }, [panelActivo])

  return (
    <main
      className="inspector-app"
      data-panel-activo={panelActivo}
    >
      <header className="inspector-mobile-header">
        <div>
          <strong>Inspector Sipucol</strong>
          <span>Vista para tablet y celular</span>
        </div>

        <span className="inspector-mobile-mode">
          Modo campo
        </span>
      </header>

      <nav
        className="inspector-mobile-tabs"
        aria-label="Secciones de Inspector Sipucol"
        role="tablist"
        onKeyDown={manejarTecladoTabs}
      >
        {paneles.map((panel) => {
          const activo = panelActivo === panel.id

          return (
            <button
              id={`inspector-tab-${panel.id}`}
              key={panel.id}
              type="button"
              role="tab"
              aria-selected={activo}
              aria-controls={`inspector-panel-${panel.id}`}
              tabIndex={activo ? 0 : -1}
              className={[
                'inspector-mobile-tab',
                `inspector-mobile-tab-${panel.id}`,
                activo ? 'is-active' : ''
              ].join(' ')}
              onClick={() => seleccionarPanel(panel.id)}
            >
              <strong>{panel.etiqueta}</strong>
              <span>{panel.descripcion}</span>
            </button>
          )
        })}
      </nav>

      <div className="inspector-layout">
        <aside
          id="inspector-panel-fotos"
          className={[
            'inspector-panel-slot',
            'inspector-panel-fotos',
            panelActivo === 'fotos' ? 'is-active' : ''
          ].join(' ')}
          data-inspector-panel="fotos"
          role="tabpanel"
          aria-labelledby="inspector-tab-fotos"
        >
          <PanelFotos
            onEnviarFotoAEvaluacion={undefined}
          />
        </aside>

        <section
          id="inspector-panel-evaluacion"
          className={[
            'inspector-panel-slot',
            'inspector-panel-evaluacion',
            panelActivo === 'evaluacion' ? 'is-active' : ''
          ].join(' ')}
          data-inspector-panel="evaluacion"
          role="tabpanel"
          aria-labelledby="inspector-tab-evaluacion"
        >
          <PanelEvaluacion
            codigoEnviado={codigoEnviado}
            fotoDesdePanelFotos={null}
          />
        </section>

        <section
          id="inspector-panel-codigos"
          className={[
            'inspector-panel-slot',
            'inspector-panel-codigos',
            panelActivo === 'codigos' ? 'is-active' : ''
          ].join(' ')}
          data-inspector-panel="codigos"
          role="tabpanel"
          aria-labelledby="inspector-tab-codigos"
        >
          <PanelCodigos
            onUsarCodigo={buscarCodigoEnEvaluacion}
          />
        </section>
      </div>
    </main>
  )
}
