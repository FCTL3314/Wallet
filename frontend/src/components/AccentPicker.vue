<script setup lang="ts">
import { storeToRefs } from 'pinia'
import {
  ACCENT_PRESETS,
  accentSwatchColor,
  useThemeStore,
} from '../stores/theme'

const themeStore = useThemeStore()
const { mode, hue } = storeToRefs(themeStore)
</script>

<template>
  <div class="accent-picker">
    <button
      v-for="preset in ACCENT_PRESETS"
      :key="preset.key"
      type="button"
      class="accent-swatch"
      :class="{ 'accent-swatch--active': hue === preset.hue }"
      :style="{ background: accentSwatchColor(preset.hue, mode) }"
      :title="preset.label"
      :aria-label="preset.label"
      @click="themeStore.setHue(preset.hue)"
    />
  </div>
</template>

<style scoped>
.accent-picker {
  display: inline-flex;
  gap: 8px;
}
.accent-swatch {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 0;
  cursor: pointer;
  padding: 0;
  position: relative;
  transition: transform var(--t-fast) var(--ease), box-shadow var(--t-fast) var(--ease);
}
.accent-swatch:hover { transform: scale(1.08); }
.accent-swatch--active {
  box-shadow: 0 0 0 2px var(--surface), 0 0 0 4px var(--accent);
}
</style>
