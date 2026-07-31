<script setup lang="ts" generic="T extends { id: number }">
import BaseCard from './BaseCard.vue'
import BaseButton from './BaseButton.vue'

withDefaults(defineProps<{
  title: string
  items: T[]
  addDisabled?: boolean
  addLoading?: boolean
  addHint?: string
}>(), {
  addDisabled: false,
  addLoading: false,
  addHint: '',
})

const emit = defineEmits<{ add: [] }>()
</script>

<template>
  <BaseCard :title="title">
    <div class="settings-item-row">
      <slot name="add-form" />
      <BaseButton
        variant="primary"
        size="sm"
        :disabled="addDisabled"
        :loading="addLoading"
        :title="addDisabled && addHint ? addHint : undefined"
        @click="emit('add')"
      >
        Add
      </BaseButton>
    </div>
    <p v-if="addDisabled && addHint" class="settings-add-hint">{{ addHint }}</p>
    <TransitionGroup tag="div" name="settings-item">
      <div v-for="item in items" :key="item.id" class="settings-item">
        <slot :item="item" />
      </div>
    </TransitionGroup>
  </BaseCard>
</template>

<style scoped>
.settings-add-hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--ink-3);
}
</style>
