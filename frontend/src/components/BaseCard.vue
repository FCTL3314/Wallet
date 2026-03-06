<script setup lang="ts">
defineProps<{ title?: string }>()
</script>

<template>
  <div class="card">
    <div v-if="title || $slots.actions" class="card-header">
      <div v-if="title" class="card-title">{{ title }}</div>
      <slot name="actions" />
    </div>
    <slot />
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card-header .card-title {
  margin-bottom: 0;
}
</style>
