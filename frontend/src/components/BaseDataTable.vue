<script setup lang="ts">
import BaseCard from './BaseCard.vue'

defineProps<{
  loading: boolean
  empty: boolean
  emptyMessage?: string
  title?: string
}>()
</script>

<template>
  <BaseCard :title="title">
    <p v-if="loading">Loading...</p>
    <p v-else-if="empty" class="text-muted">{{ emptyMessage ?? 'No items yet.' }}</p>
    <table v-else class="data-table">
      <thead><slot name="head" /></thead>
      <tbody><slot name="body" /></tbody>
    </table>
  </BaseCard>
</template>
