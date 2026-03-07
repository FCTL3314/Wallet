import { ref } from 'vue'
import { defineStore } from 'pinia'

export type ThemeMode = 'light' | 'dark'
export type AccentKey = 'blue' | 'violet' | 'teal' | 'green' | 'orange' | 'rose'

export interface AccentPreset {
  label: string
  main: string
  light: string
  rgb: string // "r, g, b" — for use in rgba(var(--color-accent-rgb), alpha)
}

export const ACCENT_PRESETS: Record<AccentKey, AccentPreset> = {
  blue:   { label: 'Blue',   main: '#2272cc', light: '#4298f5', rgb: '34, 114, 204' },
  violet: { label: 'Violet', main: '#7c3aed', light: '#a78bfa', rgb: '124, 58, 237' },
  teal:   { label: 'Teal',   main: '#0e9488', light: '#2dd4bf', rgb: '14, 148, 136' },
  green:  { label: 'Green',  main: '#16a34a', light: '#4ade80', rgb: '22, 163, 74' },
  orange: { label: 'Orange', main: '#ea580c', light: '#fb923c', rgb: '234, 88, 12' },
  rose:   { label: 'Rose',   main: '#e11d48', light: '#fb7185', rgb: '225, 29, 72' },
}

function applyToDOM(mode: ThemeMode, key: AccentKey) {
  const root = document.documentElement
  root.dataset.theme = mode
  const p = ACCENT_PRESETS[key]
  root.style.setProperty('--color-accent', p.main)
  root.style.setProperty('--color-accent-light', p.light)
  root.style.setProperty('--color-accent-rgb', p.rgb)
  root.style.setProperty('--shadow-btn-accent', `0 4px 24px rgba(${p.rgb}, 0.30)`)
}

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>((localStorage.getItem('theme-mode') as ThemeMode) ?? 'light')
  const accent = ref<AccentKey>((localStorage.getItem('theme-accent') as AccentKey) ?? 'blue')

  function setMode(value: ThemeMode) {
    mode.value = value
    localStorage.setItem('theme-mode', value)
    applyToDOM(mode.value, accent.value)
  }

  function setAccent(value: AccentKey) {
    accent.value = value
    localStorage.setItem('theme-accent', value)
    applyToDOM(mode.value, accent.value)
  }

  function init() {
    applyToDOM(mode.value, accent.value)
  }

  return { mode, accent, setMode, setAccent, init }
})
