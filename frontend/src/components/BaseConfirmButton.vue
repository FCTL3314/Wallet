<script setup lang="ts">
import { ref } from 'vue'
import BaseButton from './BaseButton.vue'

const emit = defineEmits<{
  confirm: []
  'pending-change': [boolean]
}>()

const pending = ref(false)

function enterPending() {
  pending.value = true
  emit('pending-change', true)
}

function cancel() {
  pending.value = false
  emit('pending-change', false)
}

function confirm() {
  emit('confirm')
  pending.value = false
  emit('pending-change', false)
}
</script>

<template>
  <div class="confirm-btn-wrap">
    <Transition name="confirm-slide" mode="out-in">
      <span v-if="pending" class="confirm-actions">
        <BaseButton variant="danger" size="sm" @click="confirm">Confirm?</BaseButton>
        <BaseButton variant="secondary" size="sm" @click="cancel">Cancel</BaseButton>
      </span>
      <BaseButton v-else variant="danger" size="sm" @click="enterPending">Del</BaseButton>
    </Transition>
  </div>
</template>

<style scoped>
.confirm-btn-wrap { display: contents; }
.confirm-actions  { display: flex; gap: 6px; }

.confirm-slide-enter-active { transition: all 0.2s var(--ease-spring); }
.confirm-slide-leave-active { transition: all 0.15s var(--ease-smooth); }
.confirm-slide-enter-from   { opacity: 0; transform: translateX(8px); }
.confirm-slide-leave-to     { opacity: 0; transform: translateX(8px); }
</style>
