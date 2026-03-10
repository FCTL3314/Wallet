<script setup lang="ts">
defineProps<{ title?: string; flush?: boolean }>()
</script>

<template>
  <div class="card" :class="{ 'card--flush': flush }">
    <div v-if="title || $slots.left || $slots.actions" class="card-header" :class="{ 'card-header--flush': flush }">
      <div class="card-header-left">
        <div v-if="title" class="card-title">{{ title }}</div>
        <slot name="left" />
      </div>
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
  gap: 12px;
  margin-bottom: 16px;
}

.card-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.card-header--flush {
  padding: 20px 24px 16px;
  margin-bottom: 0;
}

.card-header .card-title {
  margin-bottom: 0;
}
</style>
