import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'

export type ThemeMode = 'light' | 'dark' | 'system'
export type ResolvedTheme = 'light' | 'dark'

export interface AccentPreset {
  key: string
  label: string
  hue: number
}

export const ACCENT_PRESETS: AccentPreset[] = [
  { key: 'green',  label: 'Green',  hue: 150 },
  { key: 'teal',   label: 'Teal',   hue: 195 },
  { key: 'blue',   label: 'Blue',   hue: 240 },
  { key: 'violet', label: 'Violet', hue: 285 },
  { key: 'orange', label: 'Orange', hue: 35  },
  { key: 'rose',   label: 'Rose',   hue: 10  },
]

const DEFAULT_HUE = 150
const PREFERENCE_KEY = 'theme-preference'
const RESOLVED_KEY = 'theme-mode'
const HUE_KEY = 'theme-hue'
const DARK_QUERY = '(prefers-color-scheme: dark)'

export function accentSwatchColor(hue: number, mode: ResolvedTheme = 'light'): string {
  return mode === 'dark' ? `oklch(74% 0.17 ${hue})` : `oklch(58% 0.14 ${hue})`
}

let darkMedia: MediaQueryList | null = null

function darkMediaQuery(): MediaQueryList {
  darkMedia ??= window.matchMedia(DARK_QUERY)
  return darkMedia
}

function readPreference(): ThemeMode {
  const stored = localStorage.getItem(PREFERENCE_KEY)
  if (stored === 'light' || stored === 'dark' || stored === 'system') return stored
  return localStorage.getItem(RESOLVED_KEY) === 'dark' ? 'dark' : 'light'
}

function applyToDOM(mode: ResolvedTheme, hue: number) {
  const root = document.documentElement
  root.dataset.theme = mode

  if (mode === 'dark') {
    root.style.setProperty('--accent',        `oklch(74% 0.17 ${hue})`)
    root.style.setProperty('--accent-ink',    `oklch(88% 0.14 ${hue})`)
    root.style.setProperty('--accent-soft',   `oklch(26% 0.06 ${hue})`)
    root.style.setProperty('--accent-soft-2', `oklch(34% 0.09 ${hue})`)
    root.style.setProperty('--focus-ring',    `0 0 0 3px oklch(74% 0.17 ${hue} / .3)`)
  } else {
    root.style.setProperty('--accent',        `oklch(58% 0.14 ${hue})`)
    root.style.setProperty('--accent-ink',    `oklch(36% 0.11 ${hue})`)
    root.style.setProperty('--accent-soft',   `oklch(94% 0.04 ${hue})`)
    root.style.setProperty('--accent-soft-2', `oklch(88% 0.08 ${hue})`)
    root.style.setProperty('--focus-ring',    `0 0 0 3px oklch(58% 0.14 ${hue} / .22)`)
  }

  root.style.setProperty('--color-accent', `var(--accent)`)
  root.style.setProperty('--color-accent-light', `var(--accent-soft-2)`)
}

export const useThemeStore = defineStore('theme', () => {
  const preference = ref<ThemeMode>(readPreference())
  const systemPrefersDark = ref(darkMediaQuery().matches)
  const hue = ref<number>(Number(localStorage.getItem(HUE_KEY)) || DEFAULT_HUE)

  const mode = computed<ResolvedTheme>(() =>
    preference.value === 'system'
      ? (systemPrefersDark.value ? 'dark' : 'light')
      : preference.value,
  )

  function apply() {
    localStorage.setItem(RESOLVED_KEY, mode.value)
    applyToDOM(mode.value, hue.value)
  }

  watch([mode, hue], apply)

  function setMode(value: ThemeMode) {
    preference.value = value
    localStorage.setItem(PREFERENCE_KEY, value)
  }

  function setHue(value: number) {
    hue.value = value
    localStorage.setItem(HUE_KEY, String(value))
  }

  let systemListenerAttached = false

  function init() {
    localStorage.setItem(PREFERENCE_KEY, preference.value)
    if (!systemListenerAttached) {
      darkMediaQuery().addEventListener('change', (event) => {
        systemPrefersDark.value = event.matches
      })
      systemListenerAttached = true
    }
    apply()
  }

  return { preference, mode, hue, systemPrefersDark, setMode, setHue, init }
})
