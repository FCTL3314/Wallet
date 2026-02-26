<script setup lang="ts">
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
          <button type="button" class="btn btn-secondary" @click="emit('close')">Cancel</button>
          <button type="submit" class="btn btn-primary">Save</button>
        </div>
      </form>
    </div>
  </div>
</template>
