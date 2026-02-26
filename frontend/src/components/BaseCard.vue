<script setup lang="ts">
defineProps<{ title?: string }>()
</script>

<template>
  <div class="card">
    <div v-if="title" class="card-title">{{ title }}</div>
    <slot />
  </div>
</template>
