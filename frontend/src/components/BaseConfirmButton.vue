<script setup lang="ts">
import { ref } from 'vue'
import BaseButton from './BaseButton.vue'

const emit = defineEmits<{ confirm: [] }>()

const pending = ref(false)
</script>

<template>
  <template v-if="pending">
    <BaseButton variant="danger" size="sm" @click="emit('confirm'); pending = false">Confirm?</BaseButton>
    <BaseButton variant="secondary" size="sm" style="margin-left: 4px" @click="pending = false">Cancel</BaseButton>
  </template>
  <BaseButton v-else variant="danger" size="sm" style="margin-left: 4px" @click="pending = true">Del</BaseButton>
</template>
