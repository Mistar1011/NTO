import { tr } from "@nuxt/ui/runtime/locale/index.js";

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({

  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  ssr: false,
  devServer: {
    host: '0.0.0.0',
    port: 3000,
    https: true // Оставляем для камеры
  },

  fonts:false,
  ui: {
    theme: {
      colors: [
        'primary',
        'secondary',
        'tertiary',
        'info',
        'success',
        'warning',
        'error'
      ]
    }
  },

  modules: ['@nuxt/ui', '@vueuse/nuxt'],
  css: ['~/assets/css/main.css']

})