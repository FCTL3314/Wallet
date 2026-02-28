<script setup lang="ts" generic="T extends { id: number }">
import BaseCard from './BaseCard.vue'
import BaseButton from './BaseButton.vue'

defineProps<{ title: string; items: T[] }>()
const emit = defineEmits<{ add: [] }>()
</script>

<template>
  <BaseCard :title="title">
    <div class="settings-item-row">
      <slot name="add-form" />
      <BaseButton variant="primary" size="sm" @click="emit('add')">Add</BaseButton>
    </div>
    <div v-for="item in items" :key="item.id" class="settings-item">
      <slot :item="item" />
    </div>
  </BaseCard>
</template>
