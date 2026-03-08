<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import { PhInfo } from '@phosphor-icons/vue'
import type { Component } from 'vue'

defineProps<{
  label: string
  variant?: 'income' | 'expense' | 'profit'
  hint?: string
  icon?: Component
}>()

const iconRef = useTemplateRef<HTMLElement>('iconRef')
const tooltipVisible = ref(false)
const tooltipStyle = ref<Record<string, string>>({})

function showTooltip() {
  if (!iconRef.value) return
  const rect = iconRef.value.getBoundingClientRect()
  tooltipStyle.value = {
    left: `${rect.left + rect.width / 2 + window.scrollX}px`,
    top: `${rect.top + window.scrollY - 10}px`,
  }
  tooltipVisible.value = true
}

function hideTooltip() {
  tooltipVisible.value = false
}
</script>

<template>
  <div :class="['stat-card', variant ? `stat-card--${variant}` : '']">
    <div class="stat-label">
      <component :is="icon" v-if="icon" :size="14" weight="duotone" class="stat-label-icon" />
      {{ label }}
      <span
        v-if="hint"
        ref="iconRef"
        class="stat-hint"
        @mouseenter="showTooltip"
        @mouseleave="hideTooltip"
      >
        <PhInfo :size="13" weight="bold" />
      </span>
    </div>
    <slot />
  </div>
  <Teleport to="body">
    <div v-if="tooltipVisible && hint" class="stat-hint-popup" :style="tooltipStyle">
      <p class="stat-hint-text">{{ hint }}</p>
    </div>
  </Teleport>
</template>

<style scoped>
.stat-label {
  display: flex;
  align-items: center;
  gap: 5px;
}

.stat-hint {
  display: inline-flex;
  align-items: center;
  color: var(--text-placeholder);
  cursor: default;
  transition: color 0.15s;
}

.stat-hint:hover {
  color: var(--text-secondary);
}
</style>

<style>
.stat-hint-popup {
  position: absolute;
  width: 260px;
  transform: translate(-50%, -100%);
  background: rgba(15, 18, 28, 0.92);
  backdrop-filter: blur(10px);
  border-radius: 10px;
  padding: 12px 14px;
  pointer-events: none;
  z-index: 9999;
}

.stat-hint-popup::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-top-color: rgba(15, 18, 28, 0.92);
}

.stat-hint-text {
  font-size: 0.72rem;
  font-weight: 400;
  line-height: 1.65;
  color: rgba(255, 255, 255, 0.88);
  white-space: pre-line;
  margin: 0;
}
</style>
