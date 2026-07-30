import { useState } from 'react'
import PanelFotos from './components/PanelFotos'
import PanelEvaluacion from './components/PanelEvaluacion'
import PanelCodigos from './components/PanelCodigos'

export default function App() {
  const [fotoParaEvaluacion, setFotoParaEvaluacion] = useState(null)

  function enviarFotoAEvaluacion(payload) {
    setFotoParaEvaluacion({
      ...payload,
      token: Date.now()
    })
  }

  const [codigoEnviado, setCodigoEnviado] = useState(null)

  function buscarCodigoEnEvaluacion(codigo) {
    if (!codigo) return

    setCodigoEnviado({
      ...codigo,
      enviadoEn: Date.now()
    })
  }

  return (
    <main style={styles.app}>
      <aside style={styles.panelFotos}>
        <PanelFotos onEnviarFotoAEvaluacion={undefined} />
      </aside>

      <section style={styles.panelEvaluacion}>
        <PanelEvaluacion codigoEnviado={codigoEnviado}  fotoDesdePanelFotos={null} />
      </section>

      <section style={styles.panelCodigos}>
        <PanelCodigos onUsarCodigo={buscarCodigoEnEvaluacion} />
      </section>
    </main>
  )
}

const styles = {
  app: {
    height: '100vh',
    width: '100vw',
    display: 'flex',
    overflow: 'hidden',
    background: '#020617',
    fontFamily: 'Arial, sans-serif'
  },
  panelFotos: {
    width: '25%',
    minWidth: 360,
    height: '100%',
    borderRight: '2px solid #2563eb',
    boxSizing: 'border-box',
    overflow: 'hidden'
  },
  panelEvaluacion: {
    width: '47%',
    height: '100%',
    borderRight: '2px solid #059669',
    boxSizing: 'border-box',
    overflow: 'hidden'
  },
  panelCodigos: {
    width: '28%',
    height: '100%',
    boxSizing: 'border-box',
    overflow: 'hidden'
  }
}
