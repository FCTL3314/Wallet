<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{ confirm: [] }>()

const pending = ref(false)
</script>

<template>
  <template v-if="pending">
    <button class="btn btn-danger btn-sm" @click="emit('confirm'); pending = false">Confirm?</button>
    <button class="btn btn-secondary btn-sm" style="margin-left: 4px" @click="pending = false">Cancel</button>
  </template>
  <button v-else class="btn btn-danger btn-sm" style="margin-left: 4px" @click="pending = true">Del</button>
</template>
