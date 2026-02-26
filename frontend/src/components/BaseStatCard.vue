<script setup lang="ts">
defineProps<{
  label: string
  variant?: 'income' | 'expense' | 'profit'
}>()
</script>

<template>
  <div :class="['stat-card', variant ? `stat-card--${variant}` : '']">
    <div class="stat-label">{{ label }}</div>
    <slot />
  </div>
</template>
