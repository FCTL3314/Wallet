<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useLoadingStore } from '../stores/loading'

const { isLoading } = storeToRefs(useLoadingStore())

const visible = ref(false)
const finishing = ref(false)
let showTimer: ReturnType<typeof setTimeout> | null = null
let hideTimer: ReturnType<typeof setTimeout> | null = null

watch(isLoading, (loading) => {
  if (loading) {
    if (hideTimer) { clearTimeout(hideTimer); hideTimer = null }
    finishing.value = false
    if (!visible.value && !showTimer) {
      showTimer = setTimeout(() => {
        visible.value = true
        showTimer = null
      }, 120)
    }
  } else {
    if (showTimer) { clearTimeout(showTimer); showTimer = null }
    if (visible.value) {
      finishing.value = true
      hideTimer = setTimeout(() => {
        visible.value = false
        finishing.value = false
        hideTimer = null
      }, 280)
    }
  }
})

const barClass = computed(() => ({
  'loading-bar--finishing': finishing.value,
  'loading-bar--active': visible.value && !finishing.value,
}))
</script>

<template>
  <div v-if="visible" class="loading-bar" :class="barClass" aria-hidden="true">
    <div class="loading-bar__inner" />
  </div>
</template>

<style scoped>
.loading-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  z-index: 10000;
  pointer-events: none;
  background: transparent;
}

.loading-bar__inner {
  height: 100%;
  width: 0%;
  background: linear-gradient(
    90deg,
    rgba(var(--color-accent-rgb), 0.6),
    rgb(var(--color-accent-rgb)),
    rgba(var(--color-accent-rgb), 0.6)
  );
  box-shadow: 0 0 8px rgba(var(--color-accent-rgb), 0.55);
  border-radius: 0 2px 2px 0;
  transition: width 0.3s ease;
}

.loading-bar--active .loading-bar__inner {
  animation: loading-bar-progress 2.4s ease-out forwards;
}

.loading-bar--finishing .loading-bar__inner {
  width: 100% !important;
  animation: none;
  transition: width 0.2s ease-out, opacity 0.25s ease-out 0.1s;
  opacity: 0;
}

@keyframes loading-bar-progress {
  0%   { width: 0%; }
  30%  { width: 45%; }
  60%  { width: 72%; }
  85%  { width: 88%; }
  100% { width: 92%; }
}
</style>
