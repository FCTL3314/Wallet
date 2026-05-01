import { ref } from 'vue'
import { defineStore } from 'pinia'

export type ThemeMode = 'light' | 'dark'

export interface AccentPreset {
  key: string
  label: string
  hue: number
}

// Six hue presets that the design's oklch palette gracefully accepts.
export const ACCENT_PRESETS: AccentPreset[] = [
  { key: 'green',  label: 'Green',  hue: 150 },
  { key: 'teal',   label: 'Teal',   hue: 195 },
  { key: 'blue',   label: 'Blue',   hue: 240 },
  { key: 'violet', label: 'Violet', hue: 285 },
  { key: 'orange', label: 'Orange', hue: 35  },
  { key: 'rose',   label: 'Rose',   hue: 10  },
]

const DEFAULT_HUE = 150

export function accentSwatchColor(hue: number, mode: ThemeMode = 'light'): string {
  return mode === 'dark' ? `oklch(74% 0.17 ${hue})` : `oklch(58% 0.14 ${hue})`
}

function applyToDOM(mode: ThemeMode, hue: number) {
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

  // Legacy aliases for code that hasn't migrated yet. Kept in sync with --accent.
  root.style.setProperty('--color-accent', `var(--accent)`)
  root.style.setProperty('--color-accent-light', `var(--accent-soft-2)`)
}

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>((localStorage.getItem('theme-mode') as ThemeMode) ?? 'light')
  const hue = ref<number>(Number(localStorage.getItem('theme-hue')) || DEFAULT_HUE)

  function setMode(value: ThemeMode) {
    mode.value = value
    localStorage.setItem('theme-mode', value)
    applyToDOM(mode.value, hue.value)
  }

  function setHue(value: number) {
    hue.value = value
    localStorage.setItem('theme-hue', String(value))
    applyToDOM(mode.value, hue.value)
  }

  function init() {
    applyToDOM(mode.value, hue.value)
  }

  return { mode, hue, setMode, setHue, init }
})
