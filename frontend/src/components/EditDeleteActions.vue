<script setup lang="ts">
import { ref } from 'vue'
import BaseButton from './BaseButton.vue'
import BaseConfirmButton from './BaseConfirmButton.vue'

const emit = defineEmits<{ edit: []; confirm: [] }>()
const pending = ref(false)
</script>

<template>
  <div class="edit-delete-actions">
    <Transition name="btn-slide">
      <BaseButton v-if="!pending" variant="secondary" size="sm" @click="emit('edit')">Edit</BaseButton>
    </Transition>
    <BaseConfirmButton @confirm="emit('confirm')" @pending-change="pending = $event" />
  </div>
</template>

<style scoped>
.edit-delete-actions {
  display: inline-flex;
  gap: 6px;
  align-items: center;
}

.btn-slide-leave-active { transition: all 0.18s var(--ease-smooth); }
.btn-slide-enter-active { transition: all 0.2s var(--ease-spring); }
.btn-slide-enter-from   { opacity: 0; transform: translateX(-8px); }
.btn-slide-leave-to     { opacity: 0; transform: translateX(-8px); }
</style>
