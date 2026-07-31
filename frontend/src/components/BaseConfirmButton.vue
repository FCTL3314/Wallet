<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue'
import BaseButton from './BaseButton.vue'

const props = withDefaults(defineProps<{
  itemName?: string
  warning?: string
  loading?: boolean
}>(), {
  itemName: '',
  warning: '',
  loading: false,
})

const emit = defineEmits<{
  confirm: []
  'pending-change': [boolean]
}>()

const root = useTemplateRef<HTMLElement>('root')
const pending = ref(false)
let restoreTrigger = false

const prompt = computed(() => (props.itemName ? `Delete ${props.itemName}?` : 'Delete this item?'))
const triggerLabel = computed(() => (props.itemName ? `Delete ${props.itemName}` : 'Delete'))

function focusInside(selector: string) {
  root.value?.querySelector<HTMLElement>(selector)?.focus()
}

function setPending(value: boolean) {
  pending.value = value
  emit('pending-change', value)
}

function enterPending() {
  setPending(true)
}

function cancel() {
  restoreTrigger = root.value?.contains(document.activeElement) ?? false
  setPending(false)
}

function confirm() {
  restoreTrigger = root.value?.contains(document.activeElement) ?? false
  emit('confirm')
  setPending(false)
}

function onEscape() {
  if (pending.value) cancel()
}

function onAfterEnter() {
  if (pending.value) {
    focusInside('[data-confirm-cancel]')
  } else if (restoreTrigger) {
    focusInside('[data-confirm-trigger]')
    restoreTrigger = false
  }
}
</script>

<template>
  <div ref="root" class="confirm-btn-wrap" @keydown.esc="onEscape">
    <Transition name="confirm-slide" mode="out-in" @after-enter="onAfterEnter">
      <span v-if="pending" class="confirm-actions" data-confirm-pending role="alert">
        <span class="confirm-prompt">
          <span class="confirm-prompt-text">{{ prompt }}</span>
          <span v-if="warning" class="confirm-warning">{{ warning }}</span>
        </span>
        <BaseButton data-confirm-cancel variant="secondary" size="sm" @click="cancel">Cancel</BaseButton>
        <BaseButton variant="danger" size="sm" :loading="loading" @click="confirm">Delete</BaseButton>
      </span>
      <BaseButton
        v-else
        data-confirm-trigger
        variant="danger"
        size="sm"
        :loading="loading"
        :aria-label="triggerLabel"
        @click="enterPending"
      >
        Delete
      </BaseButton>
    </Transition>
  </div>
</template>

<style scoped>
.confirm-btn-wrap { display: contents; }

.confirm-actions {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.confirm-prompt {
  display: flex;
  flex-direction: column;
  gap: 2px;
  text-align: right;
}

.confirm-prompt-text {
  font-size: 12px;
  font-weight: 500;
  color: var(--ink);
  white-space: nowrap;
}

.confirm-warning {
  font-size: 11px;
  line-height: 1.3;
  color: var(--warning-ink);
  max-width: 240px;
}

.confirm-slide-enter-active { transition: all 0.2s var(--ease-spring); }
.confirm-slide-leave-active { transition: all 0.15s var(--ease-smooth); }
.confirm-slide-enter-from   { opacity: 0; transform: translateX(8px); }
.confirm-slide-leave-to     { opacity: 0; transform: translateX(8px); }

@media (max-width: 640px) {
  .confirm-actions { flex-wrap: wrap; }
  .confirm-prompt-text { white-space: normal; }
}
</style>
