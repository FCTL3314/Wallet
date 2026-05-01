<script setup lang="ts">
defineProps<{ eyebrow?: string; title?: string }>()
</script>

<template>
  <div class="page-head">
    <div>
      <div v-if="eyebrow" class="page-eyebrow">{{ eyebrow }}</div>
      <h1 v-if="title" class="page-title">{{ title }}</h1>
    </div>
    <div v-if="$slots.actions" class="page-head-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.page-head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
</style>
