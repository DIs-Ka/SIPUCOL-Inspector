import path from "node:path"
import { fileURLToPath } from "node:url"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

const configFile =
  fileURLToPath(import.meta.url)

const appRoot =
  path.dirname(configFile)

const rendererRoot =
  path.join(
    appRoot,
    ".desktop-renderer"
  )

const outputRoot =
  path.resolve(
    appRoot,
    "..",
    "desktop-package",
    "dist-desktop"
  )

export default defineConfig({
  root:
    rendererRoot,

  base:
    "./",

  publicDir:
    path.join(
      appRoot,
      "public"
    ),

  plugins: [
    react()
  ],

  build: {
    outDir:
      outputRoot,

    emptyOutDir:
      true,

    chunkSizeWarningLimit:
      2000
  }
})