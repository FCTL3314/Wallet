<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { PhSun, PhMoon } from '@phosphor-icons/vue'
import { useThemeStore, type ThemeMode } from '../stores/theme'

const themeStore = useThemeStore()
const { mode } = storeToRefs(themeStore)

const options: { key: ThemeMode; label: string }[] = [
  { key: 'light', label: 'Light' },
  { key: 'dark',  label: 'Dark'  },
]
</script>

<template>
  <div class="segmented">
    <button
      v-for="opt in options"
      :key="opt.key"
      type="button"
      :class="{ on: mode === opt.key }"
      @click="themeStore.setMode(opt.key)"
    >
      <PhSun v-if="opt.key === 'light'" :size="13" weight="bold" />
      <PhMoon v-else :size="13" weight="bold" />
      {{ opt.label }}
    </button>
  </div>
</template>
