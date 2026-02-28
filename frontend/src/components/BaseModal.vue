<script setup lang="ts">
import BaseButton from './BaseButton.vue'

defineProps<{ title: string; show: boolean }>()

const emit = defineEmits<{ close: []; submit: [] }>()
</script>

<template>
  <div v-if="show" class="modal-overlay" @click.self="emit('close')">
    <div class="modal">
      <h2>{{ title }}</h2>
      <form @submit.prevent="emit('submit')">
        <slot />
        <div class="modal-actions">
          <BaseButton variant="secondary" type="button" @click="emit('close')">Cancel</BaseButton>
          <BaseButton variant="primary" type="submit">Save</BaseButton>
        </div>
      </form>
    </div>
  </div>
</template>
