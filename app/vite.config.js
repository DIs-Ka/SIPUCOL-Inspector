import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import { VitePWA } from "vite-plugin-pwa"

export default defineConfig({
  base: "/",

  plugins: [
    react(),

    VitePWA({
      registerType: "prompt",

      includeAssets: [
        "icons/favicon.svg",
        "icons/apple-touch-icon.png"
      ],

      manifest: {
        id: "/",
        name: "Inspector Sipucol",
        short_name: "Sipucol",

        description:
          "Aplicación para inspección, evaluación, fotografías y códigos SIPUCOL.",

        lang: "es-CO",
        start_url: "/",
        scope: "/",

        display: "standalone",
        orientation: "any",

        background_color: "#020617",
        theme_color: "#059669",

        categories: [
          "productivity",
          "utilities"
        ],

        icons: [
          {
            src: "/icons/pwa-192x192.png",
            sizes: "192x192",
            type: "image/png",
            purpose: "any"
          },

          {
            src: "/icons/pwa-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "any"
          },

          {
            src: "/icons/pwa-maskable-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable"
          }
        ]
      },

      workbox: {
        cleanupOutdatedCaches: true,
        navigateFallback: "index.html",

        navigateFallbackDenylist: [
          /^\/api\//
        ],

        globPatterns: [
          "**/*.{js,css,html,svg,ico}",
          "icons/*.png"
        ],

        maximumFileSizeToCacheInBytes:
          5 * 1024 * 1024,

        runtimeCaching: [
          {
            urlPattern:
              /\/(?:catalogo-codigos|catalogo-pages)\//i,

            handler: "CacheFirst",

            options: {
              cacheName:
                "inspector-sipucol-catalogo-v1",

              expiration: {
                maxEntries: 400,
                maxAgeSeconds:
                  60 * 60 * 24 * 30
              },

              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          }
        ]
      }
    })
  ],

  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true
  },

  preview: {
    host: "127.0.0.1",
    port: 4173,
    strictPort: true
  }
})