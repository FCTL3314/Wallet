<script setup lang="ts">
import type { Component } from 'vue'
import { storeToRefs } from 'pinia'
import { PhSun, PhMoon, PhDesktop } from '@phosphor-icons/vue'
import { useThemeStore, type ThemeMode } from '../stores/theme'

const themeStore = useThemeStore()
const { preference, mode } = storeToRefs(themeStore)

const options: { key: ThemeMode; label: string; icon: Component }[] = [
  { key: 'light',  label: 'Light',  icon: PhSun },
  { key: 'dark',   label: 'Dark',   icon: PhMoon },
  { key: 'system', label: 'System', icon: PhDesktop },
]
</script>

<template>
  <div class="theme-toggle">
    <div class="segmented" role="group" aria-label="Theme mode">
      <button
        v-for="opt in options"
        :key="opt.key"
        type="button"
        :class="{ on: preference === opt.key }"
        :aria-pressed="preference === opt.key"
        @click="themeStore.setMode(opt.key)"
      >
        <component :is="opt.icon" :size="13" weight="bold" />
        {{ opt.label }}
      </button>
    </div>
    <span v-if="preference === 'system'" class="theme-toggle-hint">
      Following your device: {{ mode }}
    </span>
  </div>
</template>

<style scoped>
.theme-toggle {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.theme-toggle-hint {
  font-size: 12px;
  color: var(--ink-3);
}
</style>
