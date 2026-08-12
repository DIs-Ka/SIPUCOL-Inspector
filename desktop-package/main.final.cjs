const {
  app,
  BrowserWindow,
  dialog,
  shell
} = require("electron")

const {
  spawn,
  spawnSync
} = require("node:child_process")

const fs = require("node:fs")
const http = require("node:http")
const net = require("node:net")
const path = require("node:path")

const BACKEND_PORT = 8000

// === SIPUCOL_FINAL_RESOURCES_START ===

const BUNDLED_LIBREOFFICE_PROGRAM =
  path.join(
    process.resourcesPath,
    "libreoffice",
    "program"
  )

const APP_ICON =
  path.join(
    process.resourcesPath,
    "app-icon.ico"
  )

// === SIPUCOL_FINAL_RESOURCES_END ===

let mainWindow = null
let backendProcess = null
let backendOwned = false

app.setAppUserModelId(
  "com.sipucol.inspector.desktop"
)

function sleep(milliseconds) {
  return new Promise(
    resolve => setTimeout(
      resolve,
      milliseconds
    )
  )
}

function requestJson(
  pathname,
  timeoutMilliseconds = 10000
) {
  return new Promise(
    resolve => {
      let completed = false

      const finish = value => {
        if (completed) {
          return
        }

        completed = true
        resolve(value)
      }

      const request = http.get(
        {
          hostname: "127.0.0.1",
          port: BACKEND_PORT,
          path: pathname,
          timeout: timeoutMilliseconds
        },

        response => {
          let body = ""

          response.setEncoding("utf8")

          response.on(
            "data",
            chunk => {
              body += chunk
            }
          )

          response.on(
            "end",
            () => {
              if (
                response.statusCode < 200 ||
                response.statusCode >= 300
              ) {
                finish(null)
                return
              }

              try {
                finish(
                  JSON.parse(body)
                )
              } catch {
                finish(null)
              }
            }
          )

          response.on(
            "error",
            () => finish(null)
          )
        }
      )

      request.on(
        "timeout",
        () => {
          request.destroy()
          finish(null)
        }
      )

      request.on(
        "error",
        () => finish(null)
      )
    }
  )
}

function isPortOpen() {
  return new Promise(
    resolve => {
      const socket = new net.Socket()
      let completed = false

      const finish = value => {
        if (completed) {
          return
        }

        completed = true
        socket.destroy()
        resolve(value)
      }

      socket.setTimeout(1500)

      socket.once(
        "connect",
        () => finish(true)
      )

      socket.once(
        "timeout",
        () => finish(false)
      )

      socket.once(
        "error",
        () => finish(false)
      )

      socket.connect(
        BACKEND_PORT,
        "127.0.0.1"
      )
    }
  )
}

async function getFastBackendState() {
  const openApi = await requestJson(
    "/openapi.json",
    10000
  )

  if (!openApi) {
    return null
  }

  const routes = openApi.paths || {}

  const valid = (
    String(
      openApi.info?.title || ""
    )
      .toLowerCase()
      .includes("sipucol") &&

    Boolean(
      routes[
        "/api/export/excel-save-dialog"
      ]
    ) &&

    Boolean(
      routes[
        "/api/export/pdf-save-dialog-v2"
      ]
    )
  )

  return valid
    ? openApi
    : null
}

async function waitForBackend() {
  for (
    let attempt = 1;
    attempt <= 100;
    attempt += 1
  ) {
    const state =
      await getFastBackendState()

    if (state) {
      return state
    }

    if (
      backendProcess &&
      backendProcess.exitCode !== null
    ) {
      return null
    }

    await sleep(500)
  }

  return null
}

function getBackendExecutable() {
  return path.join(
    process.resourcesPath,
    "backend-runtime",
    "InspectorSipucolBackend.exe"
  )
}

function getBackendLog() {
  return path.join(
    app.getPath("userData"),
    "backend-startup.log"
  )
}

function stopBackend() {
  if (
    !backendOwned ||
    !backendProcess
  ) {
    return
  }

  try {
    spawnSync(
      "taskkill",
      [
        "/pid",
        String(backendProcess.pid),
        "/t",
        "/f"
      ],
      {
        windowsHide: true,
        stdio: "ignore"
      }
    )
  } catch {
  }

  backendProcess = null
  backendOwned = false
}

async function startBackend() {
  const existing =
    await getFastBackendState()

  if (existing) {
    return existing
  }

  if (await isPortOpen()) {
    throw new Error(
      "El puerto local 8000 esta ocupado " +
      "por otro programa."
    )
  }

  const executable =
    getBackendExecutable()

  if (!fs.existsSync(executable)) {
    throw new Error(
      "No se encontro el backend integrado:\n" +
      executable
    )
  }

  const userData =
    app.getPath("userData")

  fs.mkdirSync(
    userData,
    {
      recursive: true
    }
  )

  backendProcess = spawn(
    executable,
    [],
    {
      cwd: path.dirname(executable),
      windowsHide: true,
      detached: false,
      stdio: "ignore",

      env: {
        ...process.env,
// === SIPUCOL_FINAL_ENV_START ===

        PATH: [
          BUNDLED_LIBREOFFICE_PROGRAM,
          process.env.PATH || ""
        ].join(path.delimiter),

        SIPUCOL_BUNDLED_LIBREOFFICE:
          BUNDLED_LIBREOFFICE_PROGRAM,

// === SIPUCOL_FINAL_ENV_END ===

        SIPUCOL_USER_DATA:
          userData,

        SIPUCOL_BACKEND_PORT:
          String(BACKEND_PORT)
      }
    }
  )

  backendOwned = true

  backendProcess.once(
    "exit",
    () => {
      backendProcess = null
      backendOwned = false
    }
  )

  const ready =
    await waitForBackend()

  if (!ready) {
    const logPath =
      getBackendLog()

    let logText = ""

    try {
      if (fs.existsSync(logPath)) {
        logText =
          fs.readFileSync(
            logPath,
            "utf8"
          )
      }
    } catch {
    }

    throw new Error(
      "El backend integrado no respondio.\n\n" +
      "Registro:\n" +
      logPath +
      (
        logText
          ? "\n\n" + logText.slice(-5000)
          : ""
      )
    )
  }

  return ready
}

async function createWindow() {
  await startBackend()

  const rendererIndex =
    path.join(
      __dirname,
      "dist-desktop",
      "index.html"
    )

  if (!fs.existsSync(rendererIndex)) {
    throw new Error(
      "No se encontro la interfaz desktop."
    )
  }

  mainWindow =
    new BrowserWindow({
      width: 1500,
      height: 920,

      minWidth: 900,
      minHeight: 650,

      show: false,

      backgroundColor:
        "#020617",

      autoHideMenuBar:
        true,

      title:
        "Inspector Sipucol",
      icon: APP_ICON,

      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        sandbox: true,
        webSecurity: false,
        devTools: false
      }
    })

  mainWindow.removeMenu()

  mainWindow.once(
    "ready-to-show",
    () => {
      mainWindow.show()
      mainWindow.focus()
    }
  )

  mainWindow.webContents
    .setWindowOpenHandler(
      ({ url }) => {
        if (
          url.startsWith("http://") ||
          url.startsWith("https://")
        ) {
          shell.openExternal(url)
        }

        return {
          action: "deny"
        }
      }
    )

  await mainWindow.loadFile(
    rendererIndex
  )
}

const lock =
  app.requestSingleInstanceLock()

if (!lock) {
  app.quit()
} else {
  app.on(
    "second-instance",
    () => {
      if (!mainWindow) {
        return
      }

      if (mainWindow.isMinimized()) {
        mainWindow.restore()
      }

      mainWindow.show()
      mainWindow.focus()
    }
  )

  app.whenReady().then(
    async () => {
      try {
        await createWindow()
      } catch (error) {
        dialog.showErrorBox(
          "Inspector Sipucol no pudo iniciar",
          String(
            error?.stack ||
            error?.message ||
            error
          )
        )

        app.quit()
      }
    }
  )
}

app.on(
  "before-quit",
  () => {
    stopBackend()
  }
)

app.on(
  "window-all-closed",
  () => {
    app.quit()
  }
)

process.on(
  "uncaughtException",
  error => {
    dialog.showErrorBox(
      "Error inesperado",
      String(
        error?.stack ||
        error?.message ||
        error
      )
    )
  }
)