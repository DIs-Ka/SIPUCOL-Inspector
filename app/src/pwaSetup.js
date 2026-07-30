import { registerSW } from 'virtual:pwa-register'

let installPrompt = null
let timer = null

function getNotice() {
  let notice = document.getElementById(
    'inspector-pwa-notice'
  )

  if (notice) {
    return notice
  }

  notice = document.createElement('aside')
  notice.id = 'inspector-pwa-notice'
  notice.hidden = true

  notice.innerHTML = `
    <div class="inspector-pwa-copy">
      <strong data-role="title">
        Inspector Sipucol
      </strong>

      <span data-role="message"></span>
    </div>

    <div class="inspector-pwa-actions">
      <button
        type="button"
        data-action="primary"
        hidden
      ></button>

      <button
        type="button"
        data-action="close"
      >
        Cerrar
      </button>
    </div>
  `

  document.body.appendChild(notice)

  return notice
}

function closeNotice() {
  const notice = getNotice()

  notice.hidden = true

  if (timer) {
    window.clearTimeout(timer)
    timer = null
  }
}

function showNotice({
  title,
  message,
  primaryLabel = '',
  primaryAction = null,
  closeLabel = 'Cerrar',
  timeout = 0
}) {
  const notice = getNotice()

  const titleElement =
    notice.querySelector('[data-role="title"]')

  const messageElement =
    notice.querySelector('[data-role="message"]')

  const primaryButton =
    notice.querySelector('[data-action="primary"]')

  const closeButton =
    notice.querySelector('[data-action="close"]')

  titleElement.textContent =
    title || 'Inspector Sipucol'

  messageElement.textContent =
    message || ''

  closeButton.textContent =
    closeLabel

  closeButton.onclick =
    closeNotice

  if (
    primaryLabel &&
    typeof primaryAction === 'function'
  ) {
    primaryButton.hidden = false
    primaryButton.textContent = primaryLabel
    primaryButton.onclick = primaryAction
  } else {
    primaryButton.hidden = true
    primaryButton.onclick = null
  }

  notice.hidden = false

  if (timer) {
    window.clearTimeout(timer)
  }

  if (timeout > 0) {
    timer = window.setTimeout(
      closeNotice,
      timeout
    )
  }
}

const updateSW = registerSW({
  immediate: true,

  onNeedRefresh() {
    showNotice({
      title: 'Actualización disponible',

      message:
        'Guarda tu trabajo antes de actualizar la aplicación.',

      primaryLabel: 'Actualizar',

      primaryAction: async () => {
        await updateSW(true)
      },

      closeLabel: 'Más tarde'
    })
  },

  onOfflineReady() {
    showNotice({
      title: 'Disponible sin conexión',

      message:
        'La interfaz quedó almacenada en este dispositivo.',

      closeLabel: 'Entendido',

      timeout: 9000
    })
  },

  onRegisterError(error) {
    console.error(
      'Error registrando PWA:',
      error
    )
  }
})

window.addEventListener(
  'beforeinstallprompt',

  (event) => {
    event.preventDefault()
    installPrompt = event

    showNotice({
      title: 'Instalar Inspector Sipucol',

      message:
        'La aplicación puede instalarse en este dispositivo.',

      primaryLabel: 'Instalar',

      primaryAction: async () => {
        if (!installPrompt) {
          return
        }

        await installPrompt.prompt()
        await installPrompt.userChoice

        installPrompt = null
        closeNotice()
      },

      closeLabel: 'Después'
    })
  }
)

window.addEventListener(
  'appinstalled',

  () => {
    installPrompt = null

    showNotice({
      title: 'Aplicación instalada',

      message:
        'Inspector Sipucol quedó instalado correctamente.',

      closeLabel: 'Listo',

      timeout: 7000
    })
  }
)

window.addEventListener(
  'offline',

  () => {
    showNotice({
      title: 'Sin conexión',

      message:
        'La interfaz continúa disponible sin internet.',

      closeLabel: 'Entendido',

      timeout: 7000
    })
  }
)

window.addEventListener(
  'online',

  () => {
    showNotice({
      title: 'Conexión recuperada',

      message:
        'Inspector Sipucol volvió a tener conexión.',

      closeLabel: 'Listo',

      timeout: 5000
    })
  }
)