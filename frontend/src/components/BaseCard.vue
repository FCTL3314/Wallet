<script setup lang="ts">
defineProps<{ title?: string; flush?: boolean }>()
</script>

<template>
  <div class="card" :class="{ 'card--flush': flush }">
    <div v-if="title || $slots.actions" class="card-header" :class="{ 'card-header--flush': flush }">
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

.card-header--flush {
  padding: 20px 24px 16px;
  margin-bottom: 0;
}

.card-header .card-title {
  margin-bottom: 0;
}
</style>
