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
  <template v-if="pending">
    <BaseButton variant="danger" size="sm" @click="confirm">Confirm?</BaseButton>
    <BaseButton variant="secondary" size="sm" style="margin-left: 4px" @click="cancel">Cancel</BaseButton>
  </template>
  <BaseButton v-else variant="danger" size="sm" style="margin-left: 4px" @click="enterPending">Del</BaseButton>
</template>
